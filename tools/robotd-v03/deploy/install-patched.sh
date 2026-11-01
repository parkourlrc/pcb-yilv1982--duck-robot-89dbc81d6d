#!/bin/sh
set -eu
stage=/home/radxa/duck-runtime-stage-20261031
bin=/opt/robot/daemon/current/bin
[ "$(id -u)" -eq 0 ]
if systemctl is-active --quiet robotd.service; then
  echo 'Stop robotd before replacing its executable.' >&2
  exit 1
fi
cd "$stage/patched"
sha256sum -c SHA256SUMS
[ ! -e "$bin/robotd.upstream-control47" ]
cp -p "$bin/robotd" "$bin/robotd.upstream-control47"
cp -p "$bin/robotctl" "$bin/robotctl.baseline-r17"
install -m 0755 robotd "$bin/robotd"
install -m 0755 robotctl "$bin/robotctl"
"$bin/robotd" deployment-info
sha256sum "$bin/robotd" "$bin/robotctl"
