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
source=directory/"duck-hat-revb-ttl.dts"
overlay=directory/"duck-hat-revb-ttl.dtbo"
config=Path.home()/"AppData/Local/duck-robot-tools/radxa-kernel/6.1.84-10/headers/.config"
config_text=config.read_text(encoding="utf-8")
required=("CONFIG_ARCH_ROCKCHIP=y","CONFIG_NO_GKI=y","CONFIG_SERIAL_8250_DW=y","CONFIG_SERIAL_MCTRL_GPIO=y")
if any(value not in config_text.splitlines() for value in required):
    raise RuntimeError("Archived kernel does not support the reviewed GPIO direction implementation")
commands=[]


def execute(*arguments):
    result=subprocess.run(wsl(*arguments),capture_output=True,text=True,encoding="utf-8",errors="replace")
    commands.append({"arguments":list(arguments),"returncode":result.returncode,"stdout":result.stdout,"stderr":result.stderr})
    (evidence/"ttl-compile-log.json").write_text(json.dumps(commands,indent=2),encoding="utf-8")
    result.check_returncode()


execute("dtc","-@","-I","dts","-O","dtb","-o",linux_path(overlay),linux_path(source))
checks=[]
for variant in ("ap6212","aic8800ds2"):
    base=sources/("runtime-rk3566-radxa-zero-3w-"+variant+".dtb")
    merged=evidence/("revb-combined-"+variant+".dtb")
    execute("fdtoverlay","-i",linux_path(base),"-o",linux_path(merged),linux_path(directory/"duck-hat-revb-audio.dtbo"),linux_path(overlay))
    uart=symbol(merged,"uart2")
    gpio=symbol(merged,"gpio3")
    direction=symbol(merged,"hat_revb_dir")
    uart_pins=symbol(merged,"uart2m0_xfer")
    record={"variant":variant,"uart":uart,"enabled":get(merged,uart,"status")=="okay","de_gpio":get(merged,uart,"rs485-de-gpios","x"),"de_gpio_matches":get(merged,uart,"rs485-de-gpios","x")==get(merged,gpio,"phandle","x")+[1,0],"gpio3_a1":get(merged,direction,"rockchip,pins","x")[:3]==[3,1,0],"pinmux_matches":get(merged,uart,"pinctrl-0","x")==get(merged,uart_pins,"phandle","x")+get(merged,direction,"phandle","x"),"uart_pins":get(merged,uart_pins,"rockchip,pins","x"),"rts_delay":get(merged,uart,"rs485-rts-delay","x"),"merged_sha256":hashlib.sha256(merged.read_bytes()).hexdigest()}
    record["accepted_offline"]=all((record["enabled"],record["de_gpio_matches"],record["gpio3_a1"],record["pinmux_matches"],record["rts_delay"]==[0,0]))
    checks.append(record)
manifest={"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"overlay_sha256":hashlib.sha256(overlay.read_bytes()).hexdigest(),"kernel_config_sha256":hashlib.sha256(config.read_bytes()).hexdigest(),"kernel_source_commit":"e6d12a77c8bc0ea6decbd3e4604ec131d4032c30","required_config":required,"checks":checks,"accepted_offline":all(row["accepted_offline"] for row in checks),"driver_specific_polarity":{"rs485_rts_active_low":True,"gpio_active_low":False,"SER_RS485_RTS_ON_SEND":False,"SER_RS485_RTS_AFTER_SEND":True,"physical_tx_dir":1,"physical_rx_dir":0},"deployed":False,"hardware_validated":False,"limits":["Specific to archived Radxa vendor kernel polarity; not generic upstream Linux","Target kernel/boot console/DMA and actual pinmux must match","No serial traffic or robot motion performed"]}
(evidence/"ttl-offline-audit.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(manifest,ensure_ascii=False))
