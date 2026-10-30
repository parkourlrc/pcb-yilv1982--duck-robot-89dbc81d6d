"""Recovery-plan F04 (second half): microphone input and speaker amplifier.

The audit found U701 pins 10-16 (all analog inputs, including MICBIAS) left as
no-connect, and J504 only bringing out the headphone output - so neither
recording nor a speaker was possible.

This adds:
- a single-ended electret mic path: MICBIAS -> bias resistor -> J505, AC coupling
  into MIC1LP, MIC1LM AC-coupled to ground
- a mono class-D amplifier (PAM8302A) fed from LEFT_LOP, driving a 2-pin speaker
  connector

PAM8302 pin numbers are from KiCad's Amplifier_Audio symbol (SOIC-8):
1=/SD, 2=NC, 3=IN+, 4=IN-, 5=OUT+, 6=VDD, 7=GND, 8=OUT-.
"""
from pathlib import Path

GEN = Path("hardware/custom_hat/scripts/generate_rev_a.py")


def main():
    t = GEN.read_text(encoding="utf-8")

    # wire the analog pins that were left open
    t = t.replace('"10": None, "11": None, "12": None, "13": None, "14": None, "15": None, "16": None,',
                  '"10": "AUDIO_MIC_AC", "11": "AUDIO_MIC_REF", "12": None, "13": None, "14": None, '
                  '"15": "AUDIO_MIC_BIAS", "16": None,')
    t = t.replace('"27": None, "28": None, "29": None, "30": None,',
                  '"27": "AUDIO_LINE_L", "28": None, "29": None, "30": None,')

    anchor = '    audio.component("Device:C", "C317"'
    add = '''    # --- microphone: single-ended electret, biased from MICBIAS ---
    audio.component("Connector_Generic:Conn_01x02", "J505", "MIC_IN", 60, 160, {"1":"AUDIO_MIC", "2":"POWER_GND"}, "Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical")
    audio.component("Device:R", "R312", "2.2k", 100, 160, {"1":"AUDIO_MIC_BIAS", "2":"AUDIO_MIC"}, "Resistor_SMD:R_0402_1005Metric")
    audio.component("Device:C", "C325", "1uF", 140, 160, {"1":"AUDIO_MIC", "2":"AUDIO_MIC_AC"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C326", "1uF", 180, 160, {"1":"POWER_GND", "2":"AUDIO_MIC_REF"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C327", "100nF", 220, 160, {"1":"AUDIO_MIC_BIAS", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    # --- speaker: mono class-D from LEFT_LOP ---
    audio.component("Amplifier_Audio:PAM8302AAD", "U803", "PAM8302A", 280, 210, {"1":"AUDIO_AMP_EN", "2":None, "3":"AUDIO_AMP_INP", "4":"AUDIO_AMP_INN", "5":"SPK_P", "6":"+5V", "7":"POWER_GND", "8":"SPK_N"}, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
    audio.component("Device:R", "R311", "100k", 280, 250, {"1":"AUDIO_AMP_EN", "2":"+3V3"}, "Resistor_SMD:R_0402_1005Metric")
    audio.component("Device:C", "C321", "1uF", 320, 210, {"1":"AUDIO_LINE_L", "2":"AUDIO_AMP_INP"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C322", "1uF", 360, 210, {"1":"AUDIO_AMP_INN", "2":"POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    audio.component("Device:C", "C323", "10uF", 320, 250, {"1":"+5V", "2":"POWER_GND"}, "Capacitor_SMD:C_0805_2012Metric")
    audio.component("Connector_Generic:Conn_01x02", "J506", "SPEAKER", 360, 250, {"1":"SPK_P", "2":"SPK_N"}, "Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical")
'''
    if anchor not in t:
        raise SystemExit("audio anchor not found")
    t = t.replace(anchor, add + anchor, 1)

    t = t.replace(
        'audio.text("TLV320AIC3104, pinout from the TI IBIS model.',
        'audio.text("Mic: electret biased from MICBIAS via R312 2.2k, AC-coupled by C325 into MIC1LP; MIC1LM is AC-coupled to GND by C326. Speaker: PAM8302A from LEFT_LOP through C321, /SD pulled up by R311, 2-pin speaker on J506.", 35, 250)\n    audio.text("TLV320AIC3104, pinout from the TI IBIS model.')

    GEN.write_text(t, encoding="utf-8")
    print("mic input and speaker amp added")


if __name__ == "__main__":
    main()
