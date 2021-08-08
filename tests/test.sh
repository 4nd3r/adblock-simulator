#!/bin/sh -e

../adblock_simulator.py \
    -s 'example.com' \
    \
    -f '||example.net^' \
    -d 'http://example.net' \
    -d 'sub.example.net' \
    \
    -h '0.0.0.0 example.org' \
    -d 'https://example.org' \
    -d 'sub.example.org' \
    \
    -f 'test.filter' \
    -h 'test.hosts' \
    -d 'test.destinations' \
    -d 'kvlt.ee' \
    "$@"
