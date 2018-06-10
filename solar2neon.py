import serial
import requests
import jsonpickle
import datetime
import os
import time
from time import sleep
import json

with open('config.json') as json_file:
    settings = json.load(json_file)

# =====================================================
# Class definitions for data to import to Neon
# =====================================================


class DataItem:
    def __init__(self, time_stamp, value):
        self.Time = time_stamp
        self.Value = value


class Sensor:
    def __init__(self, sensor_number, import_type):
        self.SensorNumber = sensor_number
        self.ImportType = import_type
        self.Samples = []


class ImportData:
    def __init__(self):
        self.Data = []


def get_solar_status(port, baud):
    response = ''

    try:

        ser = serial.Serial(
            port=port,
            baudrate=baud,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=30
        )
        retries = 3
        if not ser.is_open:
            ser.open()
        sleep(1)
        read('$$$', 'CMD', 2, retries, ser)
        sleep(1)
        # read('I\r','Done',20,ser)
        # sleep(1)
        read('C,201512083167\r', 'CONNECT', 20, retries, ser)
        sleep(2)
        response = read('R', '\n', 5, retries, ser)
        sleep(1)
        read('$$$', '', 2, retries, ser)
        sleep(1)
        read('K,1\r', '', 2, retries, ser)
        sleep(1)
        ser.close()
        return response

    except Exception as inst:
        print(inst)
        return response


def read(cmd, term, timeout, retries, ser):
    buff = ''
    for x in range(0, retries):
        print('S:' + cmd)
        ser.reset_input_buffer()
        ser.write(cmd)
        ser.flush()
        buff = ''
        end_time = time.time() + timeout
        while True:
            if ser.inWaiting() > 0:
                d = ser.read(ser.inWaiting()).decode('ascii')
                print(d),
                buff = buff + d
                if term != '':
                    if buff.find(term) >= 0:
                        return buff
            elif time.time() > end_time:
                break
    return buff


# =====================================================
# Send the ImportData class to the Neon REST service
# =====================================================


def send_to_neon(url, user, pw, nrt_id, neon_data):
    session_url = url + '/PostSession'

    cred = {'Username': user, 'Password': pw}
    r = requests.post(url=session_url, json=cred)

    # extract session token in json format
    session = r.json()
    hdr = {'X-Authentication-Token': session['Token'], 'Content-Type': 'application/json'}

    payload = jsonpickle.pickler.encode(neon_data)
    data_url = url + '/ImportData/' + nrt_id + '?LoggerType=1'

    requests.post(data_url, data=payload, headers=hdr)


# =====================================================
# Convert the raw message from the Arduino to
# an ImportData class
# =====================================================


def convert_solar_data(raw_data, time_stamp):
    d = {}
    items = raw_data.split(',')
    for item in items:
        print('New value = ' + item)
        if item.find('=') >= 0:
            val = item.split('=')
            d[val[0]] = val[1]

    neon_data = ImportData()

    s = Sensor("0", "0")
    s.Samples.append(DataItem(time_stamp, d["PA"]))
    neon_data.Data.append(s)

    s = Sensor("1", "0")
    s.Samples.append(DataItem(time_stamp, d["HI"]))
    neon_data.Data.append(s)

    s = Sensor("2", "0")
    s.Samples.append(DataItem(time_stamp, d["CO"]))
    neon_data.Data.append(s)

    s = Sensor("3", "0")
    s.Samples.append(DataItem(time_stamp, d["WB"]))
    neon_data.Data.append(s)

    s = Sensor("4", "0")
    s.Samples.append(DataItem(time_stamp, d["MC"]))
    neon_data.Data.append(s)

    s = Sensor("5", "0")
    s.Samples.append(DataItem(time_stamp, d["SC"]))
    neon_data.Data.append(s)

    s = Sensor("6", "0")
    # Scale to KWh. First guess
    heat = float(d["HA"]) * 0.000177
    s.Samples.append(DataItem(time_stamp, str(heat)))
    neon_data.Data.append(s)

    s = Sensor("7", "0")
    s.Samples.append(DataItem(time_stamp, d["RL"]))
    neon_data.Data.append(s)

    return neon_data


def get_node_list(url, user, pw):
    session_url = url + '/PostSession'
    cred = {'Username': user, 'Password': pw}
    r = requests.post(url=session_url, json=cred)

    # extract session token in json format
    session = r.json()
    hdr = {'X-Authentication-Token': session['Token'], 'Content-Type': 'application/json'}

    data_url = url + '/GetNodeList'

    r = requests.get(data_url, headers=hdr)

    if os.path.isfile('nodes.json'):
        os.remove('nodes.json')

    with open('nodes.json', 'w', encoding="utf-8") as file:
        file.write(r.text)


solar_data = get_solar_status(settings['serial_port'], settings['serial_baud'])
if solar_data != '':
    date_time = datetime.datetime.utcnow().replace(second=0).replace(microsecond=0).isoformat()
    data = convert_solar_data(solar_data, date_time)
    send_to_neon(settings['url'], settings['user'], settings['password'], settings['nrt_id'], data)
else:
    print('NO SOLAR DATA!')
