# -*- coding: utf-8 -*-
import serial_asyncio
import asyncio
from loguru import logger
import binascii
import time
import sys
import serial
import numpy as np

# functions/classes needed to be exported
__all__ = ['GSIOCProtocol']

class GSIOCProtocol():
    """Protocol for Gilson Serial Input/Output Channel (GSIOC) master/slave communication. 
    Slave unit ID's: 0-63 (communication with only one at a time)
    Valid Baudrates: 19200 (default), 9600, 4800
    clock rate: not required due to asynchronous communication. Clock rate is sixteen times the baudrate.
    GSIOC Termination: 'passive termination' (recommended) by wating >20 ms or 'break active' by master through break character
    Control/Command Character Format: asynchronous, eight bit, even parity, half duplex, one or two stop bits.
        * ASCII '0'-'127' (hexadecimal '0'-'7F') are valid data characters.
        * extended ASCII '128'-'191' (hexadecimal '80'-'BF') from master connect slave with unit ID's 0-63.
        * ASCII '192'-'255' (hexadecimal 'CO'-'FF') disconnects every slave module.
        * ASCII '127'-'255' from slave indicate final character of a slaves response to an immediate command."""
    def __init__(self, port_name: str = 'COM3', baudrate: int = 19200) -> None:
        self.port_name = port_name
        self.baudrate = baudrate
        self.eol = b'\r'
        self.overall_communication_attempts = 5
        self.message_queue = asyncio.Queue() # a FIFO queue to process only one command at a time from multiple methods throughout the script.

        self._reader: asyncio.StreamReader = None
        self._writer: asyncio.StreamReader = None
        self.port_open = False

    def __repr__(self) -> str:
        return f'<port name: {self.port_name}, port initialised: {self.port_open}>'

    async def _initialize_port(self):
        """Coro: Initializes the serial port.
        :raises: Raises Exception when opening port fails: serial_asyncio.serial.SerialException, ConnectionError, asyncio.TimeoutError"""
        future = serial_asyncio.open_serial_connection(url=self.port_name, baudrate=self.baudrate)
        # Future used to set shorter timeout than default
        logger.info(f'try to initialise a port called {self.port_name}.')
        try:
            self._reader, self._writer = await asyncio.wait_for(future, timeout=30)
            self.port_open = True
        except serial_asyncio.serial.SerialException as serial_error:
            logger.exception(serial_error)
            pass
            # raise Exception(f"Could not find a port {self.port_name}. Probably the 'USB to RS232' converter is not connected.") from serial_error
        except ConnectionError as connection_error:
            logger.exception(connection_error)
            raise Exception(f"Cannot open connection with device {self.__class__.__name__} at port={self.port_name}") from connection_error
        except asyncio.TimeoutError as timeout_error:
            logger.exception(timeout_error)
            raise Exception(f"No reply from device {self.__class__.__name__} at port={self.port_name}") from timeout_error

    async def connect(self, device_name: str, device_id: int):#device_name: str = 'GX-241 II', device_id: int = 33):
        """Coro: Connect another device via GSIOC Protocol.
        1. master sends ASCII '255' (hexadecimal 'FF') to disconnect all slaves from the GSIOC
        2. master ensures that no slaves are active: 'passive termination' wait >20 ms
        3. master sends binary name of the desired slave device (unit ID + 128). e.g.: 16 -> 10010000
            :: Note the difference between unit ID's and binary name (set high bit for unit's binary name)!
            1. slave connects and echos its binary name to master (timeout after 20 ms, slave unavailable).
            2. master may send 'immediate' or 'buffered' command.
            3. slave remains active until it receives any disconnect code or the binary name of a different slave.
        """
        logger.info(f'Attempting connection to device ID: {device_id}')
        self._writer.write(binascii.a2b_hex('FF'))#bytes.fromhex('FF'))
        await asyncio.sleep(0.2)
        slave_binary_name = int(device_id + 128).to_bytes(1,'big')#binascii.a2b_qp(str(device_id+128))##bin(int(device_id+128))
        self._writer.write(slave_binary_name)
        future_echo = self._reader.read(10)
        logger.info(f'sent: {slave_binary_name}, received echo: {future_echo}')
        try:
            slave_echo = await asyncio.wait_for(future_echo, timeout=50)
            logger.info(f'sent: {slave_binary_name}, received echo: {slave_echo}')
            logger.info(f'sent (in human words): {slave_binary_name}, received echo: {slave_echo}')
            if bytes.fromhex('7F') <= slave_echo <= bytes.fromhex('FF'):# and slave_echo == device_id:# slave_binary_name: # len(slave_echo) > 0:
                device_name = await self.i_command('%')
                logger.info(f'Verified device as {device_name}')
                logger.info(f'Connected successfully to slave name {device_name}')
                logger.info(f'Slave unit id {device_id}, name {device_name}, echoed {slave_echo}')
                return device_name
            else:
                if self.overall_communication_attempts > 0:
                    self.overall_communication_attempts -= 1
                    logger.info(f'Invalid echo: Slave unit id {device_id}, name {device_name}, echoed {slave_echo}')
                    await asyncio.sleep(0.2)
                    await self.connect(device_name, device_id)
        except asyncio.TimeoutError as timeout_error:
            logger.exception(timeout_error)
            raise Exception(f"No reply from slave unit id {device_id}, name {device_name}, at port {self.port_name}") from timeout_error

    async def close_port(self):
        """Coro: Close writer instance."""
        self._writer.close()

    async def i_command(self, i_command: str) -> str:
        """
        Coro: Immediate Command (according to GSIOC Protocol).
        
        Sends the input string as binary to the GSIOC object and reads one response character.
        If no response before timeout, it waits another time until self.overall_communication_attempts is reached. 
        If the response byte is <= 127 it signals being ready for the next byte by answering with hexadecimal "06".
        If the response byte is > 127 (signals end of message) the response is considered complete and the function returns.
        
        :param i_command: A string argument which is sent to the GSIOC object over RS-232.
        :return: Returns the response message as string.
        :raises: Exception if input string is longer than 1.
        """
        if len(i_command) != 1:
            raise Exception('Immediate commands can solely transmit single character strings.')
        machine_i_command = i_command.encode('ascii')
        self._writer.write(machine_i_command)
        response_message = bytearray(0)
        while True:
            future_echo = self._reader.read(10)#until(separator=b'\xe8')
            slave_echo = await asyncio.wait_for(future_echo, timeout=100)
            logger.info(f'during immediate command, slave responded with {slave_echo}.')
            if len(slave_echo) == 0:
                if self.overall_communication_attempts > 0:
                    self.overall_communication_attempts -= 1
                    pass
            if slave_echo[0] == b'\x00':
                logger.info(f'The response {slave_echo[0]} case occured.')
                continue
            response_message.append(slave_echo[0])
            if response_message[-1] > 127:
                response_message[-1] -= 128
                logger.info(f'sending immediate command complete. Received: {response_message}')
                break
            
            else:
                self._writer.write(bytes.fromhex("06"))
        logger.info(f'response message: {response_message}')
        return response_message

    async def b_command(self, b_command) -> str:
        """
        Coro: Buffered Command (according to GSIOC Protocol).
        
        Appends a Line Feed (LF = \n) and Carrier Return (CR = \r) character to the input string.
        It sends the LF character to the connected GSIOC slave device until the slave responds with the ready signal byte "10", LF.
        A "#" (byte "35") response signals the slave is busy at the moment.
        After LF received from slave, the message is sent from master one character at a time and it expects the exact same character as a response from slave.
        The function is terminated when the last character CR is received back from slave.

        :param b_command: String which is sent to the connected GSIOC object via RS-232.
        :return: Returns the response from connected slave as a string.
        """
        machine_b_command = '\n' + b_command + '\r'
        response = bytearray(0)
        
        while True:
            self._writer.write(machine_b_command[0].encode('ascii'))
            future_echo = self._reader.read(10)
            slave_echo = await asyncio.wait_for(future_echo, timeout=20)
            if len(slave_echo) == 0:
                if self.overall_communication_attempts > 0:
                    self.overall_communication_attempts -= 1
                    pass
            logger.info(f'slaves echo is: {slave_echo[0]}')
            
            if slave_echo[0] == 35: # b'#':
                logger.info('device is busy ... ')
                pass
            elif slave_echo == b'\n':
                response.append(slave_echo[0])
                logger.info(f'condition slave echo == eol is true...')
                break
        
        for i in range(len(machine_b_command)-1):
            await asyncio.sleep(0.2)
            buffered_machine_command = machine_b_command[i+1].encode('ascii')
            self._writer.write(buffered_machine_command)

            future_echo = self._reader.read(3)
            slave_echo = await asyncio.wait_for(future_echo, timeout=30)
            logger.info(f'during buffered command, slave responded with {slave_echo}.')
            if len(slave_echo) == 0:
                if self.overall_communication_attempts > 0:
                    self.overall_communication_attempts -= 1
                    pass
            response.append(slave_echo[0])
            if slave_echo != buffered_machine_command:
                #logger.info(f'Invalid response from slave: {slave_echo}. Expected: {buffered_machine_command}')
                pass
            if slave_echo == b'\r':
                logger.info(f'whole response: {response}')
                return response