#!/bin/bash
source "$(dirname "$0")/env.sh"
lerobot-rollout \
  --strategy.type=episodic \
  --policy.path=outputs/train/act_green_test/checkpoints/last/pretrained_model \
  --robot.type=so101_follower --robot.port=$FOLLOWER_PORT --robot.id=$FOLLOWER_ID \
  --robot.max_relative_target=20 --robot.cameras="$CAMERAS" \
  --task="$TASK" --duration=40 \
  --dataset.repo_id=mino/rollout_green_test --dataset.single_task="$TASK" \
  --dataset.push_to_hub=false --display_data=true
