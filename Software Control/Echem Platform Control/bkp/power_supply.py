
import sys
from bkp import *
from bkp.protocol_power_supply import BKPrecisionRS232
import numpy as np
from loguru import logger
import asyncio
import time
from bkp import *

__all__ = ['BKPrecisionPowerSupply']

###################################################################################
############# available commands for B+K PRECISION 1739 Revision 1.3 ##############
OUT_ON = 'OUT ON'              #activates power output
# SET_VOLT =  'VOLT 10.00\r'          #range 00.00 - 30.00
# SET_CURRENT = 'CURR 100.0\r'          #range 000.0 - 999.9
GET_VOLT = 'VOLT?'               #queries the voltage in (V) - the same value as at the display
GET_CURRENT = 'CURR?'               #queries the current in (mA) - the same value as at the display
GET_STATUS = 'STAT?'               #queries the mode: either constant voltage (CV) or constant current (CC)
GET_IDENTITY = 'IDN?'                #queries the identity number of the device
GET_ALL = ['VOLT?','CURR?','STAT?','IDN?'] #use multiple commands to query different settings at the same time
SAVE = 'SAVE'                #sets the parameters 3 sec after the last command
OUT_OFF = 'OUT OFF'             #deactivates power output
###################################################################################


class BKPrecisionPowerSupply():
    """Represents the 'B+K PRECISION 1739 Revision 1.3' Power Supply."""
    def __init__(self, communication_protocol: BKPrecisionRS232, current_max: float|int = 999.9, voltage_max: float|int = 30.0) -> None:
        super().__init__()
        self.current_max = current_max
        self.range_current = [0,self.current_max] # settable current values specific for BK Precision 1739 (30V / 1A)
        self.voltage_max = voltage_max
        self.range_voltage = [0,self.voltage_max] # settable current values specific for BK Precision 1739 (30V / 1A)
        self.communication_protocol = communication_protocol
        self.monitoring = None

    async def initialize_device(self) -> None:
        """Coro: Contains all the logic to set the device to its initial state."""
        await self.communication_protocol.initialize_connection()
        check = 'OFF'
        while True:
            responses = []
            async for response in self.communication_protocol.send_commands(OUT_OFF,*GET_ALL):
                responses.append(response)
            logger.info(f'INITIALISAITON INFO: {responses}')
            if check in responses:
                await self.set_voltage(0.0)
                await self.communication_protocol.send_command(SAVE)
                await self.set_current(0.0)
                await self.communication_protocol.send_command(SAVE)
                break
            else:
                logger.critical(f'response {responses} during initialisation not as expected ({check}), resends initialisation commands...')
                continue

    async def close_port(self):
        await self.communication_protocol.close_port()
        
    async def set_current(self, current: float|int) -> None:
        """Coro: Contains all the logic to set a current to a specific value.
        :param current: Current in mA as float."""
        if current <= 0:
            await self.communication_protocol.send_command(OUT_OFF)
        else:
            valid_current_command = self.get_valid_current_commands([current])[0]
            await self.communication_protocol.send_command(valid_current_command)
            await self.communication_protocol.send_command(OUT_ON)
            logger.info(f'CURRENT SET TO {current} (mA)')


    async def get_current(self) -> float:
        """Coro: Contains all the logic to query the current from the device.
        :returns: Current in mA as a float."""
        while True:
            current_response = await self.communication_protocol.send_command(GET_CURRENT)
            if current_response == None:
                continue
            elif current_response == 'OFF':
                current_response = float(0)
            else:
                current_response = current_response.replace('mA','')
            logger.info(f'CURRENT IS CURRENTLY {current_response} (mA)')
            return float(current_response)


    async def set_voltage(self, voltage: float|int) -> None:
        """Coro: Contains all the logic to set a voltage to a specific value.
        :param voltage: Voltage in V as float."""
        valid_voltage_command = self.get_valid_voltage_commands([voltage])[0]
        await self.communication_protocol.send_command(valid_voltage_command)
        if voltage <= 0:
            await self.communication_protocol.send_command(OUT_OFF)
        else:
            await self.communication_protocol.send_command(OUT_ON)
            logger.info(f'VOLTAGE SET TO {voltage} (V)')

        
    async def get_voltage(self) -> float:
        """Coro: Contains all the logic to query the voltage from the device.
        :returns: Voltage in V as a float."""
        while True:
            voltage_response = await self.communication_protocol.send_command(GET_VOLT)
            if voltage_response == None:
                continue
            elif voltage_response == 'OFF':
                voltage_response = float(0)
            else:
                voltage_response = voltage_response.replace('V','')
            logger.info(f'VOLTAGE IS CURRENTLY {voltage_response} (V)')
            return float(voltage_response)


    async def monitor_power_supply(self, duration: float|int, delay: float|int = 0., monitoring_interval: float|int = 1) -> None:
        """Coro: Runs monitoring tasks for specified seconds.
        :param duration: Duration of monitoring (sec).
        :param delay: Delay before starting monitoring (sec).
        :param monitoring_interval: interval for quering monitored values (sec)."""
        asyncio.gather(
            self.start_monitoring(time_interval=monitoring_interval,delay=delay),
            self.stop_monitoring(delay=duration)
        )


    async def start_monitoring(self, time_interval: float|int = 0., delay: float|int = 0.) -> None:
        """Coro: Monitors all parameters in a certain time interval until self.monitoring is not True.
        :param delay: Delay before starting monitoring (sec).
        :param time_interval: interval for quering monitored values (sec)."""
        logger.info(f'Start monitoring. Time interval: {time_interval} (sec), delay: {delay} (sec).')
        self.monitoring = True
        await asyncio.sleep(delay)
        t1 = time.time()
        while self.monitoring == True:
            t3 = time.time()
            responses = []
            async for response in self.communication_protocol.send_commands(*GET_ALL):
                responses.append(response)
            t2 = time.time()
            logger.info(f"{responses}, time: {round(t2-t1,2)}")
            await asyncio.sleep(time_interval-(t2-t3))

    async def stop_monitoring(self, delay: float|int = 0.) -> None:
        """Coro: Stopps monitoring of BKP values at any time.
        :param delay: Duration before monitoring is stopped (sec)."""
        await asyncio.sleep(delay)
        self.monitoring = False
        if delay > 0:
            delay_note = f' after {delay} (sec).'
        else:
            delay_note = '.'
        logger.info(f'Stopped monitoring{delay_note}')



    def get_valid_current_commands(self, value: list[float|int]) -> list[str]:
        """Transfers numbers in valid current command string arguments.
        :param value: List of float/int to transfer in valid current commands.
        :returns: List of valid current commands from input list of numbers."""
        valid_values = self.format_current(value)
        commands = []
        for valid_value in valid_values:
            commands.append(f'CURR {valid_value}\r')
        return commands

    def get_valid_voltage_commands(self, value: list[float|int]) -> list[str]:
        """Transfers numbers in valid voltage command string arguments.
        :param value: List of float/int to transfer in valid current commands.
        :returns: list of valid voltage commands from input list of numbers."""
        valid_values = self.format_voltage(value)
        commands = []
        for valid_value in valid_values:
            commands.append(f'VOLT {valid_value}\r')
        return commands

    def format_current(self, currents_in: list[float|int]) -> list[str]:
        """Formats an inputted list with numbers (float, int) and returns a formatted list with str() entries like: '020.0'
        :returns: Currents in format xxx.x as list of strings. Appends NaN to the output list if out of device range.
        :raises: Exception/TypeError if the input value is out of device range."""
        currents_out=[]

        for i in range(len(currents_in)):
            n = currents_in[i]
            try:
                if n >= self.range_current[0] and n <= self.range_current[1]:
                    n = float(n)
                    n = "{:.1f}".format(n)
                    n = str(n).zfill(5)
                    currents_out.append(n)
                else:
                    currents_out.append(np.nan)
                    raise Exception(f'Current value "{n}" out of range: {self.range_current}')
                pass
            except TypeError:
                currents_out.append(np.nan)
                raise TypeError(f'Current value "{n}" is not a number')
        else:
            return currents_out

    def format_voltage(self, voltages_in: list) -> list:
        """Formats an inputted list with numbers (float, int) and returns a formatted list with str() entries like: '02.00'
        :returns: Currents in format xx.xx as list of strings. Appends NaN to the output list if out of device range.
        :raises: Exception/TypeError if the input value is out of device range."""
        voltages_out=[]

        for i in range(len(voltages_in)):
            n=voltages_in[i]
            try:
                if n >= self.range_voltage[0] and n <= self.range_voltage[1]:
                    n = float(n)
                    n = "{:.2f}".format(n)
                    n = str(n).zfill(5)
                    voltages_out.append(n)
                else:
                    voltages_out.append(np.nan)
                    raise Exception(f'Voltage value "{n}" out of range: {self.range_voltage}')
                pass
            except TypeError:
                voltages_out.append(np.nan)
                raise TypeError(f'Voltage value "{n}" is not a number')
        return  voltages_out
    


########## TESTING SECTION ##########

async def main():
    await bkp_device.initialize_device()
    await bkp_device.get_current()
    await bkp_device.set_current(130)
    await bkp_device.get_current()
    await bkp_device.set_voltage(23)
    await bkp_device.get_voltage()
    await asyncio.gather( 
         bkp_device.start_monitoring(0.01),
         bkp_device.stop_monitoring(5)
        )
    await bkp_device.set_voltage(0)

if __name__ == '__main__':
    protocol = BKPrecisionRS232('COM4')
    bkp_device = BKPrecisionPowerSupply(communication_protocol=protocol)
    asyncio.run(main())