# MQTTsensord

Python daemon transmitting local sensor updates using MQTT.

## MQTT Sensor Daemon

This is working, but far from complete.

## Sensors

The plan is to make an extensible platform for adding new
sensors. Anything the raspberry pi can support. With a fallback
command line parsing option.

### Temperature dht22 and dht11

**Coming Soon**

### apcupsd

This sensor runs the ``apcaccess`` command to get the UPS status and
sends a JSON message via MQTT. This message includes the following fields:

``` json
{
 "TIMELEFT_MINUTES": "1440.0",
 "HOSTNAME": "pihost",
 "BCHARGE_PERCENT": "100.0",
 "STATUS": "ONLINE",
 "UPSNAME": "UPS3"
 }
```

Requires installation and configuration of apcupsd.

### Reed Switches

**Coming Soon**

## Controllable

### LED

### Motors and Servos

## Installation

The daemon is started on boot by systemd service.

```bash
pip3 install -r requirements.txt
mkdir /home/pi/mqttsensord/
cp mqttsensord.py mqttsensord.json /home/pi/mqttsensord/
sudo cp mqttsensord.service /lib/systemd/system/
sudo chmod 644 /lib/systemd/system/mqttsensord.service
sudo systemctl daemon-reload
sudo systemctl enable mqttsensord.service
sudo systemctl start mqttsensord.service
tail -f /home/pi/mqttsensord/mqttsensor.log
```

NOTE: You will need to edit ``/home/pi/mqttsensord/mqttsensord.json``
with your MQTT server credentials and configure your local sensors.


# Future Plans and Features

* More sophisticated scheduling. Allow sensors to be polled at different rates.
* Add MQTT LWT support
* MQTT subscribe to channels to publish to local services

# Troubleshooting

First, make sure you have the MQTT server, username, and password
correct in the ``mqttsensord.json`` config file. Second, make sure the
server you're talking to is listing on the correct port, 1883 by
default. If you're using port 4883, make sure SSL is configured
correctly on both ends. Third, make sure that the MQTT server you're
connecting to is recieving the messages. One possible problem is if
the reciever is not listening for the given topic. Adding the MQTT
wildcard ``#`` as a listening topic is one way to get around
this. Test connectivity with the mqtt command line tools to send a few
test messages.
