"""Apply the archived typical bias models to the selected local amplifier capacitors."""
import json
from pathlib import Path

import pipeline
from digitize_capacitor_bias import decode_curve


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/amp-decoupling-20261031"
MODELS = EVIDENCE.parent / "capacitor-models-20261031"


def main():
    contract = json.loads((EVIDENCE / "amp-route-contract.json").read_text(encoding="utf-8"))
    profiles = {"C323": {"part": "C1210C226K3RACTU", "nominal_uf": 22, "rated_v": 25},
                "C328": {"part": "C0805C225K5RACTU", "nominal_uf": 2.2, "rated_v": 50}}
    results = {}
    for reference, profile in profiles.items():
        expected = contract["bulk_fields" if reference == "C323" else "bypass_fields"]["MPN"]
        if profile["part"] != expected:
            raise RuntimeError("Capacitor model does not match the candidate MPN")
        profile.update(tolerance=0.10, aging_pct_per_decade=3, voltages=[4.984, 5.119211])
        result = decode_curve(profile["part"], profile)
        result["pdf_sha256"] = pipeline.digest(MODELS / "sources" / (profile["part"] + ".pdf"))
        result["plot_sha256"] = pipeline.digest(MODELS / "sources" / (profile["part"] + "-dc-bias.png"))
        results[reference] = result
    document = {"models": results, "evidence_level": "Manufacturer typical simulations plus labelled sensitivity assumptions; not a guaranteed lower bound",
                "assumptions": "Same prior cases:subtract2percentage points of capacitance retention,multiply0.9 tolerance,0.85 TCC,and3%/decade-hour aging referenced to48h.48h/1y/10y are sensitivity cases,not user-specified service life.",
                "limits": "Combined voltage/temperature/process correlation,frequency/AC-amplitude dependency,closed-loop interaction andactual ripple have not been validated.",
                "selection": "22uF bulk and2.2uF bypass use already documented MPNs; PAM8302A recommends nearby>=10uF bulk and a typical1uF low-ESR bypass,not these exact part numbers.",
                "hardware_measured": False, "production_ready": False}
    pipeline.write_json(EVIDENCE / "capacitor-margin.json", document)
    print(json.dumps({reference: result["points"] for reference, result in results.items()}))


if __name__ == "__main__":
    main()
