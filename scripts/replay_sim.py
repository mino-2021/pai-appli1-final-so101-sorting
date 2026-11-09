"""収録したエピソードの関節の動きを、MuJoCo の SO-101 モデルで再生する（スポンジ・箱・お椀つき）。

使い方：python scripts/replay_sim.py 25            → so101_sort_2cam_v3 のエピソード 25 を再生
        python scripts/replay_sim.py 25 --speed 0.5  → 0.5 倍速
        python scripts/replay_sim.py 5 --no-objects  → ロボットだけ
        python scripts/replay_sim.py 5 --repo mino/so101_sort_2cam --key action
        python scripts/replay_sim.py 31 --video sim_ep31.mp4  → 画面を出さずに動画（MP4）で保存
        python scripts/replay_sim.py 31 --save-xml sim_ep31.xml → 物体を含めたモデルを XML で保存

モデルは TheRobotStudio/SO-ARM100 の Simulation/SO101/scene.xml（new calib＝各関節の範囲の中央が 0 度）。
LeRobot の SO-101 は度単位（use_degrees=True、範囲の中央が 0 度）なのでラジアンに直すだけで対応する。
グリッパーは LeRobot では 0（閉）〜100（開）なので、モデルの関節範囲に線形で割り当てる。

物理計算はせず、関節角度をそのまま置いて表示する。物体は見せるための近似：
- 机の高さ：データセット全体でグリッパー先端が一番低くなった高さ（モデルと実機の角度のずれで、
  机を z=0 にするとグリッパーがめり込むため。床をその高さまで下げる）
- 箱・お椀の位置：データセット全体で、その色のスポンジを放した瞬間のグリッパー先端の平均位置
- 掴む・放すの判定は、グリッパーの指令値（action）で行う（スポンジを挟むと状態の値は閉じきらないため）
- スポンジ：最後に掴んだ瞬間（最後から2番目の「開く」が終わった時点）の先端の真下に置き、
  掴んでいる間は先端にくっつけて動かし、最後に開いたら真下に落とす

必要なパッケージ（lerobot の venv に入っているもの。動作確認したバージョン）：
  mujoco 3.11.0、imageio 2.37.4＋imageio-ffmpeg 0.6.0（--video で MP4 を保存するときだけ使う）
  モデル：~/work/robo/models/SO-ARM100（TheRobotStudio/SO-ARM100 の Simulation/SO101）
"""

import argparse
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

from lerobot.datasets.lerobot_dataset import LeRobotDataset

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
OPEN = 30  # グリッパーの状態がこれより大きいと「開いている」
SPONGE = [0.035, 0.025, 0.015]  # スポンジの大きさ（半分の長さ、m）：7×5×3cm
BOX = [0.10, 0.075, 0.03]  # 箱の大きさ（半分の長さ、m）：20×15×6cm
BOWL_R, BOWL_H = 0.085, 0.06  # お椀の半径・高さ（m）
COLORS = {"green": [0.2, 0.8, 0.2, 1], "yellow": [1.0, 0.85, 0.1, 1], "white": [0.95, 0.95, 0.95, 1]}

parser = argparse.ArgumentParser()
parser.add_argument("episode", type=int)
parser.add_argument("--repo", default="mino/so101_sort_2cam_v3")
parser.add_argument("--key", default="observation.state", help="observation.state（実際の姿勢）か action（指令値）")
parser.add_argument("--speed", type=float, default=1.0)
parser.add_argument("--no-objects", action="store_true")
parser.add_argument("--model", default=str(Path.home() / "work/robo/models/SO-ARM100/Simulation/SO101/scene.xml"))
parser.add_argument("--video", help="指定すると画面を出さずに、この名前の MP4 に保存して終了")
parser.add_argument("--size", default="1280x720", help="動画の大きさ（幅x高さ）")
parser.add_argument("--camera", default="180,-25,0.7", help="動画の視点：方位角（度）,仰角（度）,距離（m）")
parser.add_argument("--save-xml", help="物体を含めたモデルを、この名前の XML に保存")
args = parser.parse_args()

ds = LeRobotDataset(args.repo)
ep_col = np.array(ds.hf_dataset["episode_index"])
task_col = np.array(ds.hf_dataset["task_index"])
all_values = np.stack([np.asarray(v, dtype=float) for v in ds.hf_dataset[args.key]])
all_grip = np.stack([np.asarray(v, dtype=float) for v in ds.hf_dataset["action"]])[:, 5]
tasks = list(ds.meta.tasks.index)


def color_of(task):
    return next((c for c in COLORS if c in task), "green")


def open_events(grip):
    """グリッパーの指令値が開いている区間の (開始, 終了) フレームの一覧"""
    o = np.r_[0, (grip > OPEN).astype(int), 0]
    d = np.diff(o)
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


values = all_values[ep_col == args.episode]
grip = all_grip[ep_col == args.episode]
task = tasks[int(task_col[ep_col == args.episode][0])]
print(f"episode {args.episode}: {len(values)} フレーム（{len(values) / ds.fps:.1f} 秒）  タスク：{task}")

spec = mujoco.MjSpec.from_file(args.model)
spec.compiler.meshdir = str(Path(args.model).parent / "assets")
WIDTH, HEIGHT = (int(x) for x in args.size.split("x"))
spec.visual.global_.offwidth, spec.visual.global_.offheight = WIDTH, HEIGHT  # 動画用の描画サイズの上限
world = spec.worldbody
VISUAL = dict(contype=0, conaffinity=0)
model = spec.compile()  # 先端位置の計算用（物体なし）
data = mujoco.MjData(model)
qadr = [model.jnt_qposadr[model.joint(name).id] for name in JOINTS]
ranges = np.array([model.jnt_range[model.joint(name).id] for name in JOINTS])


def to_qpos(v):
    q = np.deg2rad(v[:5])
    g = ranges[5, 0] + (ranges[5, 1] - ranges[5, 0]) * np.clip(v[5], 0, 100) / 100
    return np.clip(np.append(q, g), ranges[:, 0], ranges[:, 1])


def tip(v):
    """関節角度 v のときのグリッパー先端の位置と向き（回転行列）"""
    data.qpos[qadr] = to_qpos(v)
    mujoco.mj_forward(model, data)
    s = data.site("gripperframe")
    return s.xpos.copy(), s.xmat.reshape(3, 3).copy()


# 机の高さ：データセット全体で先端が一番低くなった高さ。床をそこまで下げる
table_z = min(tip(v)[0][2] for v in all_values) - 0.003
spec.geom("floor").pos = [0, 0, table_z]

if not args.no_objects:
    # 箱・お椀の位置：色ごとに、放した瞬間（最後に開いた瞬間）の先端の平均位置
    release = {}
    for ep in np.unique(ep_col):
        v = all_values[ep_col == ep]
        ev = open_events(all_grip[ep_col == ep])
        if len(ev) >= 2:
            c = color_of(tasks[int(task_col[ep_col == ep][0])])
            release.setdefault(c, []).append(tip(v[ev[-1][0]])[0][:2])
    centers = {c: np.mean(p, axis=0) for c, p in release.items()}

    if "green" in centers:  # 箱（半透明の白）：底と4枚の壁
        b = world.add_body(name="box", pos=[*centers["green"], table_z])
        rgba = [0.9, 0.9, 0.95, 0.5]
        bx, by, bz = BOX
        b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[bx, by, 0.002], pos=[0, 0, 0.002], rgba=rgba, **VISUAL)
        for sx, sy, px, py in [(bx, 0.002, 0, by), (bx, 0.002, 0, -by), (0.002, by, bx, 0), (0.002, by, -bx, 0)]:
            b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[sx, sy, bz], pos=[px, py, bz], rgba=rgba, **VISUAL)
    if "yellow" in centers:  # お椀（赤）：底の円柱と、外向きに傾けた板 16 枚
        b = world.add_body(name="bowl", pos=[*centers["yellow"], table_z])
        rgba = [0.55, 0.1, 0.05, 1]
        b.add_geom(type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[BOWL_R * 0.55, 0.003], pos=[0, 0, 0.003], rgba=rgba, **VISUAL)
        n, tilt = 16, np.deg2rad(35)
        r_mid = BOWL_R * 0.55 + np.tan(tilt) * BOWL_H / 2
        half_w = np.pi * BOWL_R / n * 1.1
        for k in range(n):
            a = 2 * np.pi * k / n
            quat = np.zeros(4)
            mujoco.mju_euler2Quat(quat, [0, tilt, a], "XYZ")
            b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.002, half_w, BOWL_H / 2 / np.cos(tilt)],
                       pos=[r_mid * np.cos(a), r_mid * np.sin(a), BOWL_H / 2], quat=quat, rgba=rgba, **VISUAL)

    # スポンジ：手で動かす（mocap）物体
    sponge = world.add_body(name="sponge", mocap=True, pos=[0, 0, table_z + SPONGE[2]])
    sponge.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=SPONGE, rgba=COLORS[color_of(task)], **VISUAL)

    model = spec.compile()
    data = mujoco.MjData(model)

    # 最後に掴んだ瞬間と、放した瞬間
    ev = open_events(grip)
    grasp_t = ev[-2][1] if len(ev) >= 2 else None
    release_t = ev[-1][0] if len(ev) >= 2 else None
    if grasp_t is None:
        print("掴んで放す動きが見つからないので、スポンジは動かさない")
        grasp_t = release_t = len(values)
    p, R = tip(values[min(grasp_t, len(values) - 1)])
    start_pos = np.array([p[0], p[1], table_z + SPONGE[2]])
    offset = R.T @ (start_pos - p)  # 先端から見たスポンジの位置（掴んでいる間は一定）
    R_grasp = R
    bottom = table_z + 0.004 + SPONGE[2]  # 入れ物の底に落とす高さ
else:
    model = spec.compile()  # 床の高さの変更を反映
    data = mujoco.MjData(model)


def sponge_pose(i, v, fall_from):
    """i フレーム目のスポンジの位置と向き（回転行列）"""
    if i < grasp_t:
        return start_pos, np.eye(3)
    if i < release_t:
        p, R = tip(v)
        return p + R @ offset, R @ R_grasp.T
    k = min(1.0, (i - release_t) / 8)  # 8 フレームかけて真下に落とし、向きは水平に戻す
    pos, _ = fall_from
    return np.array([pos[0], pos[1], pos[2] + (bottom - pos[2]) * k]), np.eye(3)


def set_frame(i, v, fall_from):
    """i フレーム目の姿勢（とスポンジの位置）をセットする。落とし始めの位置を返す"""
    if not args.no_objects:
        if i == release_t:
            fall_from = sponge_pose(i - 1, v, None)
        pos, rot = sponge_pose(i, v, fall_from)
        data.mocap_pos[0] = pos
        mujoco.mju_mat2Quat(data.mocap_quat[0], rot.flatten())
    data.qpos[qadr] = to_qpos(v)
    mujoco.mj_forward(model, data)
    return fall_from


if args.save_xml:
    Path(args.save_xml).write_text(spec.to_xml())
    print(f"モデルを保存：{args.save_xml}")

if args.video:
    import imageio

    renderer = mujoco.Renderer(model, HEIGHT, WIDTH)
    cam = mujoco.MjvCamera()
    cam.azimuth, cam.elevation, cam.distance = (float(x) for x in args.camera.split(","))
    cam.lookat[:] = [0.2, 0, 0.03]
    fall_from = None
    with imageio.get_writer(args.video, fps=ds.fps * args.speed, codec="libx264", quality=8) as writer:
        for i, v in enumerate(values):
            fall_from = set_frame(i, v, fall_from)
            renderer.update_scene(data, cam)
            writer.append_data(renderer.render())
    print(f"動画を保存：{args.video}")
    raise SystemExit

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        fall_from = None
        for i, v in enumerate(values):
            if not viewer.is_running():
                break
            start = time.time()
            fall_from = set_frame(i, v, fall_from)
            viewer.sync()
            time.sleep(max(0, 1 / (ds.fps * args.speed) - (time.time() - start)))
        time.sleep(1.0)  # 最後の姿勢で 1 秒止めてから繰り返す
