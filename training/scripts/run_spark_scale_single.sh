#!/usr/bin/env bash
set -euo pipefail
benchmark_root=/home/yilv/dspark/duck-benchmark-20261106
for benchmark_size in 1024 4096; do
  sudo -n docker run --rm --name "duck-benchmark-scale-single-env-${benchmark_size}" \
    --gpus all --network host --ipc host --device /dev/infiniband \
    --ulimit memlock=-1 --ulimit stack=67108864 \
    --env-file /home/yilv/dspark/train-gx10/env.sh \
    --entrypoint /bench/venv/bin/python \
    -v "${benchmark_root}:/bench" -v "${benchmark_root}/cache:/root/.cache" \
    nvcr.io/nvidia/pytorch:25.10-py3 \
    /bench/project/training/scripts/benchmark_locomotion.py \
    --global-envs "$benchmark_size" --warmup 2 --iterations 5 \
    --output "/bench/benchmark-scale-single-env-${benchmark_size}.json" \
    --label "spark-single-env-scale${benchmark_size}" \
    > "${benchmark_root}/scale-single-env-${benchmark_size}.log" 2>&1
done
