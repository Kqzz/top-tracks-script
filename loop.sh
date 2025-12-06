#!/bin/bash

# Usage: ./loop.sh <minutes> <main.py args>

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <minutes> <main.py args>"
  exit 1
fi

MINUTES="$1"
shift

while true; do
  python3 main.py "$@"
  sleep "$((MINUTES * 60))"
done
