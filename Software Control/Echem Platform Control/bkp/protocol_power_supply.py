# -*- coding: utf-8 -*-
import asyncio
from loguru import logger
import serial_asyncio
import numpy as np

# functions/classes needed to be exported
__all__ = ['BKPrecisionRS232']


class BKPrecisionRS232():
	f"""
	Protocol methods to communicate with B+K PRECISION 1739 Revion 1.3


	:param port_name: Name of the RS-232 port (COM** on Windows, ttyS** on Linux)
	:param device_idn: Name of the device, has to equal the response of the device. Default is B+K PRECISION 1739 Revion 1.3.
	:commands:
	* 'OUT ON\r'              	activates power output
	* 'VOLT 10.00\r' 			range 00.00 - 30.00
	* 'CURR 100.0\r'          	range 000.0 - 999.9
	* 'VOLT?\r'               	queries the voltage in (V) - the same value as at the display
	* 'VOLT?\rCURR?\rSTAT?\r'  	use multiple commands to query different settings at the same time
	* 'CURR?\r'               	queries the current in (mA) - the same value as at the display
	* 'STAT?\r'               	queries the mode: either constant voltage (CV) or constant current (CC)
	* 'IDN?\r'                	queries the identity number of the device
	* 'SAVE\r'                	sets the parameters 3 sec after the last command
	* 'OUT OFF\r'             	deactivates power output
	"""
	BAUDRATE = 9600

	def __init__(self, port_name: str, device_idn: str = 'B+K PRECISION 1739 Revision 1.3') -> None:
		self.port_name = port_name
		self.device_idn = device_idn
		self.communication_initiator = b'\x13' # Communication initiation signal.
		self.communication_terminator = b'\x11' # Communication termination signal.
		self.sol = b'' # Start of command signal "start of line".
		self.eol = b'\r' # End of command signal "end of line".

		self.message_queue = asyncio.Queue() # a FIFO queue to process only one command at a time from multiple methods throughout the script.

		self._reader: asyncio.StreamReader = None  
		self._writer: asyncio.StreamWriter = None  

		self.error_responses = {
		"Communication Error\r": ": RS232 framing, parity, or overrun error",
		"Syntax Error\r": ": invalid syntax was found in the command string",
		"Out Of Range\r": ": a numeric parameter value is outside the valid range for the command"
		}

	# @error_handler(repititions=2)
	# @logging_handler
	async def initialize_connection(self) -> str:
		"""Coro: Opens RS232 connection. Verifies the device identity.
		:returns: 'Initialisation successfull.' if device identity as excpected or 'Initialisation failed.' if not."""
		future = serial_asyncio.open_serial_connection(url=self.port_name, baudrate=self.BAUDRATE)
		self._reader, self._writer = await asyncio.wait_for(future, timeout=30)
		if await self.verify_connected():
			logger.debug(f'Initialisation successfull, connected to {self.device_idn}')
			return 'Initialisation successfull.'
		else:
			logger.critical(f'Connected to wrong device: {self.send_command("IDN?")}')
			return 'Initialisation failed.'
			
	# @logging_handler
	async def close_port(self) -> None:
		"""Coro: Closes the async writer instance."""
		self._writer.close() 

	# @error_handler(repititions=2)
	# @logging_handler
	async def send_encoded_command(self, encoded_command) -> None:
		"""Sends a command. Does not wait for a response.
		:param encoded_command: Valid device command in binary."""
		self._writer.write(encoded_command)
		logger.debug(f"SENDING >>> '{encoded_command.decode('ascii')}' (RAW: {encoded_command})")
		# logger.debug(f'Raw data sent: {encoded_command}')

	# @logging_handler
	async def receive_one_byte(self) -> bytes:
		"""Receives one byte at a time from the port. Does not send anything.
		:returns: One received byte."""
		received = await self._reader.read(1)
		# logger.debug(f'Raw data received: {received}')
		return received

	# @logging_handler
	async def verify_connected(self) -> bool:
		"""Coro: Verifies that the device is connected by quering the identity.
		:returns: True if connected, else False."""
		idn = await self.send_command('IDN?') # valid command for "B+K PRECISION 1739 Revision 1.3". Expected to get the IDN back.
		if idn == self.device_idn:
			logger.debug(f'Device verified successfully as {idn}')
			return True
		else:
			logger.critical(f'Connected to wrong device: {idn}. expected: {self.device_idn}')
			return False

	# @logging_handler
	async def verify_device_active(self) -> bool:
		"""Coro: Checks from the device response if it is in Power On state. 
		:returns: True if active, else False."""
		status = await anext(await self.send_commands('STAT?'))
		if status in ['OFF','CC','CV']:
			logger.debug(f'Device active.')
			return True
		else:
			logger.debug(f'Device inactive.')
			return False

	# @logging_handler
	def encode_command(self, uncoded_command: str, _encoding: str = 'ascii') -> bytes:
		"""Encoding to a valid binary command.
		:param uncoded_command: Command string.
		:param _encoding: (optional) Encoding keyword ('ascii','utf-8')"""
		command_encoded = self.sol + bytes(uncoded_command.encode(encoding=_encoding)) + self.eol
		return command_encoded

	# @logging_handler
	async def collect_response(self) -> bytearray:
		"""Coro: Collects response byte by byte.
		:returns: Whole response until termination sign as bytearray."""
		response_bytes = bytearray()
		while True:
			response_byte = await self.receive_one_byte()
			if response_byte == self.communication_initiator:
				response_bytes.extend(response_byte)
				while True:
					body_response_byte = await self.receive_one_byte()
					if body_response_byte == bytes(self.communication_terminator):
						response_bytes.extend(body_response_byte)
						break
					else:
						response_bytes.extend(body_response_byte)
				# logger.info(f'received: {response_bytes}')
				return response_bytes
			else:
				logger.debug(f'Received invalid response: {response_byte}. Expected: {self.communication_initiator}')
				await self.verify_device_active()
				continue
	
	# @logging_handler
	def format_response(self, response: bytearray) -> str:
		"""Stripps off all initiation and termination signs.
		:param response: Device response as bytearray.
		:returns: Modified response as string."""
		stripped_response = response.replace(self.sol,b'')
		stripped_response = stripped_response.replace(self.eol,b'')
		stripped_response = stripped_response.replace(self.communication_initiator,b'')
		stripped_response = stripped_response.replace(self.communication_terminator,b'')
		stripped_response = stripped_response.decode('ascii')
		return stripped_response

	# @logging_handler
	def verify_response(self, initial_command: str, formatted_response: str) -> bool:
		"""Verifies that the response is valid. Returns a bool.
		:param initial_command: Command that lead to the response.
		:param formatted_response: Response that has been properly formatted.
		:returns: True if response is valid, else False."""
		if '?' not in initial_command:
			if formatted_response == '':
				return True
			elif formatted_response + '\r' in list(self.error_responses.keys()):
				return True 
			else:
				return False
		else: 
			if formatted_response != '':
				return True
			else:
				return False

	# @logging_handler
	def interpret_response(self, single_command: str, verified_response: str) -> str:
		"""Interprets the response (error, success, failure) according to device documentation.
		:param single_command: Command as string.
		:param verified_response: Allowed response as string.
		:returns: "Device successfully set: [value]", "Device value is: [value] or interpreted device error message."""
		modified_verified_response = verified_response + '\r'
		if modified_verified_response in self.error_responses.keys():
			logger.critical(f'The following error occured: {verified_response},\ninterpretation: {self.error_responses.get(modified_verified_response)}')
			return self.error_responses.get(verified_response)
		elif verified_response == '':
			return f'Device successfully set: {single_command}'
		elif verified_response != '':
			return f'Device value is: {verified_response}'

	# @error_handler(repititions=2)
	# @logging_handler
	async def send_command(self,single_command: str) -> str:
		"""Coro: Encodes and sends command. 
		:param single_command: command as a string.
		:returns: Formatted response as string."""
		await self.send_encoded_command(encoded_command=self.encode_command(uncoded_command=single_command))
		resp_raw = await self.collect_response()
		resp = self.format_response(resp_raw)
		logger.info(f"RECEIVING <<< '{resp}' (RAW: {resp_raw}) ")
		if self.verify_response(initial_command=single_command,formatted_response=resp):
			# logger.critical(self.interpret_response(single_command=single_command, verified_response=resp))
			return resp

	# @logging_handler
	async def send_commands(self,*args: str) -> None:
		"""Generator: Sends multiple command arguments and yields their response values.
		:param *args: multiple command arguments as string."""
		for i in [*args]:
			yield await self.send_command(i)
			


########## TESTING SECTION ###########

# @error_handler(repititions=1)
# @logging_handler
async def main():
	global bkp
	bkp = BKPrecisionRS232('COM4')
	await bkp.initialize_connection()
	await asyncio.gather(bkp.start_monitoring(time_interval=0.5), bkp.stop_monitoring(delay=10))
	await bkp.close_port()
	
if __name__ == '__main__':
	asyncio.run(main(bkp))