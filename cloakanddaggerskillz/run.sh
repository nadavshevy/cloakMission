#!/bin/sh

MAP=$3
if [ -z "$3" ]; then
    MAP="./maps/default_map.map"
fi

if [ $# -lt 2 ]; then
    echo "Usage: $0 <bot1> <bot2> [map]"
    exit 1
fi

python "./run.py" -e -E -d --debug-in-replay --load-time 10000 --log-dir lib/game_logs --map-file $MAP $1  $2
