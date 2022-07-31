A Python script for reading out specific sensors via a serial port with configurable output to an mqtt queue, to h5 or csv files, and to a mongodb JSON database. Currently two Air Quality Datalogger are supported. If you want it to be easier, you better use `nodered`!

# Quick Start
To set up the project locally download this rep and initialize the python project. You will need `python3.6+`. To initialize the datalogger
```
git clone https://github.com/phyzzxbrewery/datalogger.git
cd datalogger
virtualenv -p python3 .env
source .env/bin/activate
pip install -r requirements
```    
If you have plugged-in the sensors, their wrappers can than be started with

    python datalogger -o <config File>
    
For each sensor you need to start a datalogger. As identical sensors do not have any attributes to discern them (at least I couldn't find them), they would get identified by by their interface identifiers `ttyUSB0, ttyUSB1,...`. To automatically start the logging services you must integrate these commands into the `system.d` or `udev` mechanism appropriatly. Instructions you will find easily in the WWW as almost all code found here is a variation of code I scraped from web tutorials.

# Short Description
The main script `datalogger.py` reads from the configuration file all the information needed to configure a reader or the writers and instantiates a reader and one or more writers. The reading loop is then started automatically. With each read event, the `write()` method is then called for each writer. The reader uses a parser to pass the read data to `reader.write()`. The writers in turn can call filters for intermediate processing of the data. Currently, there is a filter for calculating running averages or for accumulating several measured values, so that not every read data record must also be written to its sink. The filters are also configured for each writer in the *.yaml configuration file.

# Supported Sensors
This project has been realized with a PCE AQD20 data logger and a cost efficient dust sensor build around a plantower pms5003 particle counter, found at [this shopping site](https://m.banggood.com/PM1_0-PM2_5-PM10-Detector-Module-Air-Quality-Dust-Sensor-Tester-Detector-Support-Export-Data-Monitoring-Home-Office-Car-Tools-p-1615550.html?akmClientCountry=DE&utm_design=18&utm_email=1602254740_2324&utm_source=emarsys&utm_medium=Shipoutinform190813&utm_campaign=trigger-logistics&utm_content=Gakki&sc_src=email_2671705&sc_eh=2523af32c8b7c74e1&sc_llid=24696974&sc_lid=104858042&sc_uid=ud9BBoFZXw&cur_warehouse=CZ). Unfortunately, this came without any documentation but the shopping site's product description includes a Q & A section, where some relevant hints can be found. The sensor itself is [well documented](https://www.aqmd.gov/docs/default-source/aq-spec/resources-page/plantower-pms5003-manual_v2-3.pdf).

# Configuration
The configuration is done with `.yaml`-files. Generally, there is a section for the reader and each writer and subsections therein for each filter. The section name the classes for the reader, writer, filter instances and include some configuration data.
## PCE AQD20 section
```
reader_cfg:
    reader_cls: !!python/name:readers.PCEAQD20
    # Number of lines forming one dataset
    no_lines: 5
```
## Plantower section
```
reader_cfg:
    reader_cls: !!python/name:readers.Plantower 
```
## CSV-Writer Section
```
csv_writer_cfg:
    writer_cls: !!python/name:writers.CSVWriter
    description: "Ein kleiner Testlauf!"
    basedir: "/path/to/data"
    filename: "filename.csv"
		#the separator default is ";"
    separator: "\t"
```

## mqtt section
```
mqtt_writer_cfg:
    writer_cls: !!python/name:writers.MqttWriter
    broker_url: 'broker.somwhere.io'
    client_id: 'CLIENTID'
    topic: "YOUR/TOPIC"
    username: "username"
    password: "clear text password (...)"
```
## H5 section
```
# The h5 writer is not up to date and not very stable
 h5_writer_cfg:
     writer_cls: !!python/name:writers.H5Writer
     dataset_name: "datalogger_Plantower"
		 basedir: "path/to/data"
     filename: "filename"
```
# mongodb section
```
json_db_writer:
    writer_cls: !!python/name:writers.MongoDBWriter
    data_cls: !!python/name:model.PlantowerData
    database_url: "mongodb.url"
```

Each Writer Section may include one or more filter subsections. Currently there is only an accumulator filter
# filter subsection
```
	filters:
		- 
			filter_cls: !!python/name:utils.Reducer
			# number of records to accumulate
			interval: 10 
```

## Disclaimer
This is by no means stable or clean code. This is just a hack to get the the remote data visualization of serially connected data loggers running. MQTT to send and receive data has proven to be reliable so far. The same holds for a python script to connect to the serial interface and write data on `mqtt` queues. Data storage on the other side surely needs some re-thinking which also holds true for the visualization techniques. Any data processing exceeding moving averages to smooth the highly volatile CO2/particle concentration curves has not been addressed at all. 
