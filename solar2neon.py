import serial
import requests
import jsonpickle
import datetime
import os
import time
from time import sleep

base_url = 'http://restservice-neon.niwa.co.nz/NeonRESTService.svc'
nrt_id = '4063'
user_name = 'xxxxxx'
password = 'xxxxxxx'
debug_file = 'nodes.json'
serial_port = "/dev/ttyAMA0"
baud_rate = '115200'
serial_timeout = 30
retries = 3

# =====================================================
# Class definitions for data to import to Neon
# =====================================================


class DataItem:
    def __init__(self, date_time, value):
        self.Time = date_time
        self.Value = value


class Sensor:
    def __init__(self, sensor_number, import_type):
        self.SensorNumber = sensor_number
        self.ImportType = import_type
        self.Samples = []


class ImportData:
    def __init__(self):
        self.Data = []


def get_solar_status():
    response = ''
    try:
        ser = serial.Serial(
            port=serial_port,
            baudrate=baud_rate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=serial_timeout
            )

        if not ser.is_open:
            ser.open()
        sleep(1)
        read('$$$','CMD',2,ser)
        sleep(1)
        # read('I\r','Done',20,ser)
        # sleep(1)
        read('C,201512083167\r','CONNECT',20,ser)
        sleep(2)
        response = read('R','\n',5,ser)
        sleep(1)
        read('$$$','',2,ser)
        sleep(1)
        read('K,1\r','',2,ser)
        sleep(1)
        ser.close()
        return response

    except Exception as inst:
        print(inst)
        return response


def read(cmd,term,timeout,ser):
    for x in range(0,retries):
        print('S:' + cmd)
        ser.reset_input_buffer()
        ser.write(cmd)
        ser.flush()
        buff = ''
        end_time=time.time()+timeout
        while(True):
            if ser.inWaiting()>0:
                data = ser.read(ser.inWaiting()).decode('ascii')
                print(data),
                buff=buff+data
                if term != '':
                    if buff.find(term)>=0:
                        return buff
            elif time.time()>end_time:
                break
    return buff

# =====================================================
# Send the ImportData class to the Neon REST service
# =====================================================


def send_to_neon(data):
    session_url = base_url + '/PostSession'

    cred = {'Username': user_name, 'Password': password}
    r = requests.post(url=session_url, json=cred)

    # extract session token in json format
    session = r.json()
    hdr = {'X-Authentication-Token': session['Token'], 'Content-Type': 'application/json'}

    payload = jsonpickle.pickler.encode(data)
    data_url =  base_url + '/ImportData/' + nrt_id + '?LoggerType=1'

    r = requests.post(data_url, data=payload, headers=hdr)

# =====================================================
# Convert the raw message from the Arduino to
# an ImportData class
# =====================================================


def convert_solar_data(data, date_time):
    d = {}
    items = data.split(',')
    for item in items:
        print('New value = ' + item)
        if item.find('=')>=0:
            val = item.split('=')
            d[val[0]] = val[1]

    neon_data = ImportData()

    s = Sensor("0", "0")
    s.Samples.append(DataItem(date_time, d["PA"]))
    neon_data.Data.append(s)

    s = Sensor("1", "0")
    s.Samples.append(DataItem(date_time, d["HI"]))
    neon_data.Data.append(s)

    s = Sensor("2", "0")
    s.Samples.append(DataItem(date_time, d["CO"]))
    neon_data.Data.append(s)

    s = Sensor("3", "0")
    s.Samples.append(DataItem(date_time, d["WB"]))
    neon_data.Data.append(s)

    s = Sensor("4", "0")
    s.Samples.append(DataItem(date_time, d["MC"]))
    neon_data.Data.append(s)

    s = Sensor("5", "0")
    s.Samples.append(DataItem(date_time, d["SC"]))
    neon_data.Data.append(s)

    s = Sensor("6", "0")
    s.Samples.append(DataItem(date_time, d["HA"]))
    neon_data.Data.append(s)

    return neon_data


def get_node_list():
    session_url = base_url + '/PostSession'
    cred = {'Username': user_name, 'Password': password}
    r = requests.post(url=session_url, json=cred)

    # extract session token in json format
    session = r.json()
    hdr = {'X-Authentication-Token': session['Token'], 'Content-Type': 'application/json'}

    data_url = base_url + '/GetNodeList'

    r = requests.get(data_url, headers=hdr)

    if os.path.isfile(debug_file):
        os.remove(debug_file)

    with open(debug_file, 'w', encoding="utf-8") as file:
        file.write(r.text)


solarData = get_solar_status()
if solarData != '':
    dateTime = datetime.datetime.utcnow().replace(second=0).replace(microsecond=0).isoformat()
    neonData = convert_solar_data(solarData, dateTime)
    send_to_neon(neonData)
else:
    print('NO SOLAR DATA!')
