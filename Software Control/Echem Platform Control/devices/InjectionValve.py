import asyncio
from loguru import logger

class GsiocDirectInjectionModule():
    """
    GSIOC Direct Injection Module.
    """

    def __init__(self, devices) -> None:
        self.port_instance = devices
        self.currentpos = 'I'

    async def switch_to_position(self,destination: str):
        """
        Coro: Contains all the logic to switch GSIOC Direct Injection Module to another position.
        """
        logger.info(f'switching state instruction: {destination}')
        await self.port_instance.connect(device_name='GX D Inject',device_id=3)
        await asyncio.sleep(3)
        if destination != self.currentpos:
            await self.port_instance.b_command('V' + destination)
            self.currentpos = destination
        else:
            logger.info(f'Target Position is same as current position')
            pass