#!/usr/bin/env bash
set -euo pipefail
python -m venv --system-site-packages /bench/venv
python -c 'import importlib.metadata as metadata; print("torch==" + metadata.version("torch")); print("torchvision==" + metadata.version("torchvision"))' > /bench/base-constraints.txt
/bench/venv/bin/python -m pip install --disable-pip-version-check --no-input \
  --index-url https://mirrors.aliyun.com/pypi/simple --cache-dir /bench/pip-cache --timeout 30 --retries 2 \
  --constraint /bench/base-constraints.txt \
  mjlab==1.3.0 mujoco==3.10.0 mujoco-warp==3.8.1 warp-lang==1.12.0 rsl-rl-lib==5.0.1 tensordict==0.10.0
/bench/venv/bin/python -m pip check
