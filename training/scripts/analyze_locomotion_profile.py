"""分析Chrome trace区间并集，避免将嵌套耗时相加。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path


def merge(intervals):
    output = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if output and start <= output[-1][1]:
            output[-1][1] = max(output[-1][1], end)
        else:
            output.append([start, end])
    return output


def length(intervals):
    return sum(end - start for start, end in merge(intervals))


def overlap(first, second):
    left, right = merge(first), merge(second)
    left_index = right_index = 0
    total = 0.0
    while left_index < len(left) and right_index < len(right):
        total += max(0, min(left[left_index][1], right[right_index][1]) - max(left[left_index][0], right[right_index][0]))
        if left[left_index][1] <= right[right_index][1]:
            left_index += 1
        else:
            right_index += 1
    return total


def analyze(path, root_name):
    with gzip.open(path, "rt", encoding="utf-8") as source:
        document = json.load(source)
    events = [event for event in document["traceEvents"] if event.get("ph") == "X" and event.get("dur", 0) > 0]
    root = next(event for event in events if event.get("name") == root_name)
    start, end = root["ts"], root["ts"] + root["dur"]

    def interval(event):
        return max(start, event["ts"]), min(end, event["ts"] + event["dur"])

    inside = [event for event in events if event["ts"] < end and event["ts"] + event["dur"] > start]
    labels = [event for event in inside if event.get("name", "").startswith("profile/") and event is not root]
    kernels = [event for event in inside if event.get("cat") == "kernel"]
    memory = [event for event in inside if event.get("cat", "").startswith(("gpu_memcpy", "gpu_memset"))]
    api = [event for event in inside if event.get("cat") in ("cuda_runtime", "cuda_driver")]
    sync = [event for event in api if "synchronize" in event["name"].lower()]
    launches = [event for event in api if "launch" in event["name"].lower()]
    gpu_intervals = [interval(event) for event in kernels + memory]
    sync_intervals = [interval(event) for event in sync]
    launch_intervals = [interval(event) for event in launches]
    grouped = defaultdict(list)
    for label in labels:
        grouped[label["name"]].append(label)
    stages = {}
    for name, records in grouped.items():
        inclusive = [interval(event) for event in records]
        child_intervals = []
        for record in records:
            child_intervals.extend(interval(child) for child in labels if child is not record and child.get("tid") == record.get("tid") and record["ts"] <= child["ts"] and child["ts"] + child["dur"] <= record["ts"] + record["dur"])
        stages[name] = {
            "count": len(records), "cpu_inclusive_ms": length(inclusive) / 1000,
            "cpu_exclusive_of_named_children_ms": (length(inclusive) - length(child_intervals)) / 1000,
            "gpu_activity_during_cpu_range_ms": overlap(inclusive, gpu_intervals) / 1000,
            "sync_api_during_cpu_range_ms": overlap(inclusive, sync_intervals) / 1000,
        }
    correlation_stage = {}
    for event in api:
        correlation = event.get("args", {}).get("correlation")
        if correlation is None:
            continue
        containers = [label for label in labels if label.get("tid") == event.get("tid") and label["ts"] <= event["ts"] and event["ts"] + event["dur"] <= label["ts"] + label["dur"]]
        if containers:
            correlation_stage[correlation] = min(containers, key=lambda item: item["dur"])["name"]
    attributed = defaultdict(list)
    for kernel in kernels:
        owner = correlation_stage.get(kernel.get("args", {}).get("correlation"), "unattributed")
        attributed[owner].append(interval(kernel))
    by_kernel = defaultdict(lambda: {"count": 0, "summed_ms": 0.0})
    for kernel in kernels:
        record = by_kernel[kernel["name"]]
        record["count"] += 1
        record["summed_ms"] += (interval(kernel)[1] - interval(kernel)[0]) / 1000
    by_api = defaultdict(lambda: {"count": 0, "summed_ms": 0.0})
    for event in api:
        record = by_api[event["name"]]
        record["count"] += 1
        record["summed_ms"] += (interval(event)[1] - interval(event)[0]) / 1000
    graph_keys = sorted({key for kernel in kernels for key in kernel.get("args", {}) if "graph" in key.lower()})
    graph_kernels = [kernel for kernel in kernels if any(kernel.get("args", {}).get(key) for key in graph_keys)]
    result = {
        "trace": str(path), "root": root_name, "wall_ms": root["dur"] / 1000,
        "categories": dict(Counter(event.get("cat", "") for event in inside)),
        "kernel_count": len(kernels), "memory_event_count": len(memory),
        "gpu_kernel_union_ms": length([interval(event) for event in kernels]) / 1000,
        "gpu_activity_union_ms": length(gpu_intervals) / 1000,
        "gpu_activity_fraction": length(gpu_intervals) / root["dur"],
        "no_captured_gpu_activity_ms": (root["dur"] - length(gpu_intervals)) / 1000,
        "cpu_cuda_api_union_ms": length([interval(event) for event in api]) / 1000,
        "cpu_launch_api_union_ms": length(launch_intervals) / 1000,
        "cpu_sync_api_union_ms": length(sync_intervals) / 1000,
        "sync_overlap_gpu_activity_ms": overlap(sync_intervals, gpu_intervals) / 1000,
        "sync_without_captured_gpu_activity_ms": (length(sync_intervals) - overlap(sync_intervals, gpu_intervals)) / 1000,
        "graph_argument_keys": graph_keys, "graph_kernel_count": len(graph_kernels),
        "graph_launch_api_count": sum("graphlaunch" in event["name"].lower() for event in api),
        "stage_cpu": stages,
        "kernel_union_by_launch_stage_ms": {name: length(records) / 1000 for name, records in attributed.items()},
        "top_kernels": sorted(({"name": name, **values} for name, values in by_kernel.items()), key=lambda item: item["summed_ms"], reverse=True)[:30],
        "cuda_api": sorted(({"name": name, **values} for name, values in by_api.items()), key=lambda item: item["summed_ms"], reverse=True),
        "sample_kernel_arguments": [event.get("args", {}) for event in kernels[:3]],
        "cautions": ["CPU ranges and GPU activity overlap; do not sum them.", "No captured GPU activity is not proven CPU work or whole-device idle.", "Kernel attribution uses CUPTI correlation to deepest named CPU launch scope; unattributed is explicit.", "Profiler can perturb scheduling; compare unprofiled probes.", "Stage GPU activity during CPU ranges is temporal overlap, not causal attribution."],
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = {"sampling": analyze(arguments.trace_dir / "sampling.json.gz", "profile/sampling_window"),
              "returns": analyze(arguments.trace_dir / "returns.json.gz", "profile/returns_window")}
    arguments.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, record in result.items():
        print(name, record["wall_ms"], record["gpu_activity_fraction"], record["kernel_count"], record["graph_kernel_count"])


if __name__ == "__main__":
    main()
