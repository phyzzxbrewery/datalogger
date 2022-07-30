import os
import mongoengine as db
import logging
logger = logging.getLogger('__name__')

class AQData(db.Document):
	timestamp = db.IntField()
	pm25 = db.FloatField()
	humidity = db.FloatField()
	temperature = db.FloatField()
	co2 = db.FloatField()
	pressure = db.FloatField()
	
class PlantowerData(db.Document):
	timestamp = db.IntField()
	aqi = db.IntField()
	humidity = db.FloatField()
	temperature = db.FloatField()
	cpm25 = db.FloatField()
	cpm10 = db.FloatField()
	cpm100 = db.FloatField()
	apm25 = db.FloatField()
	apm10 = db.FloatField()
	apm100 = db.FloatField()

class XiaomiMiData(db.Document):
	timestamp = db.IntField()
	temperature = db.FloatField()
	humidity = db.FloatField()

