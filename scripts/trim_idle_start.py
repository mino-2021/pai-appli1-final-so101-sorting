"""各エピソードの冒頭で腕が止まっている区間を切り落とした、新しいデータセットを作る。

冒頭の「初期姿勢のまま動かない」フレームが多いと、ACT が初期姿勢のまま動き出さなくなるための対策。
元のデータセットは変更しない。動き出す少し前（MARGIN フレーム）から残す。

使い方：python scripts/trim_idle_start.py mino/so101_sort_2cam_v3 mino/so101_sort_2cam_v3_trim
"""

import sys

import numpy as np
import torch

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.utils.constants import DEFAULT_FEATURES

THRESHOLD = 3.0  # 指令値（action）のどれかの関節が開始時から 3 度以上変わったら「動き出し」
MARGIN = 5  # 動き出しの 5 フレーム前から残す

src_id, dst_id = sys.argv[1], sys.argv[2]
src = LeRobotDataset(src_id)
features = {
    k: {kk: vv for kk, vv in v.items() if kk != "info"}
    for k, v in src.meta.features.items()
    if k not in DEFAULT_FEATURES
}
dst = LeRobotDataset.create(dst_id, fps=src.fps, features=features, robot_type=src.meta.robot_type)
camera_keys = src.meta.camera_keys

ep_col = np.array(src.hf_dataset["episode_index"])
total_before = total_after = 0
for ep in range(src.meta.total_episodes):
    idx = np.where(ep_col == ep)[0]
    actions = np.stack([src.hf_dataset[int(i)]["action"].numpy() for i in idx])
    moved = np.where(np.abs(actions[:, :5] - actions[0, :5]).max(axis=1) > THRESHOLD)[0]
    start = max(0, int(moved[0]) - MARGIN) if len(moved) else 0
    for i in idx[start:]:
        f = src[int(i)]
        frame = {"task": f["task"]}
        for k in features:
            v = f[k]
            if k in camera_keys:  # CHW の float(0〜1) → HWC の uint8
                v = (v.permute(1, 2, 0).clamp(0, 1) * 255).round().to(torch.uint8)
            frame[k] = v
        dst.add_frame(frame)
    dst.save_episode()
    total_before += len(idx)
    total_after += len(idx) - start
    print(f"episode {ep}: {len(idx)} → {len(idx) - start} フレーム（冒頭 {start} を削除）", flush=True)

dst.finalize()
print(f"合計 {total_before} → {total_after} フレーム")
