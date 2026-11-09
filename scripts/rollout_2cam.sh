#!/bin/bash
# 2台構成（前方＋手首）の仕分けモデルで推論・成功率の計測（1試行 = 1エピソード）
# 使い方：scripts/rollout_2cam.sh green|white [回数] [チェックポイント]（既定 10回、last）
#   例：scripts/rollout_2cam.sh yellow 3 005000 → act_sort_2cam_v3_trim の 5000 ステップ目のモデル
#   別のモデルを使うときは MODEL=act_sort_2cam_v2 scripts/rollout_2cam.sh white 3
# モデルは「実行した場所」の outputs/train/<MODEL> から探す。学習を実行した場所と同じ場所で実行する
#   v1・v2：~/work/robo/lerobot で学習　v3：このリポジトリ（pai-appli1-final-so101-sorting）で学習
# 学習中でも実行できる（推論は約20msで、1コマ33msに収まることを確認済み）
# エピソード後はロボットが初期姿勢に戻るので、リセット中（30秒）にスポンジを次の位置へ置く
# →キーは使わない（キーリピート等で2回入力されると次のエピソードが0フレームで終わりエラーになる）
# ACT はタスク文を使わないので、色の指定は保存されるデータのラベルとデータセット名にだけ反映される
source "$(dirname "$0")/env_2cam.sh"
case "$1" in
  green) TASK="Put the green sponge in the box" ;;
  yellow) TASK="Put the yellow sponge in the red bowl" ;;
  white) TASK="Put the white sponge beside the box" ;;
  *) echo "usage: $0 green|yellow|white [回数] [チェックポイント]"; exit 1 ;;
esac
NUM_EPISODES=${2:-10}
MODEL=${MODEL:-act_sort_2cam_v3_trim}
CKPT=${3:-last}
POLICY_PATH=outputs/train/$MODEL/checkpoints/$CKPT/pretrained_model
[ -d "$POLICY_PATH" ] || { echo "モデルが見つからない: $POLICY_PATH"; ls -d outputs/train/$MODEL/checkpoints/*/ 2>/dev/null; exit 1; }
command -v lerobot-rollout >/dev/null || { echo "lerobot-rollout が見つからない。先に source ~/work/robo/lerobot/.venv/bin/activate"; exit 1; }
# lerobot-rollout と同じ venv の python で、録画中／リセット中を表示するラッパー経由で実行（音声なし）
"$(dirname "$(command -v lerobot-rollout)")/python" "$(dirname "$0")/run_with_status.py" rollout \
  --play_sounds=false \
  --strategy.type=episodic \
  --policy.path=$POLICY_PATH \
  --policy.n_action_steps=1 --policy.temporal_ensemble_coeff=0.01 \
  --robot.type=so101_follower --robot.port=$FOLLOWER_PORT --robot.id=$FOLLOWER_ID \
  --robot.max_relative_target=20 --robot.cameras="$CAMERAS" \
  --task="$TASK" \
  --dataset.repo_id=mino/rollout_${MODEL#act_}_$1_$CKPT --dataset.single_task="$TASK" \
  --dataset.num_episodes=$NUM_EPISODES --dataset.episode_time_s=30 --dataset.reset_time_s=30 \
  --dataset.push_to_hub=false --display_data=false
