A Python script for reading out specific sensors via a serial port with configurable output to an mqtt queue, to h5 or csv files, and to a mongodb JSON database. Currently two Air Quality Datalogger are supported. If you want it to be easier, you better use nodered!

# Quick Start
The datalogger is invoked with
```
	python datalogger.py config.yaml
```	


# Short Description
The main script `datalogger.py` reads from the configuration file all the information needed to configure a reader or the writers and instantiates a reader and one or more writers. The reading loop is then started automatically. With each read event, the `write()` method is then called for each writer. The reader uses a parser to pass the read data to `reader.write()`. The writers in turn can call filters for intermediate processing of the data. Currently, there is a filter for calculating running averages or for accumulating several measured values, so that not every read data record must also be written to its sink. The filters are also configured for each writer in the *.yaml configuration file.

