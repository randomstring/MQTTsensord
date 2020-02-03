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

debug_p = True


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

    move_clock_hands(name, msg_data, userdata)


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
    logger = logging.getLogger('mqttserverd')
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
    interval = config_data['interval'] if 'interval' in config_data else 5

    logger.info("connecting to host " + host + ":" + str(port))

    if debug_p:
        print("connecting to host " + host + ":" + str(port))

    userdata = {
        'logger': logger,
        'host': host,
        'port': port,
        'config_data': config_data,
        }

    # how to mqtt in python see https://pypi.org/project/paho-mqtt/
    mqttc = mqtt.Client(client_id='mqttsensord',
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

    while True:
        for sensor in config_data['sensor_list']:
            read_sensor(sensor, user_data)
        time.sleep(interval)


#
# read_sensor()  read an individual sensor and send MQTT message
#
def read_sensor(sensor, user_data):
    pass


def start_daemon(pidf, logf, wdir, configf, nodaemon):
    global debug_p

    if nodaemon:
        # non-daemon mode, for debugging.
        print("Non-Daemon mode.")
        do_something(logf, configf)
    else:
        # daemon mode
        if debug_p:
            print("mqttserver: entered run()")
            print("mqttserver: pidf = {}    logf = {}".format(pidf, logf))
            print("mqttserver: about to start daemonization")

        with daemon.DaemonContext(working_directory=wdir, umask=0o002,
                                  pidfile=lockfile.FileLock(pidf),) as context:
            do_something(logf, configf)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MQTT Sensor Deamon")
    parser.add_argument('-p', '--pid-file', default='/home/pi/mqttsensord/mqttserver.pid')
    parser.add_argument('-l', '--log-file', default='/home/pi/mqttsensord/mqttserver.log')
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
