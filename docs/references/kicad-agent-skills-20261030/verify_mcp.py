import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pcbnew


async def main():
    record_dir = Path(__file__).resolve().parent
    root = record_dir.parents[2]
    source = root / "hardware/custom_hat/rev_a"
    ki_bin = Path(os.environ["KICAD_PYTHON"]).parent
    original = source / "custom_hat_rev_a.kicad_pcb"
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    result = {"kicad_version": pcbnew.GetBuildVersion(), "source_sha256": before}
    with tempfile.TemporaryDirectory(prefix="kicad-mcp-check-") as temporary:
        copy_dir = Path(temporary) / "rev_a"
        copy_dir.mkdir()
        for source_file in source.iterdir():
            if source_file.is_file() and source_file.suffix in {".kicad_sch", ".kicad_pcb", ".kicad_pro", ".kicad_dru"}:
                shutil.copy2(source_file, copy_dir / source_file.name)
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "kicad_mcp_server"],
            env={**os.environ, "KICAD_CLI": str(ki_bin / "kicad-cli.exe"), "PYTHONUTF8": "1"},
        )
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                initialization = await session.initialize()
                result["server"] = initialization.serverInfo.model_dump()
                tools = await session.list_tools()
                result["tools"] = [tool.name for tool in tools.tools]
                result["calls"] = {}
                for name, filename in [
                    ("get_pcb_statistics", "custom_hat_rev_a.kicad_pcb"),
                    ("list_schematic_components", "power.kicad_sch"),
                ]:
                    response = await session.call_tool(name, {"file_path": str(copy_dir / filename)})
                    output = "\n".join(getattr(block, "text", "") for block in response.content)
                    result["calls"][name] = {"is_error": bool(response.isError), "text": output}
                    if response.isError or output.startswith("Error"):
                        raise RuntimeError(output)
    result["source_unchanged"] = before == hashlib.sha256(original.read_bytes()).hexdigest()
    (record_dir / "mcp-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"tools": len(result["tools"]), "source_unchanged": result["source_unchanged"], "kicad": result["kicad_version"]}))


asyncio.run(asyncio.wait_for(main(), timeout=60))
