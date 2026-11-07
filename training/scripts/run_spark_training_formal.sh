#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 2 ]]; then
  echo "Usage: $0 NODE_RANK WORKSPACE" >&2
  exit 2
fi

formal_rank="$1"
formal_workspace="$2"
formal_benchmark=/home/yilv/dspark/duck-benchmark-20261106
formal_image=nvcr.io/nvidia/pytorch:25.10-py3

[[ "$formal_rank" =~ ^[01]$ ]] || { echo "NODE_RANK must be 0 or 1" >&2; exit 2; }
[[ "$formal_workspace" == /* ]] || { echo "WORKSPACE must be absolute" >&2; exit 2; }
test -f "$formal_workspace/project/training/mjlab_duck/train_locomotion.py"
test -f "$formal_benchmark/venv/pyvenv.cfg"
test -L "$formal_benchmark/venv/bin/python"
test -f /home/yilv/dspark/train-gx10/env.sh
test ! -e "$formal_workspace/runs/run-001"
test ! -e "$formal_workspace/experiments/locomotion-v1"
mkdir -p "$formal_workspace/cache" "$formal_workspace/runs" "$formal_workspace/experiments"

sudo -n docker run -d --name "duck-training-formal-20261106-rank${formal_rank}" \
  --gpus all --network host --ipc host --device /dev/infiniband \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  --env-file /home/yilv/dspark/train-gx10/env.sh \
  --env PYTHONPYCACHEPREFIX=/work/cache/pycache \
  --workdir /work/project/training \
  --entrypoint /bench/venv/bin/python \
  -v "${formal_benchmark}:/bench:ro" \
  -v "${formal_workspace}:/work" \
  -v "${formal_workspace}/cache:/root/.cache" \
  "$formal_image" -m torch.distributed.run \
  --nnodes=2 --nproc-per-node=1 --node-rank="$formal_rank" \
  --master-addr=192.168.100.10 --master-port=29681 \
  -m mjlab_duck.train_locomotion \
  --output /work/runs/run-001 \
  --experiment-dir /work/experiments/locomotion-v1
