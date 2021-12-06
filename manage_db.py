#!/usr/bin/python3

import sqlite3
import json
import os
import signal
import time
import dateutil.parser

def load_cfg():
    with open('configuration.json', 'r') as fp:
        cfg = json.load(fp)
    return cfg

def create_tables_if_necessary(db):
    cur = db.cursor()
    # vdd is battery level remaining
    db.execute('create table if not exists readings (timestamp timestamp, device_id string, temperature float, humidity int, light int, motion int, co2 int, vdd int)')
    db.execute('create table if not exists device_location (start timestamp default current_timestamp, finish timestamp, device_id string unique, room string, detailed_location string, private bool)')

def main(cfg):
    db = sqlite3.connect(cfg['sqlite3_db_filename'])
    create_tables_if_necessary(db)

if __name__ == "__main__":
    cfg = load_cfg()
    main(cfg)

