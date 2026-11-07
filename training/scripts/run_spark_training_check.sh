#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 3 || "$#" -gt 5 ]]; then
  echo "Usage: $0 NODE_RANK WORKSPACE RUN_NAME [GLOBAL_ENVS=64] [MASTER_PORT=29671]" >&2
  exit 2
fi

check_rank="$1"
check_workspace="$2"
check_run="$3"
check_envs="${4:-64}"
check_port="${5:-29671}"
check_benchmark=/home/yilv/dspark/duck-benchmark-20261106
check_image=nvcr.io/nvidia/pytorch:25.10-py3

[[ "$check_rank" =~ ^[01]$ ]] || { echo "NODE_RANK must be 0 or 1" >&2; exit 2; }
[[ "$check_workspace" == /* ]] || { echo "WORKSPACE must be absolute" >&2; exit 2; }
[[ "$check_run" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo "RUN_NAME must be alphanumeric with dash or underscore" >&2; exit 2; }
[[ "$check_envs" =~ ^[0-9]+$ && "$check_envs" -ge 2 && "$check_envs" -le 4096 && $((check_envs % 2)) -eq 0 ]] || { echo "GLOBAL_ENVS must be even, 2..4096" >&2; exit 2; }
[[ "$check_port" =~ ^[0-9]+$ && "$check_port" -ge 1024 && "$check_port" -le 65535 ]] || { echo "Invalid MASTER_PORT" >&2; exit 2; }
test -f "$check_workspace/project/training/scripts/check_locomotion_training.py"
test -f "$check_benchmark/venv/pyvenv.cfg"
test -L "$check_benchmark/venv/bin/python"
test -f /home/yilv/dspark/train-gx10/env.sh
test ! -e "$check_workspace/checks/$check_run/result.json"
mkdir -p "$check_workspace/checks/$check_run" "$check_workspace/cache"

sudo -n docker run --rm --name "duck-training-check-${check_run}-rank${check_rank}" \
  --gpus all --network host --ipc host --device /dev/infiniband \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  --env-file /home/yilv/dspark/train-gx10/env.sh \
  --env PYTHONPYCACHEPREFIX=/validation/cache/pycache \
  --entrypoint /bench/venv/bin/python \
  -v "${check_benchmark}:/bench:ro" \
  -v "${check_workspace}:/validation" \
  -v "${check_workspace}/cache:/root/.cache" \
  "$check_image" -m torch.distributed.run \
  --nnodes=2 --nproc-per-node=1 --node-rank="$check_rank" \
  --master-addr=192.168.100.10 --master-port="$check_port" \
  /validation/project/training/scripts/check_locomotion_training.py \
  --runtime --num-envs "$check_envs" --updates 2 \
  --output "/validation/checks/$check_run/result.json" \
  > "$check_workspace/checks/$check_run/rank${check_rank}.log" 2>&1
