import io, json, asyncio, logging, sys, re
from datetime import datetime
import serial
from bleak import BleakClient, BleakError
from utils import getObserver, get_serial_if_fname
from parsers import *

logger = logging.getLogger(__name__)

class DataLogger:

	def __init__( self, tty, **kwargs):
		self.no_lines = 1
		self.name = tty
		self.observer = getObserver(tty)
		self.onread = self.observer.register	# allow registering with @onread!
		self.has_started_logging = False

	def __enter__(self):
		self.connect()
		return self._uart
		
	def __exit__(self, err_type, err_val,err_trace):
		self.disconnect()
		
	def connect(self):
		logger.debug(f"Connecting to {self.name}...")
		self._uart = serial.Serial( self.name )
		# Should be shorter than the time gap between 2 messages and longer
		# than the time gap between 2 bytes to discern messages this way 
		self._uart.timeout = 0.1 
		self.flush_input()
		logger.info("Data logger is connected!")
	
	def disconnect(self):
		self._uart.close()
		logger.info(f"Disconnected reader from {self.name}")
		
	def run(self,fun,**kwargs):
		try:
			asyncio.run(fun(**kwargs))
		except asyncio.TimeoutError as e:
			logger.error("TimeoutError: Couldn't establish a connection in the given time frame")
			sys.exit(2)
	
	def flush_input(self):
		self._uart.flushInput()
	
	def _has_started_logging(self, word):
		if self.has_started_logging:
			return True
		elif self._parser.matches_init_condition(word):
			self.has_started_logging = True
			return True
		return False

	def readline(self):
		j = b''
		# Assume, timeout allows for discerning messages
		while not j: 
			j = self._uart.readline()
		logger.debug(j)
		return j.decode('ascii')

	def readlines(self):
		"""
		Generator in case a complete dataset is formed by multiple lines
		"""		
		n = 0
		while n < self.no_lines:
			w = self.readline()
			if not w:
				continue
			if self._has_started_logging(w):
				n+=1
				yield w
			else:
				continue
	
	async def read_forever(self):
		with self:
			while True:
				msg = dict(timestamp=dict(value=round(datetime.now().timestamp()*1000),unit='msec'))
#				try:
				if self.no_lines == 1:
					line = self.readline()
					logger.debug(f'Read {line} from {self.name}')
					msg.update(self._parser.parse_word(line))
				else:
					lines = self.readlines()
					for line in lines:
						msg.update(self._parser.parse_word(line))
				self.observer.notify(message=msg)
				logger.debug('Notified observer!')
#				except ValueError as e:
#					logger.error(e)
#					continue
#				except asyncio.CancelledError:
#					logger.error('Process interrupted')
#					break
#				except KeyboardInterrupt:
#					logger.error('Process interrupted')
#					break
#				except Exception as e:
#					logger.error(e)
#					continue

##############################################################################################
# T e s t L o g g e r
class TestLogger(DataLogger):
	
	def connect(self):
		self._parser = Parser()
		self._uart = io.StringIO('Nur ein Test')
	
	def readline(self):
		return self._uart.readline()

##############################################################################################
# P C E A Q D 2 0 
pat_PCEAQD20 = re.compile('FTDI USB Serial Device converter now attached to (ttyUSB\d)')

class PCEAQD20(DataLogger):

	def __init__(self, tty = None, **kwargs):
		tty = get_serial_if_fname(pat_PCEAQD20)
		super().__init__(tty,**kwargs)
		self.no_lines = 5
		self._parser = PCEAQD20Parser()

	def connect(self):
		super().connect()
		self._uart.timeout = 0.5
		self._sio = io.BufferedReader(self._uart)
	
	def readline(self):
		j = self._sio.readline(16)
		logger.debug(f"Read {j} from interface {self.name}")
		return j.decode('ascii')

##############################################################################################
# P l a n t o w e r 
pat_plantower = re.compile('ch341-uart converter now attached to (ttyUSB\d)')
class Plantower(DataLogger):
	"""
	Unfortunately the interface of the underlying
	sensor is completely undocumented. But the 
	product comes with software that allows
	for guessing some parameters. Sending of data
	("readymade" json strings) must be triggered by 
	the client. The sensor itself is well documented.
	"""

	def __init__(self,tty = None,**kwargs):
		tty = get_serial_if_fname(pat_plantower)
		super().__init__(tty,**kwargs)
		self._parser = PlantowerParser()
		
	def connect(self):
		super().connect()
		self._uart.baudrate = 115200
		self._uart.timeout = 0.1
		self.start_sending()
	
	def disconnect(self):
		self.stop_sending()
		super().disconnect( )
		
	def start_sending(self):
		return self._uart.write(b'{"fun":"05","flag":"1"}')

	def stop_sending(self):
		return self._uart.write(b'{"fun":"05","flag":"0"}')
		
	def get_config(self):
		self._uart.write(b'{"fun":"80"}')
		return self.readline()

##############################################################################################
# B l u e t o o t h L o g g e r 
class BluetoothLogger(DataLogger):
	""""
	Based on bleak. Reads from a specified service or specified characteristic.  While the serial 
	readers have direct access to the interface the BleakClient does not. The BleakClient 
	registers a callback at the dbus to receive data. Such the bluetooth reader works a little
	different.
	"""

	# TODO: Extend for reading ESS data
	
	async def __enter__(self):
		await self.connect()
		return self._uart
		
	async def __exit__(self, err_type, err_val,err_trace):
		await self.disconnect()
		
	def __init__(self, identifier, uuid, is_characteristic = False):
		self.name = identifier
		self.observer = getObserver(identifier)
		self.onread = self.observer.register	# allow registering with @onread!
		self.ble = BleakClient(identifier)
		self.uuid = uuid
		if is_characteristic:
			self.characteristic = uuid 
		self.line={}
		
	async def connect(self):
		try:
			await self.ble.connect()
			logger.info('Bluetooth data logger is connected!')
		except Exception as e:
			logger.error(e)
			return False
		return True
	
	async def readline(self):
		raise NotImplementedError

	async def read_forever(self):
		logger.info(f"Connecting to BluetoothLogger {self.name}...")
		async with self.ble as client:
			logger.info(f"Connected to BluetoothLogger {self.name}.")
			await client.start_notify(self.characteristic, self.handle_data)
			while True:
				try:
					await asyncio.sleep(60)
				except KeyboardInterrupt:
					break
				except asyncio.CancelledError:
					break
			logger.info('BluetoothLogger has been disconnected')
	
	def handle_data(self,sender,data):
		msg = self._parser.parse(data)			
		self.observer.notify(message=msg)
	
	async def disconnect(self):
		await self.ble.disconnect()
		logger.info('Bluetooth data logger is disconnected!')
		
##############################################################################################
# X i a o m i M i T e m p e r a t u r e L o g g e r
class XiaomiMiTemperatureLogger(BluetoothLogger):
	
	def __init__(self, identifier, uuid, is_characteristic = False):
		super().__init__(identifier, uuid, is_characteristic)
		self._parser = XiaomiMiTemperatureLoggerParser()

