#!/usr/bin/env python3
"""Apply the authorized strict-telemetry order experiment in the writable WSL build copy.

Run in WSL. Expected hashes prevent overwriting unrelated source changes.
Produces a replayable incremental patch; does not touch the reference repos.
"""
import difflib
import hashlib
import json
from pathlib import Path

REPO=Path('/mnt/c/Projects/duck-robot')
BUILD=Path('/root/duck-robot-control47')
OUT=REPO/'docs/references/飞特策略模型上机核对'
PATCH=REPO/'software/robotd-v03/patches/v03-servo-first-experiment.patch'
files={
    'duck-control/src/feetech.rs':'de2eb2b927d9f940146ea4936a4bad5643e8b5827afb3155fa6024ac03bf5e83',
    'duck-control/src/feetech_v03_tests.rs':'3f1900a253d1f462ff85c6c97ff86e1abee79be8e6777ebe2c0ad02f4a75762f',
    'robotd/src/feetech_commissioning.rs':'cd9000809b8acdf7b1ae7400781dee2ae68babf520fbb97bbc20e66873cca6b2',
    'robotd/src/feetech_read_only.rs':'2e07af007c7f229e07c1ebac96f427beb0578a4967e5448a7cc83c5615396e02',
}
if PATCH.exists():
    raise SystemExit('Preserve existing experiment patch')
old={}
for name,expected in files.items():
    data=(BUILD/name).read_bytes()
    actual=hashlib.sha256(data).hexdigest()
    if actual!=expected:
        raise SystemExit(f'Baseline hash mismatch {name}: {actual}')
    old[name]=data.decode('utf-8')
new=old.copy()
name='duck-control/src/feetech.rs'
needle='''    fn imu_to_dxl_telemetry(
        &mut self,
        servo_ids: &[u8],
        allow_partial: bool,
    ) -> Result<BTreeMap<u8, Vec<u8>>> {
        let started = Instant::now();'''
replacement=needle.replace('        let started = Instant::now();','''        // This experiment covers commissioning/read-only's complete acquisitions.
        // Partial mode keeps its existing IMU-first acceptance and budget semantics.
        if !allow_partial {
            return self.imu_to_dxl_servo_first(servo_ids);
        }
        let started = Instant::now();''')
assert new[name].count(needle)==1
new[name]=new[name].replace(needle,replacement)
needle='    fn imu_to_dxl_read(&mut self, deadline: Instant) -> Result<Vec<u8>> {'
replacement='''    /// Strict acquisition with the same 20 ms budget, in servo-web's read order.
    /// No partial feedback, retries, changed checksum rules, or added delays.
    fn imu_to_dxl_servo_first(&mut self, servo_ids: &[u8]) -> Result<BTreeMap<u8, Vec<u8>>> {
        let started = Instant::now();
        let deadline = started + Duration::from_millis(TELEMETRY_DEADLINE_MS);
        let mut blocks = self.sync_read_window(
            SYNC_ADDRESS,
            SYNC_LENGTH,
            servo_ids,
            false,
            Some((started, deadline)),
            false,
        )?;
        let servo_trace = self.last_sync.clone();
        let imu_result = self.imu_to_dxl_read(deadline);
        self.last_sync.rx_bytes += servo_trace.rx_bytes;
        self.last_sync.bad_checksums += servo_trace.bad_checksums;
        self.last_sync.discarded += servo_trace.discarded;
        self.last_sync.request_sent |= servo_trace.request_sent;
        self.last_sync.elapsed_us = started.elapsed().as_micros() as u64;
        self.last_sync.deadline_exceeded = Instant::now() >= deadline;
        let raw = imu_result?;
        blocks.insert(IMU_ID, raw);
        Ok(blocks)
    }

'''+needle
assert new[name].count(needle)==1
new[name]=new[name].replace(needle,replacement)
name='duck-control/src/feetech_v03_tests.rs'
new[name]=new[name].replace('fn v03_sends_unicast_then_fifteen_servos_for_both_entry_points()',
    'fn v03_strict_servo_first_keeps_partial_imu_first()')
needle='''        assert_eq!(requests[0], packet(IMU_ID, READ, &[56, 15]).unwrap());
        assert_eq!(requests[1], sync_read_packet(56, 15, &JOINT_IDS).unwrap());'''
replacement='''        let (imu_index, servo_index) = if partial { (0, 1) } else { (1, 0) };
        assert_eq!(requests[imu_index], packet(IMU_ID, READ, &[56, 15]).unwrap());
        assert_eq!(requests[servo_index], sync_read_packet(56, 15, &JOINT_IDS).unwrap());'''
assert new[name].count(needle)==1
new[name]=new[name].replace(needle,replacement)
needle='    assert_eq!(bus.last_sync.missing_ids.len(), 15);'
assert new[name].count(needle)==1
new[name]=new[name].replace(needle,'    assert_eq!(bus.last_sync.missing_ids, vec![IMU_ID]);')
new[name]+='''
#[test]
fn v03_servo_first_still_rejects_every_imu_failure_and_keeps_servo_bytes() {
    for fault in [Fault::MissingImu, Fault::WrongId, Fault::Short, Fault::Status, Fault::Checksum] {
        let (mut bus, peer) = peer(fault);
        assert!(bus.telemetry(&JOINT_IDS).is_err());
        let requests = peer.requests.lock().unwrap();
        assert_eq!(requests.len(), 2);
        assert_eq!(requests[0], sync_read_packet(56, 15, &JOINT_IDS).unwrap());
        assert_eq!(requests[1], packet(IMU_ID, READ, &[56, 15]).unwrap());
        assert_eq!(bus.last_sync.missing_ids, vec![IMU_ID]);
        assert!(bus.last_sync.rx_bytes >= 15 * 21);
        assert!(bus.last_sync.request_sent);
        assert!(!bus.last_sync.partial_received);
        if matches!(fault, Fault::Checksum) {
            assert_eq!(bus.last_sync.bad_checksums, 1);
        }
    }
}

#[test]
fn v03_servo_first_stops_before_imu_when_servo_feedback_is_incomplete() {
    let (mut bus, peer) = peer(Fault::MissingServo);
    assert!(bus.telemetry(&JOINT_IDS).is_err());
    assert_eq!(peer.requests.lock().unwrap().len(), 1);
    assert_eq!(bus.last_sync.missing_ids, vec![JOINT_IDS[0]]);
    assert_eq!(bus.last_sync.rx_bytes, 14 * 21);
    assert!(!bus.last_sync.partial_received);
}
'''
for name in ['robotd/src/feetech_commissioning.rs']:
    assert new[name].count('+duck-v03.1')==1
    new[name]=new[name].replace('+duck-v03.1','+duck-v03.2-servo-first')
manifest={'base':'duck-v03.1','experiment':'duck-v03.2-servo-first','scope':'strict telemetry only; partial entry unchanged','files':[]}
patch=''
for name in files:
    before,after=old[name],new[name]
    patch+=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
    manifest['files'].append({'path':name,'before_sha256':hashlib.sha256(before.encode()).hexdigest(),
                              'after_sha256':hashlib.sha256(after.encode()).hexdigest()})
# All checks above completed before any source mutation.
for name in files:
    if new[name] != old[name]:
        (BUILD/name).write_text(new[name],encoding='utf-8')
PATCH.write_text(patch,encoding='utf-8')
manifest['patch_sha256']=hashlib.sha256(PATCH.read_bytes()).hexdigest()
(OUT/'servo-first-source-manifest-20261101.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
