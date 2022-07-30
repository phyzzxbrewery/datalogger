import logging, json
from os import path
from utils import PlausiChecker
logger = logging.getLogger(__name__)

class Writer(object):
	def __init__(self, filters=[]):
		"For each filter_cfg in filters instantiate Filter and append to _filters"
		self._filters = [PlausiChecker()]
		logger.debug(f"Appended PlausiChecker to {self._filters}")
		for cfg in filters:
			filter_cls = cfg.pop('filter_cls')
			self._filters.append(filter_cls(**cfg))
			logger.debug(f"Appended {filter_cls} to {self._filters}")
	
	def write(self,dataset):
		"""
		For each Filter in _filters process dataset and finally _write_dataset it, if 
		there is something to write. _write_dataset must be subclassed.
		"""
		self.dataset = dataset
		for filt in self._filters:
			self.dataset = filt.process(self.dataset)
			logger.debug(f"Filter {filt} stored {self.dataset}.")
			if not self.dataset:
				logger.debug(f'Filter {filt} returned without result. Interrupting write process...')
				return # nothing to do anymore
		self._write_dataset()
		
		def _write_dataset(self):
			raise NotImplementedError(f'No write process defined for {self}!')

##############################################################################################
# H 5 W ri t e r 
class H5Writer(Writer):
 
	@staticmethod
	def __convert(data_dict):
		if not 'narray' in globals().keys():
			from numpy import array as narray
		"Take a json frame and convert to a numpy array"
		dtype = [(k,float) for k,v in data_dict.items()]
		vals = tuple([v for v in data_dict.values()])
		return narray([vals],dtype=dtype)
 
	def __init__(self,dataset_name,filename,filters=[]):
		super().__init__(filters = filters)
		logger.debug(f"Setting {dataset_name} and {filename}...")
		self.name = dataset_name
		self.basename = filename
		self.filename = '1_'+filename
		self.index = 1
 
	def _write_dataset(self):
		if not 'File' in globals().keys():
			from h5py import File
		"append one frame"
		if not path.exists(self.filename):
			with File(self.filename,'w') as f:
				logger.info(f"Create new file {self.filename}")
				f.create_dataset(self.name,data=self.__convert(self.dataset),maxshape=(None,),chunks=True)
		else:
			try:
				with File(self.filename,'a') as f:
					h5 = f.get(self.name,False)
					if not h5:
						f.create_dataset(self.name,data=self.__convert(self.dataset),maxshape=(None,),chunks=True)
					else:
						h5.resize(h5.size+1,axis=0)
						h5[-1] = self.__convert(self.dataset)
			except:
				self.index+=1
				logger.error(f'Problem accessing {self.filename}. Writing in new file {self.index}_{self.basename}.')
				self.filename = f'{self.index}_{self.basename}'
				self._write_dataset()


##############################################################################################
# M o n g o D B W r i t e r 
class MongoDBWriter(Writer):

	def __init__(self,database_url,data_cls,filters=[]):
		if not 'connect' in globals().keys():
			from mongoengine import connect
		super().__init__(filters = filters)
		logger.debug(self._filters)
		connect(host=database_url)
		self._table = data_cls

		logger.info(f"Initialized {self}")
	
	def _write_dataset(self):
		ds = self._table(**self.dataset)
		ds.save()
		logger.debug(f'Wrote to database: {self.dataset}')

##############################################################################################
# M q t t  W r i t e r 
class MqttWriter(Writer):	
	def __init__(self,broker_url,client_id,topic, username=None, password=None,filters=[]):
		super().__init__(filters = filters)
		if not 'Mqtt' in globals().keys():
			from mqtt import Mqtt
		self.topic = topic
		logger.info(f'Connecting to broker at {broker_url}')
		self.broker = Mqtt(broker_url,client_id, username=username, password=password)
		@self.broker.on_connect
		def on_connect(client, userdata, flags, rc):
			if rc == 0:
				logger.debug("Connected to MQTT Broker!")
			else:
				logger.error("Failed to connect, return code %d\n", rc)
		
	def _write_dataset(self):
		result = self.broker.publish(self.topic, json.dumps(self.dataset))
		status = result[0]
		if status == 0:
			logger.debug(self.dataset)
			logger.debug(f"Send message to topic {self.topic}")
		else:
			logger.error(f"Failed to send message to topic {self.topic}")
			logger.error(result)


