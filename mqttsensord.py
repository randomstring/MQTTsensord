#!/usr/bin/env python3
import sys
import os
import time
import argparse
import logging
import daemon
import json
import paho.mqtt.client as mqtt
import lockfile
import re
import subprocess
import Adafruit_DHT as dht

debug_p = True


#
# wrapper for MQTT JSON generation
#
def json_response(data):
    return json.dumps(data, sort_keys=true)


#
# apcaccess_host() get APC UPS info for given host and port
#
def apcaccess_json(host='localhost', port='3551'):

    apcaccess_cmd = '/sbin/apcaccess'
    apcaccess_host = str(host) + ":" + str(port)
    apcaccess_args = [apcaccess_cmd, '-h', apcaccess_host]
    wanted_keys = ('UPSNAME', 'HOSTNAME', 'STATUS', 'BCHARGE',
                   'TIMELEFT', 'LINEV')
    units_re = re.compile(' (Percent|Volts|Minutes|Seconds)$', re.IGNORECASE)
    errors = 0
    ups_data = {}

    # run apcaccess process to get UPS state
    try:
        apcaccess_subprocess = subprocess.Popen(apcaccess_args,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT)
        stdout, stderr = apcaccess_subprocess.communicate()
    except Exception as e:
        ups_data['error_msg'] = "Error parsing apcupsd line: {}".format(e)
        return json_response(ups_data)

    # check the return code
    if (stderr or apcaccess_subprocess.returncode):
        ups_data['errors'] = 1
        ups_data['returncode'] = apcaccess_subprocess.returncode
        if stderr:
            ups_data['error_msg'] = stderr.decode('utf-8')
        elif stdout:
            ups_data['error_msg'] = stdout.decode('utf-8')
        else:
            ups_data['error_msg'] = "Command exited with non-zero return code"
        return json_response(ups_data)

    # parse the response
    for rawline in stdout.decode('utf-8').splitlines():
        line = rawline.rstrip()
        try:
            (k, v) = [s.rstrip() for s in line.split(': ', 1)]
            if k in wanted_keys:
                units_match = re.search(units_re, v)
                units = ''
                if units_match:
                    units = re.sub(' ', '_', units_match.group(0))
                if units != '':
                    v = re.sub(units_re, '', v)
                    k = k + units.upper()
                ups_data[k] = v
                # print("[" + k + "] -> [" + v + "]")
        except Exception as e:
            # print errors to stderr
            print("Error parsing apcupsd line: {}".format(e), file=sys.stderr)
            print(line, file=sys.stderr)
            errors = errors + 1

    if errors > 0:
        ups_data["errors"] = errors

    return json_response(ups_data)


def read_dht(client, sensor, userdata, dht_type=dht.DHT22):
    sensor_data = {}
    # TODO: error checking on GPIO
    humidity, temperature = dht.read_retry(dht_type, sensor['GPIO'])
    humidity = round(humidity, 2)
    temperature = round(temperature, 2)
    sensor_data['temperature'] = temperature
    sensor_data['humidity'] = humidity
    return(json_response(sensor_data))


#
# read_sensor()  read an individual sensor and send MQTT message
#
def read_sensor(client, sensor, userdata):

    sensor_type = sensor['type']
    if sensor_type == 'apcups':
        sensor_data = apcaccess_json(sensor['host'],
                                     sensor['port'])
    elif sensor_type == 'dht22':
        sensor_data = read_dht(client, sensor, userdata, dht.DHT22)
    elif sensor_type == 'dht11':
        sensor_data = read_dht(client, sensor, userdata, dht.DHT11)
    else:
        sensor_data = json_response({'error':
                                     'bad sensor type: ' + sensor_type})

    userdata['logger'].debug("update sensor data: " + sensor['topic'])

    now = time.time()
    sensor['last_updated'] = now

    if debug_p:
        print('sensor data:')
        print(sensor_data)

    # Only send update if the results are different or we're past the
    # minimum update period
    if ((sensor_data != sensor['last_sent_data']) or
        (sensor['last_sent_time'] + sensor['update_interval'] > now)):

        if debug_p:
            if (sensor['last_sent_time'] + sensor['update_interval'] > now):
                print('update_interval exceeded')
            print('PUBLISHING SENSOR DATA to MQTT')

        client.publish(sensor['topic'], payload=sensor_data, qos=0,
                       retain=False)
        
        userdata['logger'].debug("publish sensor data: " +
                                 sensor['topic'])
        
        sensor['last_sent_data'] = sensor_data
        sensor['last_sent_time'] = now
    else:
        if debug_p:
            print('NO CHANGE in DATA')

#
# Callback for when the client receives a CONNACK response from the server.
#
def on_connect(client, userdata, flags, rc):
    if 'subscribe' in userdata:
        for subscribe_topic in userdata['subscribe']:
            client.subscribe(subscribe_topic)
            # log result codes
            if rc != 0:
                userdata['logger'].warning("subscibing to topic [" +
                                           subscribe_topic +
                                           "] result code " + str(rc))
            else:
                userdata['logger'].debug("subscibing to topic [" +
                                         subscribe_topic +
                                         "] result code " + str(rc))
    # Send notify messages if needed
    if 'notify' in userdata:
        for notify_topic in userdata['notify']:
            client.publish(notify_topic, payload='{"notify":"true"}',
                           qos=0, retain=False)


#
# Try/except wrapper for MQTT Messages
#
def on_message(client, userdata, message):
    # wrap the on_message() processing in a try:
    try:
        _on_message(client, userdata, message)
    except Exception as e:
        userdata['logger'].error("on_message() failed: {}".format(e))


#
# Callback for MQTT Messages
#
def _on_message(client, userdata, message):
    topic = message.topic

    (prefix, name) = topic.split('/', 1)

    if name == "UPDATE":
        # this is an update request, ignore
        return

    m_decode = str(message.payload.decode("utf-8", "ignore"))
    if debug_p:
        print("Received message '" + m_decode +
              "' on topic '" + topic +
              "' with QoS " + str(message.qos))

    log_snippet = (m_decode[:15] + '..') if len(m_decode) > 17 else m_decode
    log_snippet = log_snippet.replace('\n', ' ')

    userdata['logger'].debug("Received message '" +
                             log_snippet +
                             "' on topic '" + topic +
                             "' with QoS " + str(message.qos))

    try:
        msg_data = json.loads(m_decode)
    except json.JSONDecodeError as parse_error:
        if debug_p:
            print("JSON decode failed. [" + parse_error.msg + "]")
            print("error at pos: " + parse_error.pos +
                  " line: " + parse_error.lineno)
        userdata['logger'].error("JSON decode failed.")

    # python <=3.4.* use ValueError
    # except ValueError as parse_error:
    #    if debug_p:
    #        print("JSON decode failed: " + str(parse_error))

    # TODO: process incoming msg_data
    # handle_message(topic, msg_data, userdata)



def move_servo(name, message, userdata):
    #
    # move a sevro
    #
    # config_data = userdata['config_data']
    pass


def do_something(logf, configf):

    #
    # setup logging
    #
    logger = logging.getLogger('mqttsensord')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(logf)
    fh.setLevel(logging.INFO)
    formatstr = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(formatstr)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # read config file
    with open(configf) as json_data_file:
        try:
            config_data = json.load(json_data_file)
        except json.JSONDecodeError as parse_error:
            print("JSON decode failed. [" + parse_error.msg + "]")
            print("error at pos: ", parse_error.pos,
                  " line: ",  parse_error.lineno)
            sys.exit(1)

    # connect to MQTT server
    host = config_data['mqtt_host']
    port = config_data['mqtt_port'] if 'mqtt_port' in config_data else 4884
    default_interval = config_data['default_interval'] if 'default_interval' in config_data else 5

    logger.info("connecting to host " + host + ":" + str(port))

    if debug_p:
        logger.setLevel(logging.DEBUG)
        print("connecting to host " + host + ":" + str(port))

    userdata = {
        'logger': logger,
        'host': host,
        'port': port,
        'config_data': config_data,
        }

    client_id = config_data['client_id'] if 'client_id' in config_data else 'mqttsensord'

    # how to mqtt in python see https://pypi.org/project/paho-mqtt/
    mqttc = mqtt.Client(client_id=client_id,
                        clean_session=True,
                        userdata=userdata)

    mqttc.username_pw_set(config_data['mqtt_user'],
                          config_data['mqtt_password'])

    # create callbacks
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message

    if port == 4883 or port == 4884:
        mqttc.tls_set('/etc/ssl/certs/ca-certificates.crt')

    mqttc.connect(host, port, 60)
    mqttc.loop_start()

    for sensor in config_data['sensors']:
        # set defaults
        poll_interval = sensor['poll_interval'] if 'poll_interval' in sensor else default_interval
        update_interval = sensor['update_interval'] if 'update_interval' in sensor else 0
        sensor['last_sent_data'] = None
        sensor['last_sent_time'] = 0
        sensor['last_updated'] = 0
        sensor['update_interval'] = update_interval
        sensor['poll_interval'] = interval
    
    for sensor in config_data['sensors']:
        # first time for each sensor
        read_sensor(mqttc, sensor, userdata)

    while True:
        time.sleep(1)
        now = time.time()
        for sensor in config_data['sensors']:
            if sensor['last_updated'] + sensor['poll_interval'] > now:
                if debug_p:
                    print("read_sensor:", sensor)
                try:
                    read_sensor(mqttc, sensor, userdata)
                except Exception as e:
                    userdata['logger'].error("read_sensor failed: {}".format(e))
                    userdata['logger'].error("read_sensor failed: {}".format(sensor))
                if debug_p:
                    print(sensor)
                    print('---------------------')


    mqttc.disconnect()
    mqttc.loop_stop()


def start_daemon(pidf, logf, wdir, configf, nodaemon):
    global debug_p

    if nodaemon:
        # non-daemon mode, for debugging.
        print("Non-Daemon mode.")
        do_something(logf, configf)
    else:
        # daemon mode
        if debug_p:
            print("mqttsensor: entered run()")
            print("mqttsensor: pidf = {}    logf = {}".format(pidf, logf))
            print("mqttsensor: about to start daemonization")

        with daemon.DaemonContext(working_directory=wdir, umask=0o002,
                                  pidfile=lockfile.FileLock(pidf),) as context:
            do_something(logf, configf)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MQTT Sensor Deamon")
    parser.add_argument('-p', '--pid-file', default='/home/pi/mqttsensord/mqttsensor.pid')
    parser.add_argument('-l', '--log-file', default='/home/pi/mqttsensord/mqttsensor.log')
    parser.add_argument('-d', '--working-dir', default='/home/pi/mqttsensord')
    parser.add_argument('-c', '--config-file', default='/home/pi/mqttsensord/mqttsensord.json')
    parser.add_argument('-n', '--no-daemon', action="store_true")
    parser.add_argument('-v', '--verbose', action="store_true")

    args = parser.parse_args()

    if args.verbose:
        debug_p = True

    start_daemon(pidf=args.pid_file,
                 logf=args.log_file,
                 wdir=args.working_dir,
                 configf=args.config_file,
                 nodaemon=args.no_daemon)
