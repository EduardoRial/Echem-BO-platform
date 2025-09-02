# -*- coding: utf-8 -*-
import asyncio
from asyncua import Client, ua
from loguru import logger
import sys
import numpy as np

__all__ = ['FractionCollector']

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
    def __init__(self, vial_B: int):# , valve_position: str):
        self.vial_B = vial_B
        # self.valve_position = valve_position

class State():
    MOVETOPOSITION = "MOVETOPOSITION"
    IDLE = "IDLE"
    MOVETOVIAL = "MOVETOVIAL"

class FC(State):
    '''
    Pump class for Syrris Asia Pump

    :param client: OPCUA client object
    :param serial_number: serial number of the pump
    :param pump_identificator: A or B as str
    '''

    NAME = "AsiaAutomatedCollector_"
    METHOD_MOVETOPOSITION = "MoveToPosition"
    METHOD_MOVETOVIAL = "MoveToVial"


    @classmethod
    async def create(cls, client, serial_number: str, FC_identificator: str):
        #Creates instance for communication to the pump via OPC-UA protocol.
        self = FC()
        self.client = client
        self.serial_number = serial_number
        self.DeviceSet = get_node(self.client, 2, 5001)
        self.name = f"AsiaAutomatedCollector_{serial_number}{FC_identificator}"
        pump_browse_name = f"1:{self.name}"
        logger.info(f'pump_browse_name: {pump_browse_name}')
        self.pump_object    = await self.DeviceSet.get_child([pump_browse_name])
        logger.info(f'self.pump_object: {self.pump_object}')
 
        self.ValvePosition  = await self.pump_object.get_child(["5:ValvePosition"])
        self.ValvePosition_type  = await self.ValvePosition.read_data_type_as_variant_type()
        
        self.VialPosition  = await self.pump_object.get_child(["5:VialPosition"])
        self.VialPosition_type  = await self.VialPosition.read_data_type_as_variant_type()
        
        self.methods = {
            self.METHOD_MOVETOPOSITION: await self.pump_object.get_child(["5:MoveToPosition"]),
            self.METHOD_MOVETOVIAL: await self.pump_object.get_child(["5:MoveToVial"]),
        }
        

        return self
    
    
    async def set_flowrate_to(self, value):
        #Sets the flowRate parameter to desired value and awaits this change
        reply = await self._call_method(self.METHOD_PUMP, value)
        if reply == "OK":
            logger.debug(f"{self.name}: FlowRate sent")
            #await self._wait_for_value(self.FlowRate, value)
            logger.info(f"{self.name}: FlowRate set to {value}")

        else:
            raise Exception(f"Coro set_flowrate_to got unexpected reply: {reply}.")
        
    async def _call_method(self, method_name, value=None):
        if value is None:
            reply = await self.pump_object.call_method(self.methods[method_name])
            return reply

        else:
            #input_argument = ua.Variant(value, self.VialPosition_type)
            input_argument = ua.Variant(value, ua.VariantType.UInt32)
            reply = await self.pump_object.call_method(self.methods[method_name], input_argument)
            return reply


    async def _call_method_2(self, method_name, value1=None, value2=None):
        if value1 is None:
            reply = await self.pump_object.call_method(self.methods[method_name])
            return reply

        else:
            #input_argument = ua.Variant(value, self.VialPosition_type)
            input_argument_1 = ua.Variant(value1, ua.VariantType.Double)
            input_argument_2 = ua.Variant(value2, ua.VariantType.Double)
            reply = await self.pump_object.call_method(self.methods[method_name], input_argument_1, input_argument_2)
            return reply

        # input_argument = ua.Variant(value, self.VialPosition_type)
        # await self.pump_object.call_method(self.methods[method_name], input_argument)       


    async def move_to_tube(self, value):
        #Sets the flowRate parameter to desired value and awaits this change
        # await self._call_method(self.METHOD_MOVETOVIAL, value)
        reply = await self._call_method(self.METHOD_MOVETOVIAL, value)
        if reply == "OK":
            logger.debug(f"{self.name}: FlowRate sent")
            #await self._wait_for_value(self.FlowRate, value)
            logger.info(f"{self.name}: Fraction collector moved to vial {value}")
        else:
             raise Exception(f"Coro set_flowrate_to got unexpected reply: {reply}.")

    async def cleaning_tip(self, value_x, value_y):
        #Sets the flowRate parameter to desired value and awaits this change
        # await self._call_method(self.METHOD_MOVETOVIAL, value)
        reply = await self._call_method_2(self.METHOD_MOVETOPOSITION, value_x, value_y)
        if reply == "OK":
            logger.debug(f"{self.name}: FlowRate sent")
            #await self._wait_for_value(self.FlowRate, value)
            logger.info(f"{self.name}: Fraction collector moved to vial {value_x, value_y}")
        else:
             raise Exception(f"Coro set_flowrate_to got unexpected reply: {reply}.") 
             
    async def read_vial_position(self):
        #Reads the pressure
        value = await self.VialPosition.read_value()
        logger.info(f"{self.name}: The position is {value}")
        return value

    async def valve_to_collect_position(self):
        await self.ValvePosition.write_value("COLLECT")
        logger.info(f"{self.name}: Valve of fraction collector in collect position")

    async def valve_to_waste_position(self):
        await self.ValvePosition.write_value("WASTE")
        logger.info(f"{self.name}: Valve of fraction collector in waste position")
    
async def main(tube, valve_position):

    url = "opc.tcp://rcpeno02341:5000/" # OPC Server on new RCPE laptop

    logger.info(f"OPC-UA Client: Connecting to {url} ...")
    async with Client(url=url) as client:
        # ------ Here you can define and operate all your pumps -------
        AsiaFC = await FC.create(client, "20475", "B")
        # vial = Level(tube)
        await AsiaFC.move_to_tube(tube)

        if valve_position == "waste":
            await AsiaFC.valve_to_waste_position()
        elif valve_position == "collect":
            await AsiaFC.valve_to_collect_position()
        elif valve_position == "beaker_waste":
            await AsiaFC.cleaning_tip(130, 70)
        # await asyncio.sleep(4)
        # await AsiaFC.valve_to_collect_position()




      
if __name__ == "__main__":
# logger.remove()
# logger.add(sys.stderr, level=LOG_LEVEL)
    asyncio.run(main())