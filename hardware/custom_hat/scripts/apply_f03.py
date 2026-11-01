"""Recovery-plan fix F03: BMI088 footprint and I2C/CSB contract.

Findings from the audit (BST-BMI088-DS000-19 Rev 1.9, p52/53/55):
- recommended pads are 0.675 x 0.25 mm at 0.5 mm pitch, 7 pads per long side
  plus one pad at each short end (pin 16 / pin 8)
- CSB2 (pin 5) is DNC in I2C mode; only CSB1 (pin 14) selects the interface
- VDD (pin 3) and VDDIO (pin 11) each want a local 100 nF

The project footprint was a hand-made short-pad version with pin 8 / pin 16
swapped relative to the vendor drawing. KiCad ships the vendor land pattern as
Package_LGA:Bosch_LGA-16_4.5x3mm_P0.5mm_LayoutBorder7x1y_ClockwisePinNumbering
(0.25 x 0.675 pads, 0.5 pitch, clockwise numbering), so use that instead of
maintaining a private copy.
"""
from pathlib import Path

GEN = Path("hardware/custom_hat/scripts/generate_rev_a.py")
LIB_ID = "Package_LGA:Bosch_LGA-16_4.5x3mm_P0.5mm_LayoutBorder7x1y_ClockwisePinNumbering"


def main():
    t = GEN.read_text(encoding="utf-8")

    old = ('imu.component("Connector_Generic:Conn_01x16", "U501", "BMI088", 127, 101.6, '
           '{"1":None, "2":"POWER_GND", "3":"+3V3", "4":"POWER_GND", "5":"+3V3", "6":"POWER_GND", '
           '"7":"+3V3", "8":"I2C5_SCL", "9":"I2C5_SDA", "10":"POWER_GND", "11":"+3V3", '
           '"12":"BMI_INT3_TP", "13":None, "14":"+3V3", "15":"+3V3", "16":"BMI_INT1_TP"}, '
           '"duck:Bosch_LGA-16_3x4.5mm_P0.5mm")')
    new = ('imu.component("Connector_Generic:Conn_01x16", "U501", "BMI088", 127, 101.6, '
           '{"1":None, "2":"POWER_GND", "3":"+3V3", "4":"POWER_GND", "5":None, "6":"POWER_GND", '
           '"7":"+3V3", "8":"I2C5_SCL", "9":"I2C5_SDA", "10":"POWER_GND", "11":"+3V3", '
           '"12":"BMI_INT3_TP", "13":None, "14":"+3V3", "15":"+3V3", "16":"BMI_INT1_TP"}, '
           f'"{LIB_ID}")')
    if old not in t:
        raise SystemExit("U501 line not found")
    t = t.replace(old, new)

    # local decoupling for VDD and VDDIO, as the datasheet asks
    anchor = '    imu.component("Connector_Generic:Conn_01x04", "J502"'
    caps = ('''    imu.component("Device:C", "C319", "100nF", 60, 120, {"1":"+3V3", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    imu.component("Device:C", "C320", "100nF", 100, 120, {"1":"+3V3", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
''')
    if anchor not in t:
        raise SystemExit("J502 anchor not found")
    t = t.replace(anchor, caps + anchor, 1)

    t = t.replace(
        'imu.text("BMI088 Rev1.9 contract: accel SDO1=3V3 (0x19), gyro SDO2=GND (0x68), PS=3V3, CSB2=3V3 (I2C mode requires CSB1/CSB2 high). Pin 2 is GND despite NC name.", 35, 35)',
        'imu.text("BMI088 Rev1.9 p52/53: accel SDO1=3V3 (0x19), gyro SDO2=GND (0x68), PS=3V3 selects I2C, CSB2 pin5 is DNC in I2C mode, CSB1 pin14=3V3. Pin 2 is GND despite its NC name. C319/C320 are the local 100nF for VDD/VDDIO.", 35, 35)')

    GEN.write_text(t, encoding="utf-8")
    print("U501 -> KiCad vendor land pattern; CSB2 open; C319/C320 added")


if __name__ == "__main__":
    main()
