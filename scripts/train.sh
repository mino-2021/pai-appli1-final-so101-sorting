#!/bin/bash
lerobot-train \
  --dataset.repo_id=mino/so101_green_test_20261026_001122 \
  --policy.type=act --policy.device=cuda --policy.push_to_hub=false \
  --output_dir=outputs/train/act_green_test --job_name=act_green_test \
  --wandb.enable=false --steps=20000
