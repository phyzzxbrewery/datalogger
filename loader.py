import yaml, json
from os.path import splitext 
from importlib import import_module

def getConfigLoader(ext):
	if ext == '.yaml' or ext == '.yml':
		return yaml
	elif ext == '.json':
		return JSONLoader
	else:
		raise NotImplementedError(f'There is no Loader implemented for extension "{ext}"')

def as_class(dct):
	"Any key ending with _cls is supposed to have a value of the form module__name__.class__name__"
	for k in dct:
		if k.endswith('_cls'):
			mname, cname = splitext(dct[k])
			mdl = import_module(mname)
			cls = getattr(mdl,cname[1:])
			dct.update({k:cls})
	return dct

class JSONLoader():
	@staticmethod
	def load( fobj ):
		return json.load(fobj, object_hook = as_class)	
	def loads( s ):
		return json.loads(s, object_hook = as_class)	

