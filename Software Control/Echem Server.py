import asyncio
import os
import logging
from datetime import datetime
from asyncua import Server, ua

async def main():
    # Serversetup
    server = Server()
    server.name = "LiquidHandlerCommunicationServer"     
    await server.init()

    server.set_endpoint("opc.tcp://introduce IP/LiquidhandlerCommunication/")
    server.set_server_name("LiquidHandlerCommunication")
    uri = "liquidhandler"
    idx = await server.register_namespace(uri)

    LiquidHandler = await server.nodes.objects.add_object(idx, "LiquidHandler")

    start = await LiquidHandler.add_variable(idx,"Start", 0)
    await start.set_writable()

    recipe = await LiquidHandler.add_variable(idx, "Recipe", [1,100,2,100,3,100,4,100])
    await recipe.set_read_only()

    recipeSTR = await LiquidHandler.add_variable(idx, "RecipeSTR", "1,100,2,100,3,100,4,100")
    await recipeSTR.set_writable()

    uptime = await LiquidHandler.add_variable(idx, "uptime", 0)
    await uptime.set_read_only()

    end = await LiquidHandler.add_variable(idx, "End", 0)
    await end.set_writable()

    print("Starting server!")

    async with server:
        while True:
            await asyncio.sleep(1)
            new_uptime = await uptime.get_value() + 1
            recipeitl = []
            STR = await recipeSTR.get_value()
            listSTR = STR.split(",")
            for s in listSTR:
                recipeitl.append(int(s))
            await recipe.write_value(recipeitl)
            os.system("cls")
            print(new_uptime)
            print(await recipe.get_value())
            print(await start.get_value())
            await uptime.write_value(new_uptime)

if __name__ == "__main__":
    asyncio.run(main())