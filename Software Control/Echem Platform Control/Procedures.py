import devices.InjectionValve
import devices.LiquidHandler
import devices.rack
import devices.VERITYPump
import asyncio
import math
from loguru import logger
from bkp.power_supply import *
from bkp.protocol_power_supply import *
from devices import Asia_syringe_pump
from bkp import *

class ProcedureObject():
    def __init__(self, ports) -> None:
        self.liquidhandler = devices.LiquidHandler.GsiocLiquidHandler(ports)
        self.pump = devices.VERITYPump.VERITYPump(ports)
        self.valve = devices.InjectionValve.GsiocDirectInjectionModule(ports)
        self.rack = devices.rack.Rack()
        self.solvdensity = 1.1
        self.extraasp = 10
        self.count = 1

    
    async def AspirateFromVial(self, vial, volume, flowrate = 1):
        position = self.rack.FindVial(vial)
        logger.info("switching to position: " + str(position))
        await asyncio.sleep(1)
        await self.liquidhandler.switch_to_position(position)
        await asyncio.sleep(2)
        logger.info("waited for 3 sec")
        await self.pump.aspirate_solution(volume, flowrate = flowrate)
        await asyncio.sleep(2)
        logger.info("waited for 5 sec")
        await self.liquidhandler.go_home()

    async def GoToVial(self, vial):
        position = self.rack.FindVial(vial)
        logger.info("switching to position: " + str(position))
        await asyncio.sleep(1)
        await self.liquidhandler.switch_to_position(position)
        await asyncio.sleep(2)
        logger.info("waited for 5 sec")
        await self.liquidhandler.go_home()

    async def DispenseToVial(self, vial, volume, flowrate = 0.5):
            if (self.pump.aspirated_volume < volume): self.pump.aspirated_volume = volume
            position = self.rack.FindVial(vial)
            logger.info("switching to position: " + str(position))
            await asyncio.sleep(1)
            await self.liquidhandler.switch_to_position(position)
            await asyncio.sleep(2)
            await self.pump.dispense_solution(volume, flowrate = flowrate)
            await asyncio.sleep(2)
            await self.liquidhandler.go_home()
    
    async def Inject(self, flowrate = 1):

        injectvolume = self.pump.aspirated_volume * 1.2
        logger.info("switching to position: DIM")
        await asyncio.sleep(1)
        await self.liquidhandler.switch_to_position(DIM = True)
        logger.info("injecting " + str(injectvolume) + "mL")
        await asyncio.sleep(5)
        await self.valve.switch_to_position("L")
        await asyncio.sleep(2)
        logger.info("waited for 3 sec")
        await self.pump.dispense_solution(injectvolume, safety=False, flowrate = flowrate)
        await asyncio.sleep(2)
        logger.info("waited for 3 sec")

    async def AspirateMixture(self, recipe, flowrate = 0.5):
        if len(recipe) % 2 == 0:
            for i in range(len(recipe)):
                if i % 2 == 0:
                    vialnum = recipe[i]
                else:
                    aspamt = round(recipe[i], ndigits = 1)
                    logger.info("aspirating " + str(aspamt) + "mL from vial in position " + str(vialnum))
                    await self.AspirateFromVial((vialnum-4), aspamt+self.extraasp, flowrate = flowrate)
                    await asyncio.sleep(5)
                    await self.DispenseToVial(((vialnum+4)-4),self.extraasp)
                    await asyncio.sleep(5)
                    logger.info("waited for 10 sec")

    async def SlugFormation(self, dictionary_substance_volume : dict): 
        SolvPos = 1
        GasPos = 2
        await self.AspirateFromVial(vial = GasPos, volume = 60)

        for substance,volume in dictionary_substance_volume.items():
            await self.AspirateFromVial(substance, volume)
            await asyncio.sleep(3)
            await self.AspirateFromVial(SolvPos, 0)

        await self.AspirateFromVial(vial = GasPos, volume = 10)

        await self.Inject()
        logger.info("injection done")
        await asyncio.sleep(3)
        await self.valve.switch_to_position("I")
        await asyncio.sleep(3)
        await self.liquidhandler.go_home()
        logger.info("valve switched")
        self.pump.aspirated_volume = 0

    async def Perform_Reaction (self, flow_rate, time_pumping, voltage, current):
        protocol = BKPrecisionRS232('COM4')
        bkp_device = BKPrecisionPowerSupply(protocol)
        await bkp_device.initialize_device()
        await bkp_device.set_current(current)
        await bkp_device.set_voltage(voltage)
        await Asia_syringe_pump.main(flow_rate, 0, time_pumping)
        # await asyncio.sleep (time_pumping)
        await bkp_device.set_voltage(0)
        await asyncio.sleep(0.5)
        voltage = await bkp_device.get_voltage()
        for i in range (10):
            if voltage == 0:
                await bkp_device.close_port()
                pass
            else:
                await bkp_device.set_voltage(0)
                await bkp_device.close_port()
        await asyncio.sleep(1)
        await bkp_device.close_port()
