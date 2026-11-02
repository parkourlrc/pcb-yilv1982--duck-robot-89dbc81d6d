"""Compile and merge the audio overlay against both official ZERO 3W base DTBs."""
import hashlib
import json
from pathlib import Path
import subprocess

from build_codec_module import linux_path, run, wsl
from collect_radxa_driver_sources import EVIDENCE, ROOT, SOURCES
from inspect_radxa_runtime_package import KERNEL


def get(dtb, node, property_name, value_type="s"):
    output = subprocess.check_output(wsl("fdtget", "-t", value_type, linux_path(dtb), node, property_name), text=True, encoding="utf-8").strip()
    return [int(value, 16) for value in output.split()] if value_type == "x" else output


def symbol(dtb, name):
    return get(dtb, "/__symbols__", name)


def main():
    directory = ROOT / "hardware/custom_hat/software/codec"
    source = directory / "duck-hat-audio.dts"
    output = directory / KERNEL / "duck-hat-audio.dtbo"
    if not (output.parent / "manifest.json").is_file():
        raise RuntimeError("Build the matching codec module first")
    contract_path = ROOT / "hardware/custom_hat/rev_a/net-contract.json"
    full_contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract = full_contract["codec_hardware_reset"]
    if (contract["header_pin"], contract["bank"], contract["offset"]) != (33, 3, 19):
        raise RuntimeError("GPIO contract changed; update the overlay explicitly")
    header_nets = {str(row["pin"]): row["net"] for row in full_contract["pins"] if row["reference"] == "J101"}
    expected_nets = {"12": "I2S_BCLK", "13": "I2S_MCLK", "35": "I2S_LRCK", "38": "I2S_SDI", "40": "I2S_SDO",
                     "29": "I2C5_SCL", "31": "I2C5_SDA", "33": "CODEC_RST"}
    if any(header_nets.get(pin) != net for pin, net in expected_nets.items()):
        raise RuntimeError("PCB interface pin contract changed")
    run("audio-overlay-compile", wsl("dtc", "-@", "-I", "dts", "-O", "dtb", "-o", linux_path(output), linux_path(source)))
    checks = []
    for variant in ("ap6212", "aic8800ds2"):
        base = SOURCES / ("runtime-rk3566-radxa-zero-3w-" + variant + ".dtb")
        merged = EVIDENCE / ("offline-audio-" + variant + ".dtb")
        run("audio-overlay-merge-" + variant, wsl("fdtoverlay", "-i", linux_path(base), "-o", linux_path(merged), linux_path(output)))
        bus, controller, codec = symbol(merged, "i2c5"), symbol(merged, "i2s3_2ch"), symbol(merged, "hat_codec")
        gpio, supply = symbol(merged, "gpio3"), symbol(merged, "vcc3v3_sys")
        pins = [symbol(merged, name) for name in ("i2s3m0_mclk", "i2s3m0_sclk", "i2s3m0_lrck", "i2s3m0_sdi", "i2s3m0_sdo")]
        pin_values = [get(merged, path, "rockchip,pins", "x")[:3] for path in pins]
        reset_gpio = get(merged, codec, "reset-gpios", "x")
        supply_phandle = get(merged, supply, "phandle", "x")
        core_supply = get(merged, "/regulator-hat-codec-1v8", "phandle", "x")
        reset_group = symbol(merged, "hat_codec_reset")
        i2c_group = symbol(merged, "i2c5m0_xfer")
        i2c_pins = get(merged, i2c_group, "rockchip,pins", "x")
        cpu_node = symbol(merged, "hat_cpu")
        cpu_phandle = get(merged, cpu_node, "phandle", "x")
        controller_pin_phandles = [get(merged, path, "phandle", "x")[0] for path in pins]
        record = {"variant": variant, "base_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
                  "merged_sha256": hashlib.sha256(merged.read_bytes()).hexdigest(), "i2c5_enabled": get(merged, bus, "status") == "okay",
                  "i2s3_enabled": get(merged, controller, "status") == "okay", "i2c_frequency_hz": get(merged, bus, "clock-frequency", "x")[0],
                  "codec_address": get(merged, codec, "reg", "x")[0], "reset_gpio": reset_gpio,
                  "reset_gpio_matches": reset_gpio == get(merged, gpio, "phandle", "x") + [19, 1],
                  "reset_pinmux_matches": get(merged, symbol(merged, "hat_codec_reset"), "rockchip,pins", "x")[:3] == [3, 19, 0],
                  "codec_selects_reset_pinmux": get(merged, codec, "pinctrl-0", "x") == get(merged, reset_group, "phandle", "x"),
                  "i2s_pinmux": pin_values, "i2s_pinmux_matches": pin_values == [[3, 2, 4], [3, 3, 4], [3, 4, 4], [3, 6, 4], [3, 5, 4]],
                  "controller_selects_all_i2s_pins": get(merged, controller, "pinctrl-0", "x") == controller_pin_phandles,
                  "i2c_m0_selected": get(merged, bus, "pinctrl-0", "x") == get(merged, i2c_group, "phandle", "x"),
                  "i2c_pins_match_header": [i2c_pins[index:index+3] for index in range(0, len(i2c_pins), 4)] == [[3, 11, 4], [3, 12, 4]],
                  "three_3v3_supplies_match": all(get(merged, codec, name + "-supply", "x") == supply_phandle for name in ("IOVDD", "AVDD", "DRVDD")),
                  "header_supply_is_3v3": get(merged, supply, "regulator-min-microvolt", "x") == [3300000] and get(merged, supply, "regulator-max-microvolt", "x") == [3300000],
                  "core_1v8_supply_matches": get(merged, codec, "DVDD-supply", "x") == core_supply,
                  "core_microvolt": get(merged, "/regulator-hat-codec-1v8", "regulator-min-microvolt", "x")[0],
                  "core_supply_parent_matches": get(merged, "/regulator-hat-codec-1v8", "vin-supply", "x") == supply_phandle,
                  "cpu_dai_matches": get(merged, cpu_node, "sound-dai", "x") == get(merged, controller, "phandle", "x"),
                  "codec_dai_matches": get(merged, "/sound-duck-hat/simple-audio-card,codec", "sound-dai", "x") == get(merged, codec, "phandle", "x"),
                  "cpu_is_clock_master": all(get(merged, "/sound-duck-hat", "simple-audio-card," + name, "x") == cpu_phandle for name in ("bitclock-master", "frame-master")),
                  "mclk_fs": get(merged, "/sound-duck-hat", "simple-audio-card,mclk-fs", "x")[0]}
        record["accepted"] = all((record["i2c5_enabled"], record["i2s3_enabled"], record["i2c_frequency_hz"] == 100000,
                                  record["codec_address"] == 0x18, record["reset_gpio_matches"], record["reset_pinmux_matches"],
                                  record["i2s_pinmux_matches"], record["three_3v3_supplies_match"], record["core_1v8_supply_matches"],
                                  record["core_microvolt"] == 1800000, record["mclk_fs"] == 256,
                                  record["codec_selects_reset_pinmux"], record["controller_selects_all_i2s_pins"], record["i2c_m0_selected"],
                                  record["i2c_pins_match_header"], record["header_supply_is_3v3"], record["core_supply_parent_matches"],
                                  record["cpu_dai_matches"], record["codec_dai_matches"], record["cpu_is_clock_master"]))
        checks.append(record)
    result = {"kernel": KERNEL, "overlay_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "overlay_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "net_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
              "base_checks": checks, "accepted_offline": all(row["accepted"] for row in checks), "deployed": False, "hardware_tested": False,
              "limits": ["No live pinmux/overlay conflict check", "No binding-schema validation", "No ALSA registration, MCLK waveform, playback or capture test",
                         "J504 Line widget names a DAPM endpoint, not an approval of any external load", "No microphone model or measured bias acceptance"]}
    for path in (EVIDENCE / "audio-overlay-audit.json", output.parent / "overlay-manifest.json"):
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    if not result["accepted_offline"]:
        raise RuntimeError("Offline overlay checks failed")


if __name__ == "__main__":
    main()
