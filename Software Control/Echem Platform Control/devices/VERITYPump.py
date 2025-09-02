import asyncio
import math
from loguru import logger

class VERITYPump():
    """
    GSIOC Syringe Pump.
    """
    def __init__(self, devices) -> None:
        self.port_instance = devices
        self.aspirated_volume = 0
    
    async def aspirate_solution(self, volume, flowrate = 0.5) -> None:
        """
        Coro: aspirate specificed volume (µL) at specified flow rate (mL/min).
        """
        aspvolume = volume
        maxasptime = 75 #29 seconds for 500 µL with default settings #needs changes to be dependent on flowrate
        logger.info('starting pump to aspirate ...')
        await self.port_instance.connect(device_name='VERITY 4020',device_id=11)
        await asyncio.sleep(2)  #wait for connection to be established
        logger.info("waited for 5 sec")
        while (aspvolume > 0):
            await asyncio.sleep(5)
            if(aspvolume >= 400):
                await self.port_instance.b_command('PN:+400:'+ str(flowrate) )
                await asyncio.sleep(maxasptime) #wait for aspiration to finish
                logger.info("waited for 80 sec")
                await self.port_instance.b_command('PR:-400:'+ str(2) ) #purge syringe to reservoir
                await asyncio.sleep(15) #wait for aspiration to finish
                logger.info("waited for 80 sec")

                aspvolume = aspvolume - 400 #subtract 500 from total volume to be aspirated
                self.aspirated_volume = self.aspirated_volume + 400 #track amount aspirated as object property
                print("Aspirated Volume = " + str(self.aspirated_volume))
            else:
                a = (aspvolume/400) * maxasptime
                if (a < 10): a = 10   #minimum wait time is 10 seconds
                #await asyncio.sleep(a)
                #logger.info("waited for " + str(a))
                await self.port_instance.b_command('PN:+' + str(aspvolume) + ':' + str(flowrate))
                await asyncio.sleep(a)
                logger.info("waited for " + str(a))
                await self.port_instance.b_command('PR:-' + str(aspvolume) + ':' + str(2))
                #await asyncio.sleep(a)
                #logger.info("waited for " + str(a))
                self.aspirated_volume = self.aspirated_volume + aspvolume #track amount aspirated as object property
                aspvolume = aspvolume - aspvolume #reduce aspirated volume to 0
                print("Aspirated Volume = " + str(self.aspirated_volume))
                #await asyncio.sleep(5)
                #logger.info("waited for 5 sec")


    async def dispense_solution(self, volume, flowrate = 1.0, safety = True) -> None:
        """
        Coro: dispense specificed volume (µL) at specified flow rate (mL/min).
        """
        dispvolume = volume
        maxdisptime = 15 + ((0.4/flowrate)*60)
        logger.info('starting pump to dispense ...')
        await self.port_instance.connect(device_name='VERITY 4020',device_id=11)
        await asyncio.sleep(5)  #wait for connection to be established
        logger.info("waited for 5 sec")

        if (dispvolume > self.aspirated_volume) and safety:
            dispvolume = self.aspirated_volume
        
        while (dispvolume > 0):
            await asyncio.sleep(5)
            if(dispvolume >= 400):
                await self.port_instance.b_command('PR:+400:'+ str(2) )
                await asyncio.sleep(15) #wait for aspiration to finish

                await self.port_instance.b_command('PN:-400:'+ str(flowrate) ) #purge syringe to reservoir
                await asyncio.sleep(maxdisptime) #wait for aspiration to finish

                dispvolume = dispvolume - 400 #subtract 500 from total volume to be aspirated
                self.aspirated_volume = self.aspirated_volume - 400 #track amount aspirated as object property
                print("Aspirated Volume = " + str(self.aspirated_volume))

            else:
                a = (dispvolume/400) * maxdisptime
                #await asyncio.sleep(a)
                #logger.info("waited for " + str(a))
                if (a < 10): a = 10   #minimum wait time is 20 seconds
                await self.port_instance.b_command('PR:+' + str(dispvolume) + ':' + str(2))
                await asyncio.sleep(a)
                logger.info("waited for " + str(a))
                await self.port_instance.b_command('PN:-' + str(dispvolume) + ':' + str(flowrate))
                #await asyncio.sleep(a)
                #logger.info("waited for " + str(a))
                self.aspirated_volume = self.aspirated_volume - dispvolume #track amount aspirated as object property
                dispvolume = dispvolume - dispvolume #reduce aspirated volume to 0
                print("Aspirated Volume = " + str(self.aspirated_volume))
                #await asyncio.sleep(5)
                #logger.info("waited for 5 sec")
