#!/bin/bash

[ -n "$1" ] || exit 1
[ -n "$2" ] || exit 1
[ -n "$3" ] || exit 1

wdir="$1"
cfg="$2"
dest="$3"

filename="`date -I`.json"

tmpfile="$dest/.$filename"
destfile="$dest/$filename"

cd "$wdir"
python3 dump_readings.py --config "$cfg" -D "`date -I`" -j > "$tmpfile" && mv "$tmpfile" "$destfile"

