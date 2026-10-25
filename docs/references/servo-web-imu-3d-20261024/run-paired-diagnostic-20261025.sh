#!/bin/sh
set -eu
log="/home/radxa/imu200-paired-$(date -u +%Y%m%dT%H%M%SZ).jsonl"
restore() {
    systemctl --user start duck-servo-web.service
    systemctl --user is-active duck-servo-web.service
}
trap restore EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
systemctl --user stop duck-servo-web.service
if fuser /dev/ttyS2 >/dev/null 2>&1; then
    echo 'Serial port still occupied; refusing diagnostic.' >&2
    exit 1
fi
set -C
python3 /tmp/duck-imu200-paired-diagnostic-20261025.py "$@" > "$log"
echo "CAPTURE=$log"
tail -n 7 "$log"
