# MQTTserver

Python daemon transmitting local sensor updates using MQTT.

## MQTT Server Daemon

* WORK IN PROGRESS *

## Sensors

The plan is to make an extensible platform for adding new
sensors. Anything the raspberry pi can support. With a fallback
command line parsing option.

### Temperature dht22 and dht11

### apcupsd

### Reed Switches

## Controllable

### LEDs

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


