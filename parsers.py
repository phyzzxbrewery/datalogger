import io, json, logging, sys, re
from datetime import datetime
from parsers import *

logger = logging.getLogger(__name__)

class Parser(object):
	
	def __init__(self):
		self.STOP = ''

	def _check_validity(self, word ):
		"Should be subclassed"
		if not word:
			logger.debug('Did not receive any data. Does the data logger send data?')
		if not self.has_start_byte(word):
			logger.debug('Has no start Byte. Truncated dataset?')
		return True
	
	def matches_init_condition(self, word):
		"""
		To catch the first line of a dataset.
		Should be subclassed if required.
		"""
		return self.has_start_byte(word)

	def parse_word(self, word ):
		"Must be subclassed if required"
		return word

	def has_start_byte(self,word):
		return word[0]==self.START
		

##############################################################################################
# P C E A Q D 2 0 
pat_PCEAQD20 = re.compile('FTDI USB Serial Device converter now attached to (ttyUSB\d)')

class PCEAQD20Parser(Parser):
	UNITS = ['H0','04','02','78','19','80','01','91','G4']
	MEASURING_TYPES = ['pm25','humidity','temperature','co2','pressure']
	START = '\x02'
	STOP = b'\r'
	INIT = '1'

	def _check_validity(self, word):
		super()._check_validity(word)
		if not len(word)==16:
			logger.error(f"Not enough bytes to unpack. Expected 16 but got {len(word)}")
		if not word[1]=='4' or not int(word[2]) in range(1,6) or not word[3:5] in self.UNITS:
			raise ValueError(f'Data string {word} contains invalid characters!')
		return True

	def matches_init_condition(self,word):
		return super().matches_init_condition(word) and word[2] == self.INIT
		
	def parse_word(self, w): 
		self._check_validity(w)
		t = w[2] 
		t = self.MEASURING_TYPES[int(t)-1] 
		u = w[3:5] 
		if u=='H0': 
			unit = 'µg/m³' 
		elif u=='04': 
			unit = '%' 
		elif u == '01': 
			unit = '°C' 
		elif u == 'G4': 
			unit = 'ppm' 
		elif u ==  '91': 
			unit = 'hPa' 
		else: 
			unit = u 
		s = w[5] 
		sign = 1 if s == '0' else -1 
		d = w[6] 
		div = sign*10**int(d) 
		val = int(w[7:15])/div 
		return {t:dict(value=val, unit=unit)} 

##############################################################################################
# P l a n t o w e r 
class PlantowerParser(Parser):
	START = '{'
	STOP = b'}'
	INIT = START
	
	def _check_validity(self, j):
		try:
			super()._check_validity(j)
		except ValueError:
			raise ValueError('Not a json string')
		return True
	
	def parse_word(self,j):
		self._check_validity(j)
		pat = re.compile('\{.*?\}')
		r = pat.match(j)

		while r:
			if len(r.group().split(',')) == 16:
				break
			start, end = r.span()
			j = j[end:]
			r = pat.match(j)

		d = json.loads(j)
		
		res = dict(
			cpm25 = getDim(float(d['cpm2.5']),'µg/m³'),
			cpm10 = getDim(float(d['cpm1.0']),'µg/m³'),
			cpm100 = getDim(float(d['cpm10']),'µg/m³'),
			apm25 = getDim(float(d['apm2.5']),'µg/m³'),
			apm10 = getDim(float(d['apm1.0']),'µg/m³'),
			apm100 = getDim(float(d['apm10']),'µg/m³'),
			# aqi = int(d['aqi']),
			temperature = getDim(float(d.pop('t')),'°C'),
			humidity = getDim(float(d.pop('r')),'%')
		)
		return res

def getDim(val,unit):
	return dict(value=val,unit=unit)		

##############################################################################################
# X i a o m i M i T e m p e r a t u r e L o g g e r
class XiaomiMiTemperatureLoggerParser(Parser):

	def parse(self,data):
		msg = dict(timestamp=round(datetime.now().timestamp()*1000))
		sign = int(data[1]) & 1<<7
		val = (int(data[1])&0x7f)<<8|int(data[0])
		if sign:
			val -= 32767
		msg.update(
			temperature = val/100,
			humidity = int(data[2])
		)
		return msg
		


