#!/bin/sh
# Read-only serial capture, with service restoration on exit.
set -eu
log="/home/radxa/imu200-raw-$(date -u +%Y%m%dT%H%M%SZ).jsonl"
restore() {
    systemctl --user start duck-servo-web.service
    systemctl --user is-active duck-servo-web.service
}
trap restore EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
systemctl --user stop duck-servo-web.service
if fuser /dev/ttyS2 >/dev/null 2>&1; then
    echo 'Serial port is still occupied; refusing capture.' >&2
    exit 1
fi
set -C
python3 /tmp/duck-imu200-raw-capture-20261025.py "$@" > "$log"
echo "CAPTURE=$log"
tail -n 7 "$log"
