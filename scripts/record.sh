#!/bin/bash
source "$(dirname "$0")/env.sh"
lerobot-record \
  --robot.type=so101_follower --robot.port=$FOLLOWER_PORT --robot.id=$FOLLOWER_ID \
  --robot.max_relative_target=20 --robot.cameras="$CAMERAS" \
  --teleop.type=so101_leader --teleop.port=$LEADER_PORT --teleop.id=$LEADER_ID \
  --display_data=true \
  --dataset.repo_id=mino/so101_green \
  --dataset.num_episodes=10 --dataset.single_task="$TASK" \
  --dataset.episode_time_s=40 --dataset.reset_time_s=600 \
  --dataset.push_to_hub=false
