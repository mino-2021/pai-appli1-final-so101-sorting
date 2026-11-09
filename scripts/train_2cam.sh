#!/bin/bash
# 2台構成（前方＋手首）の仕分けデータで学習
# v3：緑→箱、黄→赤いお椀のデータで学習。設定は v2 と同じ
# v3_trim：冒頭の止まっている区間を切ったデータ（scripts/trim_idle_start.py で作成）で学習し直す
#   act_sort_2cam_v3（切る前のデータ）は初期姿勢のまま動き出さなかったので、比較用に残す
# v1（act_sort_2cam）と v2（act_sort_2cam_v2、白→箱の横、batch 24・30000ステップ）は残す
# 5000ステップごとに保存し、途中のモデルも実機で比べられるようにする
# W&B には loss などの数値だけを記録（モデルはアップロードしない）。事前に wandb login が必要
# 保存先は「実行した場所」の outputs/train/act_sort_2cam_v3_trim（rollout_2cam.sh も同じ場所で実行する）
lerobot-train \
  --dataset.repo_id=mino/so101_sort_2cam_v3_trim --batch_size=24 \
  --policy.type=act --policy.device=cuda --policy.push_to_hub=false \
  --output_dir=outputs/train/act_sort_2cam_v3_trim --job_name=act_sort_2cam_v3_trim \
  --wandb.enable=true --wandb.project=so101_sort --wandb.disable_artifact=true \
  --steps=30000 --save_freq=5000
