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


## Future Plans and Features

* More sophisticated scheduling. Allow sensors to be polled at different rates.
* Add MQTT LWT support
* MQTT subscribe to channels to publish to local services
