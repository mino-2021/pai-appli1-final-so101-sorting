#!/bin/bash
# 成功率の計測（1試行 = 1エピソード、20回）
# エピソード後はロボットが初期姿勢に戻るので、リセット中（30秒）にスポンジを次の位置へ置く
# →キーは使わない（キーリピート等で2回入力されると次のエピソードが0フレームで終わりエラーになる）
source "$(dirname "$0")/env.sh"
lerobot-rollout \
  --strategy.type=episodic \
  --policy.path=outputs/train/act_green_test/checkpoints/last/pretrained_model \
  --policy.n_action_steps=1 --policy.temporal_ensemble_coeff=0.01 \
  --robot.type=so101_follower --robot.port=$FOLLOWER_PORT --robot.id=$FOLLOWER_ID \
  --robot.max_relative_target=20 --robot.cameras="$CAMERAS" \
  --task="$TASK" \
  --dataset.repo_id=mino/rollout_green_eval --dataset.single_task="$TASK" \
  --dataset.num_episodes=20 --dataset.episode_time_s=30 --dataset.reset_time_s=30 \
  --dataset.push_to_hub=false --display_data=false
