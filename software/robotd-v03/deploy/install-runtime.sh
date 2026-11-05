#!/bin/sh
# Run as root after transferring verified runtime artifacts to the fixed staging directory.
# Installs the baseline without starting robotd or touching the serial bus.
set -eu
stage=/home/radxa/duck-runtime-stage-20261031
studio=/home/radxa/studio-dev
runtime=/opt/robot/daemon/releases/duck-v03-20261031
python_root=/opt/duck-robot/python-3.13.18
[ "$(id -u)" -eq 0 ]
[ "$(uname -m)" = aarch64 ]
[ ! -e /opt/robot/daemon/current ]
[ ! -e /etc/robot/feetech-ft5/robotd.toml ]
[ ! -e /etc/systemd/system/robotd.service ]
[ ! -e /etc/systemd/system/microduck-studio.service ]
[ ! -e /usr/local/bin/robotd ]
[ ! -e /usr/local/bin/robotctl ]
[ ! -e /usr/local/bin/padd ]
printf '%s  %s\n' \
  578d9da1983463ffb0c8c98ab0da2f18177f44069328eb0af847860c1eb05c3e "$stage/python.tar.gz" \
  725b74cd93660a312970a44879abe5b75e8becf108499a1b8798961e48ca5f00 "$studio/deploy/native/robotd" \
  dc1c7043a108964583fc09a11e3d6f87a25e259c346f7ce9154e77500a0881ec "$studio/deploy/native/padd" | sha256sum -c -
install -d -m 0755 "$python_root" "$runtime/bin" /opt/robot/onnxruntime/1.28.0 /etc/robot/feetech-ft5
tar -xzf "$stage/python.tar.gz" -C "$python_root" --strip-components=1
tar -xzf "$stage/onnxruntime.tar.gz" -C /opt/robot/onnxruntime/1.28.0 --strip-components=1
install -m 0755 "$studio/deploy/native/robotd" "$runtime/bin/robotd"
install -m 0755 "$studio/deploy/native/padd" "$runtime/bin/padd"
install -m 0755 "$stage/robotctl-baseline" "$runtime/bin/robotctl"
install -m 0644 "$stage/deploy/robotd.toml" /etc/robot/feetech-ft5/robotd.toml
install -m 0644 "$stage/deploy/robotd.service" /etc/systemd/system/robotd.service
install -m 0644 "$stage/deploy/microduck-studio.service" /etc/systemd/system/microduck-studio.service
ln -s "$runtime" /opt/robot/daemon/current
ln -s /etc/robot/feetech-ft5/robotd.toml /etc/robot/robotd.toml
for binary in robotd robotctl padd; do
  ln -s "/opt/robot/daemon/current/bin/$binary" "/usr/local/bin/$binary"
done
# Studio's model validator resolves this upstream fixed path and reads ORT_DYLIB_PATH
# from robotd.service. Keep it pointed at the same installed executable.
install -d -m 0755 /opt/robot/feetech-ft5-r5
ln -s /opt/robot/daemon/current/bin/robotd /opt/robot/feetech-ft5-r5/robotd
sh "$studio/deploy/install.sh" radxa
systemctl daemon-reload
systemctl enable --now microduck-studio.service
"$python_root/bin/python3.13" --version
/usr/local/bin/robotd --version
systemctl is-active microduck-studio.service
systemctl show robotd.service -p ActiveState -p UnitFileState
