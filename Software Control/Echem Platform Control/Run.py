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

'This file allows to perform automated experiments by reading the experimental conditions from a server'

async def initialize(ports):

    await run_client(ports)

async def run_client(ports):

    url = "opc.tcp://143.50.141.23:4840"
    # url = "opc.tcp://143.50.141.42:4840"
    namespace = "liquidhandler"
    client = Client(url=url, timeout=4)

    try:
        print(f"Connecting to {url} ...")
        await client.connect()
        node = client.get_node("ns=2;i=1;NodeIdType=<NodeIdType.FourByte: 1>")
        nsidx = await client.get_namespace_index(namespace)
        root = client.nodes.root
        objects = client.nodes.objects
        StartVar = await client.nodes.root.get_child(
        ["0:Objects", "2:LiquidHandler", "2:Start"])
        EndVar = await client.nodes.root.get_child(
        ["0:Objects", "2:LiquidHandler", "2:End"])
        UptimeVar = await client.nodes.root.get_child(
        ["0:Objects", "2:LiquidHandler", "2:uptime"])
        RecipeVar = await client.nodes.root.get_child(
        ["0:Objects", "2:LiquidHandler", "2:Recipe"])
        print(await UptimeVar.get_value())
        await run_closed_loop(StartVar, EndVar, RecipeVar, ports)

    except Exception as e:
        print(e)
        return

async def run_closed_loop(StartVar, EndVar, RecipeVar, ports):
    Start = 0
    End = 0
    print("Loop Started")
    while True:
        Start = await StartVar.get_value()
        End = await EndVar.get_value()
        print(Start)
        print(End)
        await asyncio.sleep(1)

        if (Start == 1) and (End == 0):
            await asyncio.sleep(2)
            Recipe = await RecipeVar.get_value()
            print(Recipe)
            await runSlug(ports, Recipe, EndVar)
            await EndVar.write_value(1)

        if (Start == 0) and (End == 1):
            await EndVar.write_value(0)

async def runSlug(ports, Recipe, EndVar):
    proc = Procedures.ProcedureObject(ports)
    logger.info("start")
           
    dictionary_reagents_substances = {}
    list_of_dictionaries = []
    k = 0 
    for j in range (len(Recipe)):
        even = Recipe[4::2]
        odd = Recipe[5::2]
        if k < len (even):
            vial = even[k]
            volume_vial = odd[k]
        
            k = k + 1

        else:
            break

        dictionary_reagents_substances[vial] = volume_vial

        list_of_dictionaries.append(dictionary_reagents_substances)

        flow_rate = Recipe[0]
        time_pumping = Recipe[1]
        voltage = Recipe[2]
        current = Recipe[3]/100 #It is easier to use integers for the number values and later divide them to get the decimals
            

    print (dictionary_reagents_substances)
    print (f"The current is {current} mA, the voltage is {voltage} V, the flow rate is {flow_rate} uL/min and the reaction time is {time_pumping} s")
        
    await proc.SlugFormation(dictionary_reagents_substances)
    
    await Asia_syringe_pump.main(1000,0,14.5) #transfer slug from sample loop to reactor
    await proc.Perform_Reaction (flow_rate, time_pumping, voltage, current)
    
    await EndVar.write_value(1)
    # print(Recipe)
    logger.info("done")
   
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


