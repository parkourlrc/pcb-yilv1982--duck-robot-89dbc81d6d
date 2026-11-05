import hashlib
import json
from pathlib import Path
import subprocess

from build_codec_module import linux_path, wsl
from verify_codec_overlay import get, symbol


root=Path(__file__).resolve().parents[3]
directory=root/"hardware/custom_hat/software/codec/rev_b"
evidence=root/"docs/references/扩展板乙版降本"
sources=root/"docs/references/扩展板电路仿真工具/driver-compatibility-20261031/sources"
source=directory/"duck-hat-revb-audio.dts"
overlay=directory/"duck-hat-revb-audio.dtbo"
commands=[]


def execute(*arguments):
    result=subprocess.run(wsl(*arguments),capture_output=True,text=True,encoding="utf-8",errors="replace")
    commands.append({"arguments":list(arguments),"returncode":result.returncode,"stdout":result.stdout,"stderr":result.stderr})
    (evidence/"audio-compile-log.json").write_text(json.dumps(commands,indent=2),encoding="utf-8")
    result.check_returncode()


execute("dtc","-@","-I","dts","-O","dtb","-o",linux_path(overlay),linux_path(source))
checks=[]
for variant in ("ap6212","aic8800ds2"):
    base=sources/("runtime-rk3566-radxa-zero-3w-"+variant+".dtb")
    merged=evidence/("revb-audio-"+variant+".dtb")
    execute("fdtoverlay","-i",linux_path(base),"-o",linux_path(merged),linux_path(overlay))
    controller=symbol(merged,"i2s3_2ch")
    codec=symbol(merged,"hat_revb_codec")
    bus=symbol(merged,"i2c5")
    cpu=symbol(merged,"hat_revb_cpu")
    clock=symbol(merged,"hat_revb_mclk")
    pin_names=("i2s3m0_sclk","i2s3m0_lrck","i2s3m0_sdi","i2s3m0_sdo")
    expected_pins=[get(merged,symbol(merged,name),"phandle","x")[0] for name in pin_names]
    record={
        "variant":variant,
        "base_sha256":hashlib.sha256(base.read_bytes()).hexdigest(),
        "merged_sha256":hashlib.sha256(merged.read_bytes()).hexdigest(),
        "i2c_hz":get(merged,bus,"clock-frequency","x")[0],
        "codec_address":get(merged,codec,"reg","x")[0],
        "reset_matches":get(merged,codec,"reset-gpios","x")==get(merged,symbol(merged,"gpio3"),"phandle","x")+[19,1],
        "codec_is_clock_master":all(get(merged,"/sound-duck-hat-revb","simple-audio-card,"+name,"x")==get(merged,symbol(merged,"hat_revb_codec_dai"),"phandle","x") for name in ("bitclock-master","frame-master")),
        "codec_clock_hz":get(merged,clock,"clock-frequency","x")[0],
        "four_i2s_pins_only":get(merged,controller,"pinctrl-0","x")==expected_pins,
        "codec_supply_microvolt":get(merged,"/regulator-hat-revb-1v8","regulator-min-microvolt","x")[0],
        "audio_routing":get(merged,"/sound-duck-hat-revb","simple-audio-card,routing"),
    }
    record["accepted_offline"]=all((record["i2c_hz"]==100000,record["codec_address"]==0x18,record["reset_matches"],record["codec_is_clock_master"],record["codec_clock_hz"]==12000000,record["four_i2s_pins_only"],record["codec_supply_microvolt"]==1800000))
    checks.append(record)
result={"revision":"B.0 candidate","overlay_sha256":hashlib.sha256(overlay.read_bytes()).hexdigest(),"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"checks":checks,"accepted_offline":all(record["accepted_offline"] for record in checks),"deployed":False,"hardware_tested":False,"initial_sample_rate_hz":48000,"limits":["No live pinmux conflict check","No ALSA card registration or waveform test","No full devicetree schema validation","Other sample rates have not been accepted"]}
(evidence/"audio-offline-audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
if not result["accepted_offline"]:
    raise RuntimeError("Offline audio checks failed")
