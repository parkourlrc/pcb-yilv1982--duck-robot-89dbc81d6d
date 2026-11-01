"""SDS814X HD 的只查询诊断：不发 RUN/STOP/RESET 或采集设置指令。"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time

import pyvisa
from pyvisa.rname import ResourceName


SERIAL = "SDS08A0QA12396"
IDENTITY = "*IDN?"
# 来源：SDS800XHD_Series_ProgrammingGuide_EN11G，印刷 p38/40/42/46/51/53/56–60。
STATE_QUERIES = [
    ":ACQuire:MMANagement?",
    ":ACQuire:MDEPth?",
    ":ACQuire:POINts?",
    ":ACQuire:SRATe?",
] + [
    f":CHANnel{channel}:{field}?"
    for channel in range(1, 5)
    for field in ["SWITch", "PROBe", "SCALe", "OFFSet", "COUPling", "INVert"]
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--state", action="store_true", help="附加只读采集参数查询")
    args = parser.parse_args()
    # 使用新文件保留每次证据，不能无提示覆盖上次结果。
    with args.output.open("x", encoding="utf-8") as log:
        record = {
            "started_at": datetime.now().astimezone().isoformat(),
            "purpose": "identity and optional state queries only",
            "pyvisa_version": pyvisa.__version__,
            "queries": [],
            "success": False,
        }
        manager = None
        instrument = None
        try:
            manager = pyvisa.ResourceManager()
            record["visa_library"] = str(manager.visalib)
            candidates = []
            for resource in manager.list_resources("USB?*::INSTR"):
                parsed = ResourceName.from_string(resource)
                if (
                    int(parsed.manufacturer_id, 0) == 0xF4EC
                    and int(parsed.model_code, 0) == 0x1017
                    and parsed.serial_number == SERIAL
                ):
                    candidates.append(resource)
            record["matching_resources"] = candidates
            if len(candidates) != 1:
                raise RuntimeError(f"Expected one target instrument; found {len(candidates)}")
            instrument = manager.open_resource(candidates[0])
            # 本地传输设置，不更改仪器通道、触发或采集状态。
            instrument.timeout = 3000
            instrument.read_termination = "\n"
            instrument.write_termination = "\n"
            commands = [IDENTITY] + (STATE_QUERIES if args.state else [])
            for command in commands:
                start = time.perf_counter()
                item = {"query": command}
                record["queries"].append(item)
                response = instrument.query(command).strip()
                item.update(response=response, elapsed_ms=1000 * (time.perf_counter() - start))
                print(f"{command} -> {response}", flush=True)
                if command == IDENTITY:
                    fields = [part.strip() for part in response.split(",")]
                    if len(fields) < 4 or fields[1].replace(" ", "").upper() != "SDS814XHD" or fields[2] != SERIAL:
                        raise RuntimeError("Identity response does not match the expected instrument")
            record["success"] = True
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            print(record["error"], file=sys.stderr)
        finally:
            if instrument is not None:
                instrument.close()
            if manager is not None:
                manager.close()
            record["finished_at"] = datetime.now().astimezone().isoformat()
            json.dump(record, log, ensure_ascii=False, indent=2)
            log.write("\n")
        return 0 if record["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
