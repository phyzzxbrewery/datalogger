import queue, logging, os, subprocess
logger = logging.getLogger(__name__)

class Event:
	pass
	
class Observer:

	def __init__(self, name ):
		self.name = name
		self.callbacks = []
		
	def register(self, callback ):
		"Use it as a decorator!"
		self.callbacks.append( callback )
		logger.debug('Appended a callback')
		return callback
		
	def notify(self,**kwargs):
		e = Event()
		e.source = self.name
		for k,v in kwargs.items():
			setattr(e,k,v)
		for callback in self.callbacks:
			logger.debug('Executing callback')
			callback(e)
			
observers = {}

def getObserver(name):
	if not observers.get(name,False):
		observers[name] = Observer(name)
	return observers.get(name)

class NoSerialInterfaceFoundError(Exception):
	pass

def get_serial_if_fname(pat):
	"Search for busy interfaces with lsof"
	lines = subprocess.run(['lsof','+d','/dev'], stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')
	busy_ifs = [line.split()[-1] for line in lines if line.find('ttyUSB')>0]
	"Search for serial interface with pattern pat.pattern"
	lines = subprocess.run(['dmesg'], stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')
	serial_ifs = ['/dev/' + pat.search(line).group(1) for line in lines if pat.search(line)]
	""
	for sif in serial_ifs:
		if not sif in busy_ifs and os.path.exists(sif):
			logger.info(f'Found serial interface {sif}')
			return sif
		else:
			logger.info(f'Serial interface {sif} is busy.')
	raise NoSerialInterfaceFoundError(f'Could not find a serial interface for the given pattern {pat}!\nIs the interface blocked?')

class MovingAverage:
	s = 0
	
	def __init__(self,n=30):
		self.q = queue.Queue()
		self.q.maxsize = n

	def next(self,val):
		"""
		processes the next value and returns the average value.
		If the Queue is full, subtract the first value to have a 
		moving average on maxsize values.
		"""
		if self.q.full():
			self.s -= self.q.get()
		if val and isinstance(val,(int,float)):
			self.q.put(val)	
			self.s += val
			return round(self.s/self.q.qsize())
		return None
		
	def is_full(self):
		return self.q.full()
		
class H5Writer:
	"Lazily initialize a H5Writer"
	H5FNAME = os.environ.get('H5FILE_PATH','default.h5')
	__writers = {}
 
	@classmethod
	def get_Writer(cls, name,data_dict):
		if not cls.__writers.get(name,False):
			cls.__writers[name] = cls(name,data_dict)
		return cls.__writers[name]
 
	@staticmethod
	def __convert(data_dict):
		"Take a json frame and convert to a numpy array"
		dtype = [(k,float) for k,v in data_dict.items()]
		vals = tuple([v for v in data_dict.values()])
		return narray([vals],dtype=dtype)
 
	def __init__(self,name,data_dict):
		from h5py import File
		from numpy import array as narray
		self.name = name
		if not os.path.exists(self.H5FNAME):
			with File(self.H5FNAME,'w') as f:
				logger.info(f"Create new file {name}")
				f.create_dataset(name,data=self.__convert(data_dict),maxshape=(None,),chunks=True)
		else:
			with File(self.H5FNAME,'a') as f:
				try:
					f.create_dataset(name,data=self.__convert(data_dict),maxshape=(None,),chunks=True)
				except Exception as e:
					logger.warning(e)
 
	def append(self,data_dict):
		"append one frame"
		with File(self.H5FNAME,'a') as f:
			h5 = f[self.name]
			h5.resize(h5.size+1,axis=0)
			h5[-1] = self.__convert(data_dict)
 
class Reducer:
	dataset = {}
	interval = 30
	_reducers = {}
	
	@classmethod
	def get_reducer(cls, type):
		"Lazily initialize a Reducer"
		if not cls._reducers.get(type):
			cls._reducers[type] = cls(type)
		return cls._reducers[type]
		
	def __init__(self,name=None,interval=30):
		self.name = name
		self.interval = interval
		self.averagers = {}
		logger.debug(f"Initialized reducer for topic {self.name}")
		
	def put(self,obj):
		"""
		Lazily initialize an Averager for each measurement in obj 
		and process each value, i.e. feed them to the
		avergers and update the averages container with the current avarage values
		"""
		logger.debug(f"Going to process {obj}")
		if not self.averagers:
			for key in obj.keys():
				logger.debug(f"Initializing averager for key {key}")
				self.averagers.update({ key:MovingAverage( self.interval ) })
		for key in obj.keys():
			if isinstance(obj.get(key,0),(int,float)):
				val = self.averagers[key].next(obj.get(key,0))
				self.dataset.update({key:val})
			else:
				val = self.averagers[key].next(obj.get(key).get('value',0))
				obj[key].update(value=val)
				self.dataset.update({key:obj[key]})
	
	def get_data(self):
		"Returns the averaged data obj"
		return self.dataset
	
	def is_full(self):
		return self.averagers.get('timestamp').is_full()
	
	def process(self, dataset):
		self.put(dataset)
		logger.debug(f'put {dataset}')
		if not self.is_full():
			return
		else:
			rval = dict( self.get_data() ) # Clone return value to not delete it in the next step
			self.reset()
			return rval
		
	def reset(self):
		self.dataset = {}
		self.averagers = {}
	
class PlausiChecker:
	def process(self,dataset):
		logger.debug(f'Going to check {dataset} for plausibility...')
		for k,v in dataset.items():
			"Discard dataset if one value is not in an allowed range"
			logger.debug(f"Checking {k}...")
			if k == 'temperature':
				if (not v['value'] and v['value'] != 0) or v['value'] < -30 or v['value'] > 80:
					logger.warning(f'Discarded dataset {dataset} due to invalid value for {k}')
					return
			elif k == 'pressure':
				if (not v['value'] and v['value'] != 0)  or v['value'] < 800 or v['value'] > 1200:
					logger.warning(f'Discarded dataset {dataset} due to invalid value for {k}')
					return
			elif k == 'humidity':
				if (not v['value'] and v['value'] != 0)  or v['value'] > 100 or v['value'] <  0:
					logger.warning(f'Discarded dataset {dataset} due to invalid value for {k}')
					return
			else:
				if v['value'] < 0 or (not v['value'] and v['value'] != 0):
					logger.warning(f'Discarded dataset {dataset} due to invalid value {v} for {k}')
					return
			logger.debug(f"{k} passed check.")
		return dataset
				

