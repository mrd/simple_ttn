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
argparser.add_argument('-J', '--javascript', action='store_true',
                       help='Javascript/HTML output')
argparser.add_argument('-D', '--date', metavar='DATE', type=str,
                       help='Search for data from a particular date')
argparser.add_argument('--amber-y-value', metavar='N', type=int, default=600,
                       help='Amber horizontal line at N ppm CO2')
argparser.add_argument('--red-y-value', metavar='N', type=int, default=800,
                       help='Red horizontal line at N ppm CO2')
argparser.add_argument('--strip-device-id-prefix', metavar='N', type=int, default=13,
                       help='Number of characters to strip off device_ids in display')
args = argparser.parse_args()
    
def load_cfg():
    with open('configuration.json', 'r') as fp:
        cfg = json.load(fp)
    return cfg

def js_output(db, cur, fixed, devs):
    # db - sqlite3 connection
    # cur - cursor for query (should have 'timestamp' and 'co2' columns)
    # fixed - fixed parameters that are unchanging (i.e. the WHERE condition)
    # devs - devices we expect to see in the results
    title = ', '.join([f"{k}={v}" for k, v in fixed.items()])
    print("""
<html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/dygraph/2.1.0/dygraph.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/dygraph/2.1.0/dygraph.css">
<script type="text/javascript">
const data = [""")
    xval = None
    yvals = {d['device_id']:0 for d in devs}
    first=True
    for row in cur:
        ts = row['timestamp']
        co2 = row['co2']
        if xval is None or ts != xval:
            if xval is not None:
                # previous xval (data row) is finished, print it
                if not first: print(", ", end="")
                else: first = False
                print(f"[new Date('{xval}')", end="")
                for y in yvals.values():
                    if y == 0: y = "null" # treat 0 as a gap in the data
                    print(f", {y}", end="")
                print("]")

            # now working on new xval (data row), reset yval table
            xval = ts
            yvals = {d:0 for d in yvals}

        # add yval to current table indexed by device_id
        yvals[row['device_id']] = co2
    #labels = ["timestamp"] + list([d['device_id'][args.strip_device_id_prefix:] for d in devs])
    labels = ["timestamp"] + list([d['detailed_location'] for d in devs])
    print("];")
    print("const ambYval = {}, redYval = {};".format(args.amber_y_value, args.red_y_value))
    print("""
function legendFormatter(data) {
  if (data.x == null) return '';  // no selection
  function f(v) {
    var yCSS = '';
    if(v.y == null) return '';
    if(v.isHighlighted) yCSS = 'font-weight: bolder;';
    return '<tr style="' + yCSS + 'color: ' + v.color + '"><td>' + v.dashHTML + '</td><td>device ' + v.labelHTML + ':</td><td>CO<sub>2</sub> = ' + v.yHTML + ' ppm</td></tr>';
  };
  return '<strong>' + data.xHTML + '</strong><table>' + data.series.map(f).join(' ') + '</table>';
}

const options = {
connectSeparatedPoints: true,
legendFormatter: legendFormatter,
highlightSeriesOpts: { strokeWidth: 2 },
//labelsDiv: 'legend',
legend: 'follow',
ylabel: 'CO<sub>2</sub> (ppm)',
labels: {labels},
title: '{title}',
underlayCallback: function (canvas, area, g) {
    var ambline = g.toDomYCoord(ambYval+2);
    var redline = g.toDomYCoord(redYval+2);

    canvas.fillStyle = "rgba(255, 191, 0, 1.0)";
    canvas.fillRect(area.x, ambline, area.w, 2);
    canvas.fillStyle = "rgba(255, 0, 0, 1.0)";
    canvas.fillRect(area.x, redline, area.w, 2);
  }
};
$(document).ready(function() {
const g = new Dygraph(document.getElementById("chart"), data, options);
});

</script>
</head>
<body> 
<div style="width:100%; height="300px" id="chart"></div>
<div id="legend"></div>
</body></html>
""".replace('{labels}', str(labels)).replace('{title}', title))

def get_devices_in_room(db, room):
    q = """
SELECT DISTINCT device_id, detailed_location
FROM readings JOIN device_location USING (device_id)
WHERE room = ?
AND start <= timestamp
AND (finish IS NULL OR timestamp < finish)
AND (? OR DATE(timestamp) = DATE(?))
GROUP BY strftime('%s', timestamp)/300, device_id
ORDER BY device_id"""
    devs = []
    for row in db.execute(q, (room, args.date is None, args.date)):
        devs.append({'device_id': row[0], 'detailed_location': row[1]})
    return devs

def main(cfg):
    db = sqlite3.connect(cfg['sqlite3_db_filename'])
    db.row_factory = sqlite3.Row
    if args.room:
        devs = get_devices_in_room(db, args.room)

        q = """
SELECT datetime(strftime('%s', timestamp)/300*300, 'unixepoch') AS timestamp, device_id, co2, detailed_location, private
FROM readings JOIN device_location USING (device_id)
WHERE room = ?
AND start <= timestamp
AND (finish IS NULL OR timestamp < finish)
AND (? OR DATE(timestamp) = DATE(?))
GROUP BY strftime('%s', timestamp)/300, device_id
ORDER BY timestamp, device_id
"""
        cur = db.cursor()
        cur.execute(q, (args.room, args.date is None, args.date))

        if args.javascript:
            # {'timestamp': row[0], 'device_id': row[1], 'co2': row[2], 'detailed_location': row[3], 'private': row[4]}
            
            # js_output()
            js_output(db, cur, {'room': args.room}, devs)
        else:
            for row in cur:
                print({k:row[k] for k in sorted(row.keys())})

    elif args.device_id:
        q = """
SELECT timestamp, co2, room, detailed_location, private
FROM readings JOIN device_location USING (device_id)
WHERE device_id = ?
AND start <= timestamp
AND (finish IS NULL OR timestamp < finish)
ORDER BY timestamp
"""
        if args.javascript:
            pass
            #{'timestamp', 'co2', 'room', 'detailed_location', 'private'}
            #js_output({'timestamp': row[0], 'device_id': row[1], 'co2': row[2], 'detailed_location': row[3], 'private': row[4]})
        else:
            for row in db.execute(q, (args.device_id, )):
                print(row)

if __name__ == "__main__":
    cfg = load_cfg()
    main(cfg)

