import asyncio
import numpy as np
from loguru import logger
from LHProtocol.gsioc import GSIOCProtocol
import devices.VERITYPump
import devices.LiquidHandler
import Procedures
from asyncua import Client
from devices import Asia_syringe_pump
port = 'COM3'

'This file allows to perform automated experiments without using a server for getting the experimental conditions'

concentration_main_stock_sol = 100 #mM
concentration_main_in_reaction = 20 #mM
position_main_reagent = "3"
volume_main_reagent = (concentration_main_in_reaction*415/concentration_main_stock_sol) #415 is the slug size with a correction factor

concentration_stock_sol_reagents_1 = [170, 500, 500] #Write the concentration of the stock solutions in order
equiv_reagents_1 = [3, 1, 3] #Write in order the equivalents that it is desired for each reagent
reagents_list_1 = ["4","5","6"] #Position of the stock solutions. The list position should match with concentration and number of equiv.


async def initialize(ports):
    
    await recipe_calculation(ports, equiv_reagents_1,concentration_stock_sol_reagents_1, reagents_list_1)

async def recipe_calculation (ports, equiv_reagents : list, concentration_stock_sol_reagents : list, reagents_list : list, position_main_reagent = "3"):
    
    volume_reagent = []
    for i in range(len(concentration_stock_sol_reagents)):
        calculated_volume = (equiv_reagents[i]*concentration_main_in_reaction*370)/concentration_stock_sol_reagents[i] #256 uL droplet with a correction factor
        volume_reagent.append(calculated_volume)
   

    dictionary_reagents_substances = {position_main_reagent: volume_main_reagent}
    for j in range (len(reagents_list)):  
        key = reagents_list[j]
        value = volume_reagent[j]

        dictionary_reagents_substances[key] = value
        print (dictionary_reagents_substances)

    volume_all_reagents = sum(volume_reagent) + volume_main_reagent
    volume_solvent = 360 - volume_all_reagents
    
    dictionary_reagents_substances[1] = volume_solvent

    print (dictionary_reagents_substances)
    print (volume_solvent)
    
    await runSlug(ports, dictionary_reagents_substances)


async def runSlug(ports, dictionary_reagents_substances):
    proc = Procedures.ProcedureObject(ports)
    logger.info("start")         
    
    await proc.SlugFormation(dictionary_reagents_substances)
    await asyncio.sleep(1)

    await Asia_syringe_pump.main(1000,0,14.5) #transfer slug from sample loop to reactor
    await asyncio.sleep(1)

    await proc.Perform_Reaction (flow_rate=52, time_pumping=295, voltage=7, current=4.3)
    await asyncio.sleep(1) 
   
async def process_devices_command_queue(*active_components):
    #prints message queue
    logger.info('############### STARTS PROCESSING DEVICES COMMAND QUEUE ################')
    devices = [*active_components]
    while True:
        logger.info('starting loop ...')
        for i in range(len(devices)):
            logger.info(devices[i].message_queue)
            await devices[i].message_queue.get()
            await devices[i].message_queue.join()
            await asyncio.sleep(2)


async def main(closedloop = True, *active_components):
    #main function
    #initializes serial port and devices
    #starts 
    devices = [GSIOCProtocol(port_name=port)]
    await devices[0]._initialize_port()

    logger.info('starting')

    task_list = []
    for i in range(len(devices)):
        task_list.append(asyncio.create_task(process_devices_command_queue(devices[i])))
    await asyncio.gather(initialize(devices[i]),*task_list)

    logger.info('############### STARTUP Finished ################')
    if(closedloop):
        logger.info('############### Entering Closed Loop ################')

    else:
        logger.info('############### Running Direct Commands ################')


asyncio.run(main())


