# MuJoCo シミュレーション

SO-101 で収録したデータセット（LeRobot 形式）の動きを、MuJoCo の 3D モデルで再生する。
SO-101 自身で再生するほか、UR5e・COBOTTA・myCobot 280 に動きを移し替えて再生することもできる。

- どれも **見せるための再生**で、物理計算はしない（関節角度をそのまま置いて表示する）
- 移し替えた動きは、移し替え先のロボットの学習データには使えない（カメラ映像は SO-101 のまま）
- スクリプトは、このリポジトリのフォルダで実行する（`--video outputs/sim/...` の保存先は実行した場所が基準）

## 1. 準備

### 必要なパッケージ（lerobot の venv）

| パッケージ | バージョン | 用途 |
|---|---|---|
| mujoco | 3.11.0 | シミュレーション・表示（もともと入っている） |
| imageio ＋ imageio-ffmpeg | 2.37.4 ＋ 0.6.0 | `--video` で MP4 を保存（もともと入っている） |
| trimesh ＋ pycollada | 5.2.0 ＋ 0.9.3 | `urdf_to_mujoco.py` で .dae を STL に変換（追加で入れた） |

```bash
uv pip install --python ~/work/robo/lerobot/.venv/bin/python trimesh==5.2.0 pycollada==0.9.3
```

### ロボットのモデル（`~/work/robo/models/`、リポジトリの外）

| ロボット | 置き場所 | 取得元 | MuJoCo での形式 |
|---|---|---|---|
| SO-101 | `SO-ARM100/Simulation/SO101/` | TheRobotStudio/SO-ARM100（`Simulation/SO101` だけ sparse checkout） | MJCF（そのまま） |
| UR5e | `mujoco_menagerie/universal_robots_ur5e/` | google-deepmind/mujoco_menagerie（`universal_robots_ur5e` だけ sparse checkout） | MJCF（そのまま） |
| COBOTTA | `awesome-robot-arm-zoo/models/denso/cobotta/` | hyyyyyyz/awesome-robot-arm-zoo（元は DENSORobot/denso_robot_ros2、Apache-2.0） | URDF＋.dae → 変換が必要 |
| myCobot 280 M5 | `awesome-robot-arm-zoo/models/elephant_robotics/mycobot_280_m5/` | 同上（元は elephantrobotics/mycobot_ros、BSD-3-Clause） | URDF＋.dae → 変換が必要 |

```bash
cd ~/work/robo/models
git clone --depth 1 --filter=blob:none --sparse https://github.com/TheRobotStudio/SO-ARM100
cd SO-ARM100 && git sparse-checkout set Simulation/SO101 && cd ..
git clone --depth 1 --filter=blob:none --sparse https://github.com/google-deepmind/mujoco_menagerie
cd mujoco_menagerie && git sparse-checkout set universal_robots_ur5e && cd ..
git clone --depth 1 --filter=blob:none --sparse https://github.com/hyyyyyyz/awesome-robot-arm-zoo
cd awesome-robot-arm-zoo && git sparse-checkout set models/denso/cobotta models/elephant_robotics/mycobot_280_m5
```

### COBOTTA・myCobot の変換（`scripts/urdf_to_mujoco.py`）

MuJoCo は .dae を読めないので、STL に変換して MJCF に書き出す。出力先は `~/work/robo/models/mujoco_converted/`。

```bash
Z=~/work/robo/models/awesome-robot-arm-zoo/models
C=~/work/robo/models/mujoco_converted
python scripts/urdf_to_mujoco.py $Z/denso/cobotta/urdf/cobotta.urdf $C/cobotta
python scripts/urdf_to_mujoco.py $Z/elephant_robotics/mycobot_280_m5/urdf/arm/mycobot_280_m5.urdf $C/mycobot_280_m5
# グリッパー付き（表示のみ。retarget_sim.py では使わない）
python scripts/urdf_to_mujoco.py $Z/elephant_robotics/mycobot_280_m5/urdf/with_gripper_parallel/mycobot_280_m5.urdf $C/mycobot_280_m5_gripper
```

- .dae に書かれた長さの単位（`<unit meter="0.001">` など）をメートルに直す。myCobot は部品ごとに mm と m が混在している（trimesh は単位を反映しないため、スクリプトで倍率をかける）
- 慣性（重さ）が書かれていないリンクは形から計算する（表示用の近似）
- STL には色が無いので、灰色一色で表示される

モデルだけを見るとき：

```bash
python -m mujoco.viewer --mjcf=$HOME/work/robo/models/mujoco_menagerie/universal_robots_ur5e/scene.xml
python -m mujoco.viewer --mjcf=$HOME/work/robo/models/mujoco_converted/cobotta/scene.xml
```

## 2. SO-101 で再生（`scripts/replay_sim.py`）

```bash
python scripts/replay_sim.py 31                                   # エピソード 31 を画面で再生（繰り返し）
python scripts/replay_sim.py 5 --speed 0.5                        # 0.5 倍速
python scripts/replay_sim.py 5 --no-objects                       # ロボットだけ
python scripts/replay_sim.py 31 --video outputs/sim/sim_ep31.mp4  # 画面を出さずに MP4 で保存
python scripts/replay_sim.py 5 --video outputs/sim/sim_ep5.mp4 --camera 150,-30,0.8  # 視点（方位角,仰角,距離）
python scripts/replay_sim.py 31 --save-xml sim_ep31.xml           # 物体を含めたモデルを XML で保存
python scripts/replay_sim.py 5 --repo mino/so101_sort_2cam --key action  # 別のデータセット・指令値で再生
```

- 既定のデータセットは `mino/so101_sort_2cam_v3`（緑 0〜19、黄 20〜39）
- 関節角度：LeRobot の SO-101 は度単位（範囲の中央が 0 度）で、SO-ARM100 の new calib モデルと同じ基準なので、ラジアンに直すだけで対応する。グリッパー（0〜100）はモデルの関節範囲に線形で割り当てる
- 画面の「Save XML」ボタンは、このスクリプトでは使えない（モデルを MjSpec で組み立てているため「No XML model loaded」になる）。`--save-xml` を使う

## 3. 別のロボットに移し替えて再生（`scripts/retarget_sim.py`）

```bash
python scripts/retarget_sim.py 31                                   # COBOTTA（既定）
python scripts/retarget_sim.py 31 --robot ur5e
python scripts/retarget_sim.py 31 --robot mycobot
python scripts/retarget_sim.py 5 --robot ur5e --video outputs/sim/ur5e_ep5.mp4
python scripts/retarget_sim.py 5 --scale 1.2 --offset 0.05,0,0     # 置き直しの調整（既定はロボットごと）
```

関節の数や長さが違うため、関節角度ではなく「グリッパー先端の通り道」を移し替える：

1. SO-101 のモデルで、各フレームの先端の位置と向きを計算する
2. 机の高さを 0 にして `scale` 倍し、`offset` だけずらす
3. 移し替え先の指先がその位置・向きに来る関節角度を、逆運動学（IK）で求める
   - MuJoCo のヤコビアンを使った減衰最小二乗法。前のフレームの答えから解き始め、行き詰まったら初期姿勢から解き直して良い方を使う
   - 向き：SO-101 の先端の x 軸（指の向き）→ 手先の z 軸、y 軸（指が開く向き）→ 手先の y 軸
4. どのモデルにもハンドが無いので、手先に仮の指（灰色の板 2 枚）を付け、グリッパーの値で開閉させる

ロボットごとの設定（`ROBOTS`）：

| ロボット | 倍率 | ずらし（m） | 向きの重み | 指の長さ（m） | 備考 |
|---|---|---|---|---|---|
| cobotta | 1.0 | 0.05,0,0 | 0.3 | 0.09 | |
| ur5e | 2.0 | 0.15,0,0 | 0.3 | 0.15 | ハンドの取り付けは menagerie の attachment_site と同じ |
| mycobot | 0.9 | 0.05,0,0 | 0.1 | 0.05 | 届く範囲が約 0.28 m と狭いので縮め、向きより位置を優先 |

先端の位置のずれ（IK の誤差、平均／最大）：

| ロボット | 緑（ep5） | 黄（ep31） |
|---|---|---|
| COBOTTA | 2.1 / 32 mm | 2.8 / 132 mm |
| UR5e | 5.1 / 191 mm | 0.0 / 0.1 mm |
| myCobot 280 | 2.8 / 13 mm | 0.2 / 2.6 mm |

大きくずれるのは腕を戻す途中の空中の数フレームで、掴む・放す瞬間はほぼ合っている。

ロボットを追加するときは `ROBOTS` に 1 項目足す（モデル、手先のボディ、ハンドの取り付け位置・向き、指の長さ、IK の初期姿勢、倍率・ずらし、向きの重み、カメラ）。

## 4. スポンジ・箱・お椀（両スクリプト共通の考え方）

見せるための近似で、物理計算はしない。

| 項目 | 決め方 |
|---|---|
| 机の高さ | データセット全体でグリッパー先端が一番低くなった高さ − 3 mm。モデルと実機の角度のずれで、机を z=0 にするとグリッパーが最大約 1.7 cm めり込むため（床をその高さまで下げる） |
| 箱・お椀の位置 | 色ごとに、放した瞬間（最後に開いた瞬間）の先端の平均位置 |
| 掴む・放すの判定 | グリッパーの指令値（action）が 30 を超えている区間を「開いている」とする。スポンジを挟むと状態の値は閉じきらないため、指令値を使う |
| スポンジの動き | 最後に掴んだ瞬間の先端の真下に置く → 掴んでいる間は先端にくっつけて動かす → 最後に開いたら 8 フレームかけて真下に落とす |
| 大きさ | スポンジ 7×5×3 cm、箱 20×15×6 cm、お椀 半径 8.5 cm・高さ 6 cm（推測。`replay_sim.py` 冒頭の定数で変更） |

- 放した位置にお椀・箱を置いているので、中に落ちて見えるのは当然の結果（縁に当たって転がるなどは再現しない）
- お椀は底の円柱と、外向きに傾けた板 16 枚で作っている

## 5. 出力

動画は `outputs/sim/`（.gitignore 済み）に保存している。

| ファイル | 内容 |
|---|---|
| `sim_ep5_green.mp4`、`sim_ep31_yellow.mp4` | SO-101（replay_sim.py） |
| `cobotta_ep5.mp4`、`cobotta_ep31.mp4` | COBOTTA（retarget_sim.py） |
| `ur5e_ep5.mp4`、`ur5e_ep31.mp4` | UR5e |
| `mycobot_ep5.mp4`、`mycobot_ep31.mp4` | myCobot 280 M5 |

## 6. 注意点・既知の問題

- 画面が無い環境で `--video` を使うときは `MUJOCO_GL=egl` を付ける
- SO-ARM100 の `Simulation/SO101/README.md` には、グリッパーの 0〜100 の対応関係は「まだモデルに反映されていない」とある。両スクリプトでは関節範囲に線形で割り当てているので、開き具合の見た目は実物と少し違う可能性がある
- awesome-robot-arm-zoo の myCobot の README には「.dae の単位は読み込む側で反映すること」とあり、実際に部品ごとに mm と m が混在していた（`urdf_to_mujoco.py` で対応済み）
- COBOTTA の重さは仮の値（1 kg）、myCobot は一部のリンクに慣性が無い。表示だけなら問題ない
