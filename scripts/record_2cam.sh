#!/bin/bash
# 2台構成（前方＋手首）で仕分けタスクを収録。指定した回数ずつ、同じデータセットに追加
# v3：緑スポンジ→箱、黄スポンジ→赤いお椀（白→箱の横は v2 の so101_sort_2cam に残す）
# 使い方：scripts/record_2cam.sh green 20 → scripts/record_2cam.sh yellow 20
# 途中で止まったときは残りの回数を2つ目に指定（例：scripts/record_2cam.sh green 7）
# 1回目はデータセットを作成、2回目以降は --resume=true で追記（日時は付けない）
# 別のデータセットに撮るときは REPO_ID=mino/xxx scripts/record_2cam.sh green
source "$(dirname "$0")/env_2cam.sh"
case "$1" in
  green) TASK="Put the green sponge in the box" ;;
  yellow) TASK="Put the yellow sponge in the red bowl" ;;
  white) TASK="Put the white sponge beside the box" ;;
  *) echo "usage: $0 green|yellow|white [回数]"; exit 1 ;;
esac
NUM_EPISODES=${2:-10}
REPO_ID=${REPO_ID:-mino/so101_sort_2cam_v3}
# resume には保存先の明示が必要（LeRobot の仕様）。既定と同じ場所を指定する
DATASET_ROOT=$HOME/.cache/huggingface/lerobot/$REPO_ID
RESUME=false
[ -d "$DATASET_ROOT" ] && RESUME=true
command -v lerobot-record >/dev/null || { echo "lerobot-record が見つからない。先に source ~/work/robo/lerobot/.venv/bin/activate"; exit 1; }
# lerobot-record と同じ venv の python で、録画中／リセット中を表示するラッパー経由で実行（音声なし）
"$(dirname "$(command -v lerobot-record)")/python" "$(dirname "$0")/run_with_status.py" record \
  --play_sounds=false \
  --robot.type=so101_follower --robot.port=$FOLLOWER_PORT --robot.id=$FOLLOWER_ID \
  --robot.max_relative_target=20 --robot.cameras="$CAMERAS" \
  --teleop.type=so101_leader --teleop.port=$LEADER_PORT --teleop.id=$LEADER_ID \
  --display_data=true \
  --dataset.repo_id=$REPO_ID --dataset.no_stamp=true --dataset.root=$DATASET_ROOT --resume=$RESUME \
  --dataset.num_episodes=$NUM_EPISODES --dataset.single_task="$TASK" \
  --dataset.episode_time_s=40 --dataset.reset_time_s=600 \
  --dataset.push_to_hub=false
