#!/usr/bin/python3

import sqlite3
import paho.mqtt.client as mqtt
import base64
import json
import os
import signal
import time
import dateutil.parser
from elsys_decoder import decoder
from manage_db import load_cfg

def on_message(client, userdata, msg):
    db=userdata['db']
    print(msg.topic+" " +str(msg.payload))
    p = json.loads(msg.payload)
    data = None
    if 'end_device_ids' in p:
        dev_id = p['end_device_ids']['device_id']
        if 'received_at' in p:
            ts = p['received_at']
            t = dateutil.parser.isoparse(ts)
            if 'uplink_message' in p:
                enc = p['uplink_message']['frm_payload']
                data = base64.b64decode(enc)

    if data is not None:
        print(dev_id)
        print(t)
        print(data.hex())
        print(decoder(data))
        d = decoder(data)
        if 'temperature' in d and 'humidity' in d and 'light' in d and 'motion' in d and 'co2' in d and 'vdd' in d:
            with db:
                db.execute('insert into readings (timestamp, device_id, temperature, humidity, light, motion, co2, vdd) values (?, ?, ?, ?, ?, ?, ?, ?)',
                           [t, dev_id,
                            d['temperature'], d['humidity'],
                            d['light'], d['motion'],
                            d['co2'], d['vdd']])

def on_connect(client, userdata, flags, rc):
    print('Connected')
    client.subscribe('#')

def on_disconnect(client, userdata, rc):
    print('Disconnected')
    if rc != 0:
        print('Unexpected disconnection rc={}'.format(rc))

def on_subscribe(client, mid, qos, properties):
    print('SUBSCRIBED')

def main(cfg):
    db = sqlite3.connect(cfg['sqlite3_db_filename'])
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.username_pw_set(cfg['mqtt_username'],cfg['mqtt_password'])
    client.user_data_set({'db': db, 'cfg': cfg})
    client.connect(cfg['mqtt_hostname'],cfg['mqtt_port'],60)

    client.loop_forever()

if __name__ == "__main__":
    cfg = load_cfg()
    print(cfg)
    main(cfg)

