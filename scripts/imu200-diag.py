#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IMU 小板（ID 200）只读诊断 + 可选厂商命令（2026-10-24）。

背景：servo-web --imu-bus 上线后 IMU 不出数（四元数全 0、BIT1 告警）。本脚本在
独占总线时直接读 ID 200，按社区 kit 固件协议（imu_to_dxl_protocol.md §6/§8）解码：
- FeeTech 56..70（15 字节契约块）：陀螺 i16×3 + 四元数 half×3 + 计数 + 状态位
- FeeTech 128..147（20 字节完整块）：上面 + 加速度 i16×3
- FeeTech 160..179（厂商窗 20 字节）：magic/CMD/SIM/REPORT_FRAME/STATUS 等
状态位按 §6.4 社区 kit 语义解读（bit0=四元数有效、bit1=计数回绕、bit3=传感器
探测失败、bit4=模拟器、bit7=融合运行中）；注意 servo-web 的 imu_bus.py 按
duck-control 旧语义解读（bit1=通信失败），两套不一样，本脚本两种都标出来。

用法（板上，先停 servo-web 释放 /dev/ttyS2）：
  python3 imu200-diag.py                 # 只读探测：ping + 8 帧契约块 + 3 帧完整块 + 厂商窗
  python3 imu200-diag.py --vcmd 4        # 发厂商命令（4=重启融合, 3=软重启, 2=恢复默认）
                                         # 流程：读回整窗 → 仅改 CMD 字节 → 整窗写回 → 等 3s 复测
"""

import argparse
import struct
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("缺少 pyserial")

PORT = "/dev/ttyS2"
BAUD = 1_000_000
IMU_ID = 200
BLOCK15 = (56, 15)
BLOCK20 = (128, 20)
VENDOR = (160, 20)
VCMD_RESET_SIM = 4   # 重启融合（CONVERGE ~1.5s，四元数归零后恢复）
VCMD_REBOOT = 3      # 50ms 后软复位应用

# §6.4 状态位（社区 kit imu_to_dxl v1 语义）
KIT_BITS = {0x01: "bit0 四元数有效(SFLP_VALID)", 0x02: "bit1 计数回绕(CNT_WRAP)",
            0x04: "bit2 陀螺饱和(GYRO_SAT)", 0x08: "bit3 传感器探测失败(SENSOR_ERR)",
            0x10: "bit4 模拟器", 0x20: "bit5 frozen", 0x40: "bit6 配置未保存(从不置位)",
            0x80: "bit7 融合运行中(FUSION_OK)"}


def frame(sid, inst, params=b""):
    body = bytes([sid, len(params) + 2, inst]) + params
    return b"\xFF\xFF" + body + bytes([(~sum(body)) & 0xFF])


def transact(ser, sid, inst, params=b"", timeout=0.08):
    ser.reset_input_buffer()
    ser.write(frame(sid, inst, params))
    ser.flush()
    dl = time.monotonic() + timeout
    buf = b""
    while time.monotonic() < dl:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
            if len(buf) >= 5 and buf[:2] == b"\xFF\xFF":
                total = 4 + buf[3]
                if len(buf) >= total:
                    if ((~sum(buf[2:total - 1])) & 0xFF) != buf[total - 1] or buf[2] != sid:
                        return None
                    return bytes(buf[5:total - 1])
    return None


def read_reg(ser, addr, n, tries=2):
    for _ in range(tries):
        d = transact(ser, IMU_ID, 0x02, bytes([addr, n]))
        if d is not None and len(d) == n:
            return d
    return None


def half(h):
    """uint16 原始位型 → float（IEEE 754 binary16）。"""
    return struct.unpack("<e", struct.pack("<H", h))[0]


def decode15(b):
    gx, gy, gz = struct.unpack_from("<3h", b, 0)
    qx, qy, qz = (half(v) for v in struct.unpack_from("<3H", b, 6))
    return gx, gy, gz, qx, qy, qz, b[12], b[13], b[14]


def flags_str(bits):
    kit = [name for m, name in KIT_BITS.items() if bits & m] or ["无位置位"]
    return " | ".join(kit)


def probe(ser):
    print("ping:", "在线" if transact(ser, IMU_ID, 0x01) is not None else "无应答")
    print("\n契约块 56..70（8 帧，间隔 0.3s）：")
    for i in range(8):
        b = read_reg(ser, *BLOCK15)
        if b is None:
            print(f"  #{i} 无应答")
        else:
            gx, gy, gz, qx, qy, qz, cnt, bits, rsv = decode15(b)
            print(f"  #{i} gyro=({gx},{gy},{gz})raw quat=({qx:+.4f},{qy:+.4f},{qz:+.4f}) "
                  f"cnt={cnt} flags=0x{bits:02X} rsv={rsv}")
            if i == 0:
                print(f"      flags 释义（kit 语义）：{flags_str(bits)}")
    print("\n完整块 128..147（3 帧）：")
    for i in range(3):
        b = read_reg(ser, *BLOCK20)
        if b is None:
            print(f"  #{i} 无应答")
        else:
            gx, gy, gz = struct.unpack_from("<3h", b, 0)
            qx, qy, qz = (half(v) for v in struct.unpack_from("<3H", b, 6))
            ax, ay, az = struct.unpack_from("<3h", b, 12)
            print(f"  #{i} gyro=({gx},{gy},{gz})raw quat=({qx:+.4f},{qy:+.4f},{qz:+.4f}) "
                  f"accel=({ax},{ay},{az})raw cnt={b[18]} flags=0x{b[19]:02X}")
    v = read_reg(ser, *VENDOR)
    if v is None:
        print("\n厂商窗 160..179：无应答")
    else:
        magic = v[0] | v[1] << 8
        print(f"\n厂商窗 160..179：magic=0x{magic:04X}({'正确' if magic == 0x4D49 else '异常'}) "
              f"cmd={v[2]} sim_mode={v[3]} report_frame={v[8]} proto_lock={v[9]} "
              f"mirror_baud={v[16]} dbg={v[17]} status=0x{v[18]:02X} last_err=0x{v[19]:02X}")
    return v


def send_vcmd(ser, code):
    v = read_reg(ser, *VENDOR)
    if v is None:
        sys.exit("读不到厂商窗，拒绝写")
    magic = v[0] | v[1] << 8
    if magic != 0x4D49:
        sys.exit(f"厂商窗 magic 异常 0x{magic:04X}，拒绝写")
    out = bytearray(v)
    out[2] = code
    d = bytes(out)
    print(f"写回厂商窗（仅 CMD 改为 {code}，其余原样）：{d.hex(' ')}")
    ack = transact(ser, IMU_ID, 0x03, bytes([VENDOR[0]]) + d)
    print("写指令应答：", "有" if ack is not None else "无（写静默也可能正常，靠复测判定）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vcmd", type=int, help="发送厂商命令码（1..7）后复测")
    args = ap.parse_args()
    ser = serial.Serial(PORT, BAUD, timeout=0.01)
    try:
        probe(ser)
        if args.vcmd is not None:
            if not 1 <= args.vcmd <= 7:
                sys.exit("vcmd 范围 1..7")
            send_vcmd(ser, args.vcmd)
            wait = 3.5 if args.vcmd == VCMD_RESET_SIM else 4.0
            print(f"等待 {wait}s 让命令生效 ...")
            time.sleep(wait)
            print("\n===== 复测 =====")
            probe(ser)
    finally:
        ser.close()


if __name__ == "__main__":
    main()
