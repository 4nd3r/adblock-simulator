#!/bin/sh -e

./adblock_simulator.py \
    -f '||example.net^' \
    -f 'test.filters' \
    -h '0.0.0.0 example.org' \
    -h 'test.hosts' \
    -s 'example.com' \
    -d 'example.net' \
    -d 'https://example.example.org' \
    -d 'test.destinations' \
    "$@"
