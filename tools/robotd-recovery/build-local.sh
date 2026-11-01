#!/bin/sh
# Local WSL build only. No SSH, service changes or device access.
set -eu
export PATH=/opt/duck-robot/rust-1.99/bin:/opt/duck-robot/build-env/bin:/usr/local/bin:/usr/bin:/bin
export CARGO_HOME=/opt/duck-robot/cargo
project=/mnt/c/Projects/duck-robot/tools/robotd-recovery
build=/root/duck-robot-recovery-20261101
if [ "${1:-}" = baseline-check ]; then
    baseline=/root/duck-robot-recovery-baseline-20261101
    mkdir -p "$baseline"
    tar -xzf /mnt/c/Projects/duck-robot/training/logs/b-feetech-walk-20261024/controller-preparation-20261031/controller-source.tar.gz \
        -C "$baseline" --strip-components=3 fanhao375-Microduck-kissqy-27d7921/microduck-hd1910/firmware
    cd "$baseline"
    # The baseline and candidate must not share crate fingerprints or test binaries.
    cargo test --offline --locked -p robotd --bin robotd tests::r17_empty_snapshot_and_warming_imu_do_not_accept_home -- --exact --test-threads=1 --nocapture
    exit
fi
if [ ! -d "$build" ]; then
    mkdir "$build"
fi
# No old v0.3 build output is used. Preserve this task's incremental build only.
cp -a "$project/.work/firmware/." "$build/"
cd "$build"
case "${1:-check}" in
    check) cargo check --offline --locked -p robotd ;;
    test) cargo test --locked -p robotd --bin robotd recovery::tests -- --test-threads=1 ;;
    guards)
        cargo test --offline --locked -p duck-ipc-proto --lib
        cargo test --offline --locked -p robotd --bin robotd home_start:: -- --test-threads=1
        # This unchanged upstream test fails in pristine control.47 as well;
        # baseline-check records it separately instead of hiding the failure.
        cargo test --offline --locked -p robotd --bin robotd r17_ -- --test-threads=1 --skip tests::r17_empty_snapshot_and_warming_imu_do_not_accept_home
        ;;
    integration)
        export ORT_DYLIB_PATH=/opt/duck-robot/recovery-ort/onnxruntime/capi/libonnxruntime.so.1.28.0
        export RECOVERY_TEST_MODEL=/mnt/c/Projects/duck-robot/training/logs/b-feetech-walk-20261024/runtime-package-review/Microduck-Robotd-FT6-R17/models/1cbf8730eadd75a5704332c9f3c10f60/policy.onnx
        # Deployment HOME is a process-wide OnceLock, just as on the board.
        # Each complete daemon fixture therefore gets its own test process.
        for name in \
            joint_walk_recovery_uses_walk_math_reads_after_torque_and_lease_expires \
            joint_walk_recovery_post_torque_read_failure_never_writes_a_model_target \
            joint_walk_recovery_home_cancels_without_a_second_torque_on \
            joint_walk_recovery_holds_neutral_until_explicit_walk_handoff
        do
            cargo test --offline --locked -p robotd --bin robotd "feetech_recovery_tests::$name" -- --exact --test-threads=1
        done
        ;;
    build) cargo zigbuild --offline --locked --release --target aarch64-unknown-linux-gnu.2.31 -p robotd ;;
    *) exit 2 ;;
esac
