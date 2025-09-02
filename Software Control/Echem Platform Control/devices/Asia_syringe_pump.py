# -*- coding: utf-8 -*-
import asyncio
from asyncua import Client, ua
from loguru import logger
import sys
import numpy as np

__all__ = ['Pump']

LOG_LEVEL = "INFO"

def get_node(client, idx, name):
    print('getting node ...')
    nodeid = build_nodeid(idx, name)
    node = client.get_node(nodeid)
    print(f'node: {node}')
    return node

def build_nodeid(idx, name) -> ua.NodeId:
    print('building node id ...')
    nodeid = ua.NodeId.from_string(f'ns={idx};i={name}')
    print(f'node id: {nodeid}')
    return nodeid


class Level():
    def __init__(self, flowrate_A: int, flowrate_B: int, time_in_seconds: float):
        self.flowrate_A = flowrate_A
        self.flowrate_B = flowrate_B
        self.time_in_seconds = time_in_seconds

class State():
    EMPTY = "EMPTY"
    EMPTYING = "EMPTYING"
    IDLE = "IDLE"
    FILLING = "FILLING"
    FULL = "FULL"
    PUMPING = "PUMPING"

class Pump(State):
    '''
    Pump class for Syrris Asia Pump

    :param client: OPCUA client object
    :param serial_number: serial number of the pump
    :param pump_identificator: A or B as str
    '''

    NAME = "AsiaPump_"
    METHOD_STOP = "stop"
    METHOD_PUMP = "pump"
    METHOD_FILL = "fill"
    METHOD_EMPTY = "empty"
    METHOD_TARE = "tare"

    @classmethod
    async def create(cls, client, serial_number: str, pump_identificator: str):
        #Creates instance for communication to the pump via OPC-UA protocol.
        self = Pump()
        self.client = client
        self.serial_number = serial_number
        self.DeviceSet = get_node(self.client, 2, 5001)
        self.name = f"AsiaPump_{serial_number}{pump_identificator}"
        pump_browse_name = f"1:{self.name}"
        logger.info(f'pump_browse_name: {pump_browse_name}')
        self.pump_object    = await self.DeviceSet.get_child([pump_browse_name])
        logger.info(f'self.pump_object: {self.pump_object}')
        self.State          = await self.pump_object.get_child(["5:State"])
        self.Pressure       = await self.pump_object.get_child(["5:Pressure"])
        logger.info(f'pressure: {self.Pressure}')
        self.SyringeVolume  = await self.pump_object.get_child(["5:SyringeVolume"])
        self.FlowRate       = await self.pump_object.get_child(["5:FlowRate"])
        self.FlowRate_type  = await self.FlowRate.read_data_type_as_variant_type()
        
        self.methods = {
            self.METHOD_STOP: await self.pump_object.get_child(["5:Stop"]),
            self.METHOD_PUMP: await self.pump_object.get_child(["5:Pump"]),
            self.METHOD_FILL: await self.pump_object.get_child(["5:Fill"]),
            self.METHOD_EMPTY: await self.pump_object.get_child(["5:Empty"]),
            self.METHOD_TARE: await self.pump_object.get_child(["5:Tare"])
        }
        
        self.MAX_FLOWRATE = 4 * (await self.SyringeVolume.read_value())
        return self

    async def activate(self):
        #Activates the pump: stops and filles the valve
        logger.info(f"{self.name}: Starting the activation process...")
        await self._call_method(self.METHOD_STOP)
        await self._call_method(self.METHOD_FILL, self.MAX_FLOWRATE)
        await self._wait_for_value(self.State, self.FULL)
        logger.info(f"{self.name}: Activation process completed. -> Ready to use.")


    async def set_flowrate_to(self, value):
        #Sets the flowRate parameter to desired value and awaits this change
        reply = await self._call_method(self.METHOD_PUMP, value)
        if reply == "OK":
            logger.debug(f"{self.name}: FlowRate sent")
            #await self._wait_for_value(self.FlowRate, value)
            logger.info(f"{self.name}: FlowRate set to {value}")

        else:
            raise Exception(f"Coro set_flowrate_to got unexpected reply: {reply}.")
        

    async def read_pressure(self):
        #Reads the pressure
        value = await self.Pressure.read_value()
        logger.info(f"{self.name}: Pressure is {value}")
        return value


    async def deactivate(self):
        #Deactivates the pump: stops and empties the valve.
        logger.info(f"{self.name}: Starting the deactivation process...")
        await self._call_method(self.METHOD_STOP)
        await self._call_method(self.METHOD_EMPTY, self.MAX_FLOWRATE)
        await self._wait_for_value(self.State, self.EMPTY)
        logger.info(f"{self.name}: Deactivation process completed.")


    async def _call_method(self, method_name, value=None):
        if value is None:
            reply = await self.pump_object.call_method(self.methods[method_name])
            return reply

        else:
            input_argument = ua.Variant(value, self.FlowRate_type)
            reply = await self.pump_object.call_method(self.methods[method_name], input_argument)
            return reply
            

    async def _wait_for_value(self, opcua_variable, desired_value):
        current_value = await opcua_variable.read_value()
        logger.debug(f"Coro _wait_for_value: current {current_value}, desired {desired_value}")
        while not current_value == desired_value:
            await asyncio.sleep(1)
            current_value = await opcua_variable.read_value()
            logger.debug(f"Coro _wait_for_value: current {current_value}, desired {desired_value}")

    @classmethod
    def format_flowrate(cls, flowrates_in: list, max_pump_flowrate: float | int ) -> list:
        """
        formats an inputted list with numbers (float, int) and returns a list with int() entries like: '[2500,234,2342, ... ]' in (uL/min).
        if the inputted flowrate exceeds the range of flowrates (depending on max flowrate of the utilized pumps) it appends a NaN (Not a Number) value to the list instead. 
        """
        RANGE_FLOWRATE = [10, max_pump_flowrate] # (μL/min)
        flowrates_out = []

        for i in range(len(flowrates_in)):
            n = flowrates_in[i]
            try:
                if RANGE_FLOWRATE[0] <= n <= RANGE_FLOWRATE[1]:
                    n=round(n,0)
                    n=int(n)
                    flowrates_out.append(n)
                else:
                    flowrates_out.append(np.nan)
                    print(f'value "{n}" out of range: {RANGE_FLOWRATE}')
                pass
            except TypeError:
                flowrates_out.append(np.nan)
                print(f'value "{n}" is not a number')
                pass
        return flowrates_out


######## TESTING SECTION #########

async def main(flow_rate_A, flow_rate_B, time_pumping):
    # ----------- Defining url of OPCUA and flowRate levels -----------
    # url = "opc.tcp://rcpeno00472:5000/" #OPC Server on RCPE Laptop
    url = "opc.tcp://rcpeno02341:5000/" # OPC Server on new RCPE laptop

    # url = "opc.tcp://18-nf010:5000/" #OPC Server on FTIR Laptop
    
    # -----------------------------------------------------------------


    logger.info(f"OPC-UA Client: Connecting to {url} ...")
    async with Client(url=url) as client:
        # ------ Here you can define and operate all your pumps -------
        pump13A = await Pump.create(client, "24196", "A")
        pump13B = await Pump.create(client, "24196", "B")
        # pump13A = await Pump.create(client, "8064112", "A")
        # pump13B = await Pump.create(client, "8064112", "B")
        # await asyncio.gather(pump13A.activate(), pump13B.activate())
        
        
        flowrate_levels = (Level(flow_rate_A, flow_rate_B, time_pumping), # filling the system with reaction mixture
                           Level(0, 0, 0),) # collecting, cleaning the tip
        for flowrate_level in flowrate_levels:
            # await asyncio.sleep(10) # Add a delay (in seconds) before pumps start
            if  flowrate_level.flowrate_A == 0: 
                await pump13A._call_method(pump13A.METHOD_STOP)
                logger.info(f"{pump13A.name}: Pump stopped.")
            else: 
                await pump13A.set_flowrate_to(flowrate_level.flowrate_A)
            
            if flowrate_level.flowrate_B == 0: 
                await pump13B._call_method(pump13B.METHOD_STOP)
                logger.info(f"{pump13B.name}: Pump stopped.")
            else:
                await pump13B.set_flowrate_to(flowrate_level.flowrate_B)
            await asyncio.sleep(flowrate_level.time_in_seconds)
            




        # await asyncio.gather(pump13A.deactivate(), pump13B.deactivate())
      
if __name__ == "__main__":
# logger.remove()
# logger.add(sys.stderr, level=LOG_LEVEL)
    asyncio.run(main())
