#!/usr/bin/python3

import sqlite3
import json
import os
import signal
import time
import argparse
import dateutil.parser

argparser = argparse.ArgumentParser()
argparser.add_argument('-d', '--device-id', metavar='DEV_ID', type=str,
                       help='Search by given Device ID')
argparser.add_argument('-r', '--room', metavar='ROOM', type=str,
                       help='Search by room identifier')
args = argparser.parse_args()
    
def load_cfg():
    with open('configuration.json', 'r') as fp:
        cfg = json.load(fp)
    return cfg


def main(cfg):
    db = sqlite3.connect(cfg['sqlite3_db_filename'])
    if args.room:
        q = """
SELECT timestamp, device_id, co2, detailed_location, private
FROM readings JOIN device_location USING (device_id)
WHERE room = ?
AND start <= timestamp
AND (finish IS NULL OR timestamp < finish)
ORDER BY timestamp, device_id
"""
        for row in db.execute(q, (args.room, )):
            print(row)

    elif args.device_id:
        q = """
SELECT timestamp, co2, room, detailed_location, private
FROM readings JOIN device_location USING (device_id)
WHERE device_id = ?
AND start <= timestamp
AND (finish IS NULL OR timestamp < finish)
ORDER BY timestamp
"""
        for row in db.execute(q, (args.device_id, )):
            print(row)

if __name__ == "__main__":
    cfg = load_cfg()
    main(cfg)

