################################################################################################
# A DataLogger instance holds a configured Reader instance and one or more configured Writer
# instances. All these instances might be configured from a configuration file, by 
# parameterization during instantiation of a DataLogger instance or later on using initialize_atts 
# or load_config. A config loader might be chosen for different formats.
#
# Repeated use of the given configuration methods will overwrite already set attributes except
# for writers. Any new writer configuration will result in a new Writer instance appended to 
# _writers!
################################################################################################
import logging
from os import path
from loader import getConfigLoader
from readers import * 
from writers import * 
from utils import Reducer

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s:[%(levelname)s][%(module)s][%(funcName)s][%(lineno)d] %(message)s',level=logging.INFO)


class DataLoggerBroker(object):

	def __init__(self,config_fname=None,**kwargs):
		"""
		config or kwargs include one reader class and all parameters to instantiate a reader 
		plus one or more writer classes and there respective parameters including a list of filters.
		"""
		self._reader = None
		self._writers = []
		if config_fname:
			self.load_config(config_fname)
		self.initialize_atts(**kwargs)
			
		
	def initialize_atts(self, **kwargs):	
		for k,v in kwargs.items():
			if k == 'reader_cfg':
				reader_cfg = kwargs.get('reader_cfg')
				reader_cls = reader_cfg.pop('reader_cls')
				logger.debug(reader_cls)
				self.setReader(reader_cls,**reader_cfg)
				@self._reader.onread
				def handle_input(event):
					for writer in self._writers:
						writer.write(event.message)
			elif k.casefold().find('writer')>-1:
				writer_cfg = kwargs.get(k)
				writer_cls = writer_cfg.pop('writer_cls')
				self.addWriter(writer_cls,**writer_cfg)
			else:
				setattr(self,'_'+k,v)
			
	def load_config(self,config_fname):
		"Any loader must provide a load method, that reconstructs classes from class names"
		try:
			self._get_loader(config_fname)
			with open(config_fname) as f:
				config = self._config_loader.load(f)
			self.initialize_atts(**config)
		except Exception as e:
			logger.error(f'ERROR: {e}')
			
	def _get_loader(self,config_fname):
		"The right loader class will be guessed from the filename extension"
		basename,ext = path.splitext(config_fname)
		self._config_loader = getConfigLoader(ext.casefold())
			
	def addWriter(self, writer_cls, **kwargs):
		logger.debug(f"Appending {writer_cls} with {kwargs}")
		self._writers.append(writer_cls(**kwargs))
	
	def setReader(self, reader_cls,**kwargs):
		logger.debug('Setting reader')
		self._reader = reader_cls(**kwargs)
		
	def run(self):
		self._reader.run( self._reader.read_forever )

if __name__=='__main__':
	'''
	Datalogger starten
	'''
	import argparse
		
	server = argparse.ArgumentParser(description="Startet einen Datalogger")
	server.add_argument("-o", "--cfg", help="Pfad zur config-Datei", type=str)
	opts = server.parse_args()
	dl = DataLoggerBroker(config_fname = opts.cfg)
	try:
		dl.run()
	except KeyboardInterrupt:
		logger.warning('Main loop closed.')

