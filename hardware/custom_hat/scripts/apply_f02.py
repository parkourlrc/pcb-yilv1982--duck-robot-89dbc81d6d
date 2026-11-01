"""Recovery-plan fix F02: half-duplex TTL chain and the servo power branch.

Current state was three separate nets: UART2_TX -> J403.1, UART2_RX -> J403.2,
DXL_DATA -> J401.2/J402.2, with no buffer at all, and SERVO_VBAT was never tied
to the battery input on the board.

This adds the classic two-buffer half-duplex interface (SN74LVC1G126 for the
transmit direction, SN74LVC1G125 for receive, one direction pin shared by both
because the enable polarities are complementary), a 0 ohm battery-to-servo
branch, and switches the EH sockets to the project's documented pin order
(1=GND, 2=VBAT, 3=DATA).

Pin numbers come from KiCad's 74xGxx symbols, which match the TI SOT-23-5
pinout: 1 = OE//OE, 2 = A, 3 = GND, 4 = Y, 5 = VCC.
"""
from pathlib import Path

GEN = Path("hardware/custom_hat/scripts/generate_rev_a.py")


def main():
    t = GEN.read_text(encoding="utf-8")

    old_ttl = '''    ttl.component("Connector_Generic:Conn_01x03", "J401", "DYNAMIXEL_TTL_1", 100, 75, {"1":"SERVO_VBAT", "2":"DXL_DATA", "3":"POWER_GND"}, "Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical")
    ttl.component("Connector_Generic:Conn_01x03", "J402", "DYNAMIXEL_TTL_2", 100, 115, {"1":"SERVO_VBAT", "2":"DXL_DATA", "3":"POWER_GND"}, "Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical")'''
    new_ttl = '''    # EH sockets follow the project's documented order: 1=GND, 2=VBAT, 3=DATA
    ttl.component("Connector_Generic:Conn_01x03", "J401", "DYNAMIXEL_TTL_1", 100, 75, {"1":"POWER_GND", "2":"SERVO_VBAT", "3":"DXL_DATA"}, "Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical")
    ttl.component("Connector_Generic:Conn_01x03", "J402", "DYNAMIXEL_TTL_2", 100, 115, {"1":"POWER_GND", "2":"SERVO_VBAT", "3":"DXL_DATA"}, "Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical")
    # half-duplex interface: 1G126 transmits (OE high), 1G125 receives (/OE low).
    # One DIR net drives both because their enables are complementary.
    ttl.component("74xGxx:74LVC1G126", "U801", "SN74LVC1G126", 190, 60, {"1":"DXL_DIR", "2":"UART2_TX", "3":"POWER_GND", "4":"DXL_DATA", "5":"+3V3"}, "Package_TO_SOT_SMD:SOT-23-5")
    ttl.component("74xGxx:74LVC1G125", "U802", "SN74LVC1G125", 240, 60, {"1":"DXL_DIR", "2":"DXL_DATA", "3":"POWER_GND", "4":"UART2_RX", "5":"+3V3"}, "Package_TO_SOT_SMD:SOT-23-5")
    # default to receive when the GPIO is high-Z at boot
    ttl.component("Device:R", "R310", "100k", 240, 90, {"1":"DXL_DIR", "2":"POWER_GND"}, "Resistor_SMD:R_0402_1005Metric")
    # single battery input with an explicit branch to the servo rail
    ttl.component("Device:R", "R309", "0R", 60, 60, {"1":"VBATT_2S_IN", "2":"SERVO_VBAT"}, "Resistor_SMD:R_0806_2012Metric")'''
    if old_ttl not in t:
        raise SystemExit("TTL block not found")
    t = t.replace(old_ttl, new_ttl)

    # direction pin: Radxa 40P pin 11 (SPI3 pin, otherwise unused on this HAT)
    old_pins = ('nets = {1:"+3V3",2:"+5V",4:"+5V",6:"POWER_GND",8:"UART2_TX",9:"POWER_GND",'
                '10:"UART2_RX",12:"I2S_BCLK",13:"I2S_MCLK",14:"POWER_GND",17:"+3V3",20:"POWER_GND",'
                '25:"POWER_GND",29:"I2C5_SCL",30:"POWER_GND",31:"I2C5_SDA",34:"POWER_GND",'
                '35:"I2S_LRCK",38:"I2S_SDI",39:"POWER_GND",40:"I2S_SDO"}')
    new_pins = ('nets = {1:"+3V3",2:"+5V",4:"+5V",6:"POWER_GND",8:"UART2_TX",9:"POWER_GND",'
                '10:"UART2_RX",11:"DXL_DIR",12:"I2S_BCLK",13:"I2S_MCLK",14:"POWER_GND",17:"+3V3",'
                '20:"POWER_GND",25:"POWER_GND",29:"I2C5_SCL",30:"POWER_GND",31:"I2C5_SDA",'
                '34:"POWER_GND",35:"I2S_LRCK",38:"I2S_SDI",39:"POWER_GND",40:"I2S_SDO"}')
    if old_pins not in t:
        raise SystemExit("40P net map not found")
    t = t.replace(old_pins, new_pins)

    t = t.replace(
        'ttl.text("TTL-only shared DATA path with automatic TX direction control. No RS485 transceiver and no RX AND-gate.", 35, 35)',
        'ttl.text("Half-duplex TTL: 1G126 drives DATA from UART2_TX (OE=DXL_DIR high), 1G125 reads DATA into UART2_RX (/OE=DXL_DIR low). R310 pulls DXL_DIR low at boot so the board listens. One bus, two EH sockets, no RS485.", 35, 35)')
    t = t.replace(
        'ttl.text("UART2 console conflict remains a software bring-up constraint; do not assume console disabled.", 35, 145)',
        'ttl.text("EH pin order: 1=GND, 2=VBAT, 3=DATA. R309 (0R) is the battery-to-servo branch. UART2 is the boot console until disabled in software.", 35, 145)')

    GEN.write_text(t, encoding="utf-8")
    print("F02 applied: buffers, DIR, EH pin order, battery branch")


if __name__ == "__main__":
    main()
