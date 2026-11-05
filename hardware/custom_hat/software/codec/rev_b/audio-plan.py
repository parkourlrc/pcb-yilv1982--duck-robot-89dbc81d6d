import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser(description="Generate an offline Rev B.0 ALSA routing plan")
parser.add_argument("--microphone", choices=("none", "onboard", "external-stereo"), default="onboard")
parser.add_argument("--speaker", action="store_true")
arguments = parser.parse_args()
catalog_path = Path(__file__).resolve().parents[1] / "control-catalog.json"
catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
controls = catalog["controls"]
settings = {}
for name, specification in controls.items():
    if specification["type"] != "ENUMERATED" and (name.endswith(("Bypass Volume", "Bypass Switch", "Playback Volume")) or " Mixer " in name and name.endswith(" Switch")):
        settings[name] = [0] * specification["count"]
settings.update({
    "PCM Playback Volume": [47,47],
    "AGC Switch": [0,0],
    "De-emphasis Switch": [0,0],
    "PGA Capture Volume": [0,0],
    "ADC HPF Cut-off": [0,0],
    "Left DAC Mux": [0],
    "Right DAC Mux": [0],
    "Line DAC Playback Volume": [0,105 if arguments.speaker else 0],
    "Right Line Mixer DACL1 Playback Volume": [105 if arguments.speaker else 0],
    "Right Line Mixer DACL1 Switch": [int(arguments.speaker)],
    "Right Line Mixer DACR1 Switch": [int(arguments.speaker)],
    "Right PGA Mixer Mic2R Switch": [int(arguments.microphone=="onboard")],
    "Left PGA Mixer Line1L Switch": [int(arguments.microphone=="external-stereo")],
    "Right PGA Mixer Line1R Switch": [int(arguments.microphone=="external-stereo")],
})
for side in ("Left","Right"):
    for line in ("Line1L","Line1R"):
        name = side+" "+line+" Mux"
        settings[name] = [controls[name]["items"].index("single-ended")]
mute = ["Line Playback Switch","HP Playback Switch","HPCOM Playback Switch","PGA Capture Switch"]
operations = [{"phase":"mute","control":name,"values":[0,0]} for name in mute]
operations += [{"phase":"configure","control":name,"values":values} for name,values in settings.items()]
operations += [
    {"phase":"enable","control":"Line Playback Switch","values":[0,int(arguments.speaker)]},
    {"phase":"enable","control":"PGA Capture Switch","values":[int(arguments.microphone=="external-stereo"),int(arguments.microphone!="none")]},
]
for operation in operations:
    specification = controls[operation["control"]]
    maximum = len(specification["items"])-1 if specification["type"]=="ENUMERATED" else specification["maximum"]
    if len(operation["values"])!=specification["count"] or any(value<0 or value>maximum for value in operation["values"]):
        raise ValueError("Invalid control: "+operation["control"])
print(json.dumps({"card_id":"DuckHATB","revision":"B.0 candidate","microphone":arguments.microphone,"speaker":arguments.speaker,"mclk_hz":12000000,"operations":operations,"plan_only":True,"hardware_validated":False},ensure_ascii=False,indent=2))
