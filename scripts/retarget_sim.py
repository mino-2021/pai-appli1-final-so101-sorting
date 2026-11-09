"""SO-101 で収録したエピソードを、別のロボット（COBOTTA）の動きに移し替えて MuJoCo で再生する。

使い方：python scripts/retarget_sim.py 31                      → エピソード 31 を COBOTTA で再生
        python scripts/retarget_sim.py 31 --robot ur5e         → UR5e で再生（ほかに mycobot）
        python scripts/retarget_sim.py 5 --video outputs/sim/cobotta_ep5.mp4  → 動画で保存
        python scripts/retarget_sim.py 5 --scale 1.2 --offset 0.05,0,0       → 置き場所の調整

replay_sim.py（関節角度をそのまま SO-101 に入れる）と違い、関節の数や長さが違うロボットのため
「グリッパー先端の通り道」を移し替える（リターゲット）：
1. SO-101 のモデルで、各フレームの先端の位置と向きを計算する
2. 位置を移し替え先の作業範囲に置き直す（机の高さを 0 にして --scale 倍し、--offset だけずらす）
3. 移し替え先の先端（手先に付けた仮の指の先）がその位置・向きに来る関節角度を逆運動学（IK）で求める
   （MuJoCo のヤコビアンを使った減衰最小二乗法。前のフレームの答えから始める）
向きは SO-101 の先端の x 軸（指の向き）を手先の z 軸に、y 軸（指が開く向き）を手先の y 軸に合わせる。
どのモデルにもハンドが無いので、手先に仮の指（2 本の板）を付け、グリッパーの値で開閉させる。
スポンジ・箱・お椀の考え方は replay_sim.py と同じ（見せるための近似で、物理計算はしない）。
移し替えた動きは見せるためのもので、移し替え先のロボットの学習データには使えない（カメラ映像は SO-101 のまま）。

必要なパッケージ：mujoco 3.11.0、imageio 2.37.4＋imageio-ffmpeg 0.6.0（--video のときだけ）
モデル：~/work/robo/models/SO-ARM100（SO-101）
  COBOTTA：~/work/robo/models/mujoco_converted/cobotta
  myCobot 280 M5（アームのみ）：~/work/robo/models/mujoco_converted/mycobot_280_m5
    （この 2 つは scripts/urdf_to_mujoco.py で awesome-robot-arm-zoo の URDF から変換したもの）
  UR5e：~/work/robo/models/mujoco_menagerie/universal_robots_ur5e（そのまま）
"""

import argparse
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

from lerobot.datasets.lerobot_dataset import LeRobotDataset

MODELS = Path.home() / "work/robo/models"
SO101_XML = MODELS / "SO-ARM100/Simulation/SO101/scene.xml"
SO101_JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
# 移し替え先のロボット：
#   xml：モデル、hand_body：手先のボディ、hand_pos/hand_quat：そのボディから見たハンドの取り付け位置・向き
#   （ハンドの z 軸が指の向きになるように）、finger_len：取り付け位置から指先までの長さ（m）、
#   home：IK の初期姿勢、scale/offset：置き直しの既定値（ロボットの大きさに合わせる）
#   rot_weight：IK で向きをどれだけ重視するか（届く範囲が狭いロボットは小さくして位置を優先する）
#   camera：動画の視点の既定値（方位角,仰角,距離）
ROBOTS = {
    "cobotta": dict(
        xml=MODELS / "mujoco_converted/cobotta/scene.xml",
        hand_body="J6", hand_pos=[0, 0, 0], hand_quat=[1, 0, 0, 0],
        finger_len=0.09,
        home=[0.0, 0.3, 1.6, 0.0, 1.2, 0.0],
        scale=1.0, offset=[0.05, 0, 0], rot_weight=0.3, camera="180,-25,1.0",
    ),
    "ur5e": dict(  # menagerie の attachment_site（工具の取り付け面）と同じ位置・向き
        xml=MODELS / "mujoco_menagerie/universal_robots_ur5e/scene.xml",
        hand_body="wrist_3_link", hand_pos=[0, 0.1, 0], hand_quat=[-1, 1, 0, 0],
        finger_len=0.15,
        home=[-1.5708, -1.5708, 1.5708, -1.5708, -1.5708, 0.0],
        scale=2.0, offset=[0.15, 0, 0], rot_weight=0.3, camera="180,-25,2.0",
    ),
    "mycobot": dict(
        xml=MODELS / "mujoco_converted/mycobot_280_m5/scene.xml",
        hand_body="joint6_flange", hand_pos=[0, 0, 0], hand_quat=[1, 0, 0, 0],
        finger_len=0.05,
        home=[0.0, -0.5, -1.2, -0.3, 0.0, 0.0],
        scale=0.9, offset=[0.05, 0, 0], rot_weight=0.1, camera="180,-25,0.7",  # 届く範囲が約 0.28 m と狭いので少し縮める
    ),
}
OPEN = 30  # グリッパーの指令値がこれより大きいと「開いている」
SPONGE = np.array([0.035, 0.025, 0.015])  # スポンジの大きさ（半分の長さ、m）：7×5×3cm
BOX = np.array([0.10, 0.075, 0.03])  # 箱の大きさ（半分の長さ、m）：20×15×6cm
BOWL_R, BOWL_H = 0.085, 0.06  # お椀の半径・高さ（m）
COLORS = {"green": [0.2, 0.8, 0.2, 1], "yellow": [1.0, 0.85, 0.1, 1], "white": [0.95, 0.95, 0.95, 1]}
VISUAL = dict(contype=0, conaffinity=0)

parser = argparse.ArgumentParser()
parser.add_argument("episode", type=int)
parser.add_argument("--robot", default="cobotta", choices=list(ROBOTS))
parser.add_argument("--repo", default="mino/so101_sort_2cam_v3")
parser.add_argument("--scale", type=float, help="SO-101 の先端の位置を何倍に広げるか（既定はロボットごと）")
parser.add_argument("--offset", help="置き直した位置をずらす量（x,y,z、m。既定はロボットごと）")
parser.add_argument("--speed", type=float, default=1.0)
parser.add_argument("--video", help="指定すると画面を出さずに、この名前の MP4 に保存して終了")
parser.add_argument("--size", default="1280x720", help="動画の大きさ（幅x高さ）")
parser.add_argument("--camera", help="動画の視点：方位角（度）,仰角（度）,距離（m）（既定はロボットごと）")
args = parser.parse_args()
robot = ROBOTS[args.robot]
scale = args.scale if args.scale is not None else robot["scale"]
offset = np.array([float(x) for x in args.offset.split(",")]) if args.offset else np.array(robot["offset"], float)

# ---- データの読み込み ----
ds = LeRobotDataset(args.repo)
ep_col = np.array(ds.hf_dataset["episode_index"])
task_col = np.array(ds.hf_dataset["task_index"])
all_state = np.stack([np.asarray(v, dtype=float) for v in ds.hf_dataset["observation.state"]])
all_grip = np.stack([np.asarray(v, dtype=float) for v in ds.hf_dataset["action"]])[:, 5]
tasks = list(ds.meta.tasks.index)
state, grip = all_state[ep_col == args.episode], all_grip[ep_col == args.episode]
task = tasks[int(task_col[ep_col == args.episode][0])]
print(f"episode {args.episode}: {len(state)} フレーム（{len(state) / ds.fps:.1f} 秒）  タスク：{task}")


def color_of(task):
    return next((c for c in COLORS if c in task), "green")


def open_events(g):
    """グリッパーの指令値が開いている区間の (開始, 終了) フレームの一覧"""
    o = np.r_[0, (g > OPEN).astype(int), 0]
    d = np.diff(o)
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


# ---- SO-101 の先端の位置と向き（順運動学） ----
so_model = mujoco.MjModel.from_xml_path(str(SO101_XML))
so_data = mujoco.MjData(so_model)
so_qadr = [so_model.jnt_qposadr[so_model.joint(n).id] for n in SO101_JOINTS[:5]]


def so_tip(v):
    so_data.qpos[so_qadr] = np.deg2rad(v[:5])
    mujoco.mj_forward(so_model, so_data)
    s = so_data.site("gripperframe")
    return s.xpos.copy(), s.xmat.reshape(3, 3).copy()


so_table_z = min(so_tip(v)[0][2] for v in all_state) - 0.003  # replay_sim.py と同じ机の高さ


def place(p):
    """SO-101 の座標を、移し替え先の座標に置き直す（机の高さを 0 にして拡大・移動）"""
    return (p - [0, 0, so_table_z]) * scale + offset


def target_rot(R_so):
    """SO-101 の先端の向き → 手先の目標の向き（z＝指の向き、y＝指が開く向き）"""
    z, y = R_so[:, 0], R_so[:, 1]
    x = np.cross(y, z)
    return np.column_stack([x, y, z])


# 箱・お椀の位置：色ごとに、放した瞬間の先端の平均位置（replay_sim.py と同じ考え方）
release = {}
for ep in np.unique(ep_col):
    ev = open_events(all_grip[ep_col == ep])
    if len(ev) >= 2:
        c = color_of(tasks[int(task_col[ep_col == ep][0])])
        release.setdefault(c, []).append(place(so_tip(all_state[ep_col == ep][ev[-1][0]])[0])[:2])
centers = {c: np.mean(p, axis=0) for c, p in release.items()}
targets = [(place(p), target_rot(R)) for p, R in (so_tip(v) for v in state)]

# ---- 移し替え先のモデル：仮の指・箱・お椀・スポンジを追加 ----
spec = mujoco.MjSpec.from_file(str(robot["xml"]))
WIDTH, HEIGHT = (int(x) for x in args.size.split("x"))
spec.visual.global_.offwidth, spec.visual.global_.offheight = WIDTH, HEIGHT
hand = spec.body(robot["hand_body"]).add_body(name="hand", pos=robot["hand_pos"], quat=robot["hand_quat"])
L = robot["finger_len"]
S = scale  # 仮の指・スポンジ・箱・お椀も、置き直しと同じ倍率で大きさを変える
hand.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.02 * S, 0.025 * S, 0.01 * S], pos=[0, 0, L - 0.05 * S],
              rgba=[0.3, 0.3, 0.3, 1], **VISUAL)  # 指の付け根（手のひら）
hand.add_site(name="tool", pos=[0, 0, L])  # 指先（IK で合わせる点）
fingers = [spec.worldbody.add_body(name=f"finger{k}", mocap=True) for k in range(2)]
for f in fingers:
    f.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.006 * S, 0.004 * S, 0.02 * S], rgba=[0.3, 0.3, 0.3, 1],
               **VISUAL)

if "green" in centers:  # 箱（半透明の白）
    b = spec.worldbody.add_body(name="box", pos=[*centers["green"], 0])
    bx, by, bz = BOX * S
    rgba = [0.9, 0.9, 0.95, 0.5]
    b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[bx, by, 0.002], pos=[0, 0, 0.002], rgba=rgba, **VISUAL)
    for sx, sy, px, py in [(bx, 0.002, 0, by), (bx, 0.002, 0, -by), (0.002, by, bx, 0), (0.002, by, -bx, 0)]:
        b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[sx, sy, bz], pos=[px, py, bz], rgba=rgba, **VISUAL)
if "yellow" in centers:  # お椀（赤）
    b = spec.worldbody.add_body(name="bowl", pos=[*centers["yellow"], 0])
    rgba = [0.55, 0.1, 0.05, 1]
    r, h = BOWL_R * S, BOWL_H * S
    b.add_geom(type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[r * 0.55, 0.003], pos=[0, 0, 0.003], rgba=rgba, **VISUAL)
    n, tilt = 16, np.deg2rad(35)
    r_mid = r * 0.55 + np.tan(tilt) * h / 2
    for k in range(n):
        a = 2 * np.pi * k / n
        quat = np.zeros(4)
        mujoco.mju_euler2Quat(quat, [0, tilt, a], "XYZ")
        b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.002, np.pi * r / n * 1.1, h / 2 / np.cos(tilt)],
                   pos=[r_mid * np.cos(a), r_mid * np.sin(a), h / 2], quat=quat, rgba=rgba, **VISUAL)
sponge_size = SPONGE * S
sponge = spec.worldbody.add_body(name="sponge", mocap=True)
sponge.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=sponge_size, rgba=COLORS[color_of(task)], **VISUAL)

model = spec.compile()
data = mujoco.MjData(model)
arm_joints = [j for j in range(model.njnt) if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE]
qadr = np.array([model.jnt_qposadr[j] for j in arm_joints])
dadr = np.array([model.jnt_dofadr[j] for j in arm_joints])
lo, hi = model.jnt_range[arm_joints].T
tool = model.site("tool").id
mocap = {name: model.body(name).mocapid[0] for name in ["finger0", "finger1", "sponge"]}


# ---- 逆運動学（減衰最小二乗法） ----
def solve_ik(q, p_goal, R_goal, iters=60, rot_weight=robot["rot_weight"], damping=1e-3):
    jacp, jacr = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    q_goal = np.zeros(4)
    mujoco.mju_mat2Quat(q_goal, R_goal.flatten())
    for _ in range(iters):
        data.qpos[qadr] = q
        mujoco.mj_forward(model, data)
        e_pos = p_goal - data.site_xpos[tool]
        q_now = np.zeros(4)
        mujoco.mju_mat2Quat(q_now, data.site_xmat[tool])
        e_rot = np.zeros(3)
        mujoco.mju_subQuat(e_rot, q_goal, q_now)  # 手先から見た向きのずれ
        e_rot = data.site_xmat[tool].reshape(3, 3) @ e_rot  # ヤコビアンに合わせて世界座標に直す
        e = np.r_[e_pos, rot_weight * e_rot]
        if np.linalg.norm(e_pos) < 1e-4 and np.linalg.norm(e_rot) < 1e-3:
            break
        mujoco.mj_jacSite(model, data, jacp, jacr, tool)
        J = np.r_[jacp[:, dadr], rot_weight * jacr[:, dadr]]
        dq = J.T @ np.linalg.solve(J @ J.T + damping * np.eye(6), e)
        q = np.clip(q + dq, lo, hi)
    data.qpos[qadr] = q
    mujoco.mj_forward(model, data)
    return q, np.linalg.norm(p_goal - data.site_xpos[tool])


q = np.clip(np.array(robot["home"]), lo, hi)
qs, errs = [], []
home = q.copy()
for p_goal, R_goal in targets:
    q, err = solve_ik(q, p_goal, R_goal)
    if err > 0.005:  # 前のフレームの答えから始めて行き詰まったら、初期姿勢から解き直して良い方を使う
        q2, err2 = solve_ik(home.copy(), p_goal, R_goal, iters=300)
        if err2 < err:
            q, err = q2, err2
    qs.append(q.copy())
    errs.append(err)
errs = np.array(errs)
print(f"IK の位置の誤差：平均 {errs.mean() * 1000:.1f} mm、最大 {errs.max() * 1000:.1f} mm"
      f"（10 mm を超えたフレーム {int((errs > 0.01).sum())} / {len(errs)}）")


def tool_pose(i):
    data.qpos[qadr] = qs[i]
    mujoco.mj_forward(model, data)
    return data.site_xpos[tool].copy(), data.site_xmat[tool].reshape(3, 3).copy()


# スポンジ：最後に掴んだ瞬間の指先の真下に置き、掴んでいる間は指先にくっつけ、最後に開いたら真下に落とす
ev = open_events(grip)
grasp_t, release_t = (ev[-2][1], ev[-1][0]) if len(ev) >= 2 else (len(state), len(state))
p, R_grasp = tool_pose(min(grasp_t, len(state) - 1))
start_pos = np.array([p[0], p[1], sponge_size[2]])
sponge_offset = R_grasp.T @ (start_pos - p)
fall_from = tool_pose(release_t - 1) if release_t < len(state) else None


def set_frame(i):
    p, R = tool_pose(i)
    # 仮の指：グリッパーの値（0〜100）に合わせて指の間隔を変える
    w = (0.008 + 0.03 * np.clip(state[i, 5], 0, 100) / 100) * S
    for k, sign in enumerate([1, -1]):
        data.mocap_pos[mocap[f"finger{k}"]] = p + R @ [0, sign * w, -0.02 * S]
        mujoco.mju_mat2Quat(data.mocap_quat[mocap[f"finger{k}"]], R.flatten())
    if i < grasp_t:
        pos, rot = start_pos, np.eye(3)
    elif i < release_t:
        pos, rot = p + R @ sponge_offset, R @ R_grasp.T
    else:
        k = min(1.0, (i - release_t) / 8)  # 8 フレームかけて真下に落とす
        fp = fall_from[0] + fall_from[1] @ sponge_offset
        pos, rot = np.array([fp[0], fp[1], fp[2] + (0.004 + sponge_size[2] - fp[2]) * k]), np.eye(3)
    data.mocap_pos[mocap["sponge"]] = pos
    mujoco.mju_mat2Quat(data.mocap_quat[mocap["sponge"]], rot.flatten())
    mujoco.mj_forward(model, data)


if args.video:
    import imageio

    renderer = mujoco.Renderer(model, HEIGHT, WIDTH)
    cam = mujoco.MjvCamera()
    cam.azimuth, cam.elevation, cam.distance = (float(x) for x in (args.camera or robot["camera"]).split(","))
    cam.lookat[:] = [0.2 * scale + offset[0], 0, 0.1 * scale]  # 作業範囲の中央あたり
    with imageio.get_writer(args.video, fps=ds.fps * args.speed, codec="libx264", quality=8) as writer:
        for i in range(len(state)):
            set_frame(i)
            renderer.update_scene(data, cam)
            writer.append_data(renderer.render())
    print(f"動画を保存：{args.video}")
    raise SystemExit

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        for i in range(len(state)):
            if not viewer.is_running():
                break
            start = time.time()
            set_frame(i)
            viewer.sync()
            time.sleep(max(0, 1 / (ds.fps * args.speed) - (time.time() - start)))
        time.sleep(1.0)  # 最後の姿勢で 1 秒止めてから繰り返す
