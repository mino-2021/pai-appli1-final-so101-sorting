#!/bin/bash
# 2台構成（前方＋手首）の仕分けデータで学習
# v2：データを色ごと20回（計40回）に増やして再学習。v1（act_sort_2cam、batch 16・20000ステップ）は残す
# 5000ステップごとに保存し、途中のモデルも実機で比べられるようにする
# W&B には loss などの数値だけを記録（モデルはアップロードしない）。事前に wandb login が必要
lerobot-train \
  --dataset.repo_id=mino/so101_sort_2cam --batch_size=24 \
  --policy.type=act --policy.device=cuda --policy.push_to_hub=false \
  --output_dir=outputs/train/act_sort_2cam_v2 --job_name=act_sort_2cam_v2 \
  --wandb.enable=true --wandb.project=so101_sort --wandb.disable_artifact=true \
  --steps=30000 --save_freq=5000
