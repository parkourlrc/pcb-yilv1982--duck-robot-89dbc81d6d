#!/bin/sh
set -eu
export PATH="/opt/duck-robot/rust-1.99/bin:/opt/duck-robot/build-env/bin:$PATH"
export CARGO_HOME=/opt/duck-robot/cargo
cd /root/duck-robot-control47
evidence=/mnt/c/Projects/duck-robot/docs/references/b-feetech-policy-deployment-20261024
if cargo test --offline --locked -p duck-control v03_transport_tests -- --test-threads=1 > "$evidence/servo-first-transport-tests-20261101.log" 2>&1; then
    tail -15 "$evidence/servo-first-transport-tests-20261101.log"
else
    tail -70 "$evidence/servo-first-transport-tests-20261101.log"
    exit 1
fi
if cargo zigbuild --offline --locked --release --target aarch64-unknown-linux-gnu.2.31 -p robotd > "$evidence/servo-first-arm64-build-20261101.log" 2>&1; then
    tail -12 "$evidence/servo-first-arm64-build-20261101.log"
    sha256sum target/aarch64-unknown-linux-gnu/release/robotd
else
    tail -70 "$evidence/servo-first-arm64-build-20261101.log"
    exit 1
fi
