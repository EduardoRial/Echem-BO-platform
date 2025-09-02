from . import rack
import asyncio
import numpy as np
from loguru import logger

class GsiocLiquidHandler():
    """
    GSIOC Liquid Handler
    """
    def __init__(self, devices) -> None:
        self.port_instance = devices
        self.dim_location = [147,0.5,95]
        self.current_location = [0,0,125]
        self.rack = rack.Rack()
        self.volume = 100 # μL (Liquid Handler Needle)


    def load_rack(self) -> None:
        pass
    
    async def switch_to_position(self, destination = [0,0,0], DIM = False) -> None:
        """
        Coro: Contains all the logic to change the position of GSIOC Liquid Handler to any position.
        """
        await self.port_instance.connect(device_name='GX 241',device_id=33)
        await asyncio.sleep(1)

        if DIM:
            x,y,z = self.dim_location
            logger.info(f'Changing position to injection location ... X{x}/{y}')
            await self.port_instance.b_command('H')
            await asyncio.sleep(2)
            await self.port_instance.b_command(f'SX{x}/{y}')
            await asyncio.sleep(1)
            await self.port_instance.b_command(f'SZ{z}:50:30')
            self.current_location = [x,y,z]
            await asyncio.sleep(5)
    
        else:
            x,y = destination
            z = 75
            logger.info(f'Changing position to location ... X{x}/{y}')
            await self.port_instance.connect(device_name='GX 241',device_id=33)
    
            await self.port_instance.b_command('H')
            await asyncio.sleep(2)
            await self.port_instance.b_command(f'SX{x}/{y}')
            await asyncio.sleep(1)
            await self.port_instance.b_command(f'SZ{z}:50:30')
            self.current_location = [x,y,z]

    async def go_home(self) -> None:
        await self.port_instance.connect(device_name='GX-241',device_id=33)
        await self.port_instance.b_command('H')
        await asyncio.sleep(1)