"""Apply recovery-plan fixes F01 (AP64350) and F04 (I2S direction) to the schematic.

F01: U301 was a generic 8-pin connector symbol on a PowerPAK footprint whose pads
collapsed into 1,2,3,4,5,5,5,5,5 - the buck was never actually wired. This uses
the real 9-pin symbol and the datasheet SO-8EP land pattern.

F04: Radxa pin38 is I2S3_SDI (SoC input) and pin40 is I2S3_SDO (SoC output); the
codec's DIN(4) must take the SoC output and DOUT(5) must feed the SoC input. The
previous mapping connected input-to-input / output-to-output.
"""
from pathlib import Path

GEN = Path("hardware/custom_hat/scripts/generate_rev_a.py")


def main():
    t = GEN.read_text(encoding="utf-8")

    old_u301 = ('power.component("Connector_Generic:Conn_01x08", "U301", "AP64350SP", 190, 90, '
                '{"1":"BUCK_BST", "2":"VBATT_2S_IN", "3":"BUCK_EN", "4":"BUCK_RT", "5":"+5V_FB", '
                '"6":"BUCK_COMP", "7":"POWER_GND", "8":"BUCK_SW"}, "Package_SO:PowerPAK_SO-8_Single")')
    new_u301 = ('power.component("duck:AP64350", "U301", "AP64350", 190, 90, '
                '{"1":"BUCK_BST", "2":"VBATT_2S_IN", "3":"BUCK_EN", "4":"BUCK_RT", "5":"+5V_FB", '
                '"6":"BUCK_COMP", "7":"POWER_GND", "8":"BUCK_SW", "9":"POWER_GND"}, '
                '"duck:SO-8EP_AP64350")')
    if old_u301 not in t:
        raise SystemExit("U301 line not found")
    t = t.replace(old_u301, new_u301)

    # I2S direction: DIN takes the SoC output, DOUT feeds the SoC input
    old_i2s = ('"1": "I2S_MCLK", "2": "I2S_BCLK", "3": "I2S_LRCK", "4": "I2S_SDI", "5": "I2S_SDO",')
    new_i2s = ('"1": "I2S_MCLK", "2": "I2S_BCLK", "3": "I2S_LRCK", "4": "I2S_SDO", "5": "I2S_SDI",')
    if old_i2s not in t:
        raise SystemExit("I2S mapping not found")
    t = t.replace(old_i2s, new_i2s)

    t = t.replace(
        'power.text("AP64350 pin map: 1 BST, 2 VIN, 3 EN, 4 RT/CLK, 5 FB, 6 COMP, 7 GND, 8 SW; EP=GND.", 35, 35)',
        'power.text("AP64350 pin map: 1 BST, 2 VIN, 3 EN, 4 RT/CLK, 5 FB, 6 COMP, 7 GND, 8 SW; EP is pin 9 and must go to GND (DS41976 p3).", 35, 35)')

    GEN.write_text(t, encoding="utf-8")
    print("U301 -> duck:AP64350 (9 pads), I2S direction corrected")


if __name__ == "__main__":
    main()
