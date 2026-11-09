"""URDF（メッシュが .dae）を MuJoCo で読める形（MJCF＋STL）に変換する。元のファイルは変更しない。

使い方：python scripts/urdf_to_mujoco.py <URDF> <出力フォルダ>
  例：python scripts/urdf_to_mujoco.py \\
        ~/work/robo/models/awesome-robot-arm-zoo/models/denso/cobotta/urdf/cobotta.urdf \\
        ~/work/robo/models/mujoco_converted/cobotta
出力：<出力フォルダ>/<名前>.xml（ロボット本体）、scene.xml（床と照明つき）、meshes/*.stl
表示：python -m mujoco.viewer --mjcf=<出力フォルダ>/scene.xml

- MuJoCo は .dae を読めないので、trimesh で STL に変換する。
  .dae に書かれた長さの単位（mm など）はメートルに直す（myCobot は部品ごとに単位が違う）
- 慣性（重さ）が書かれていないリンクは、形から計算する（inertiafromgeom="auto"）。表示用の近似

必要なパッケージ（lerobot の venv に追加済み。動作確認したバージョン）：
  trimesh 5.2.0、pycollada 0.9.3（.dae の読み込みに使う）、mujoco 3.11.0
  入れ方（uv 環境）：uv pip install --python ~/work/robo/lerobot/.venv/bin/python trimesh==5.2.0 pycollada==0.9.3
"""

import re
import sys
from pathlib import Path

import mujoco
import trimesh

urdf_path, out_dir = Path(sys.argv[1]).expanduser().resolve(), Path(sys.argv[2]).expanduser().resolve()
mesh_dir = out_dir / "meshes"
mesh_dir.mkdir(parents=True, exist_ok=True)
urdf = urdf_path.read_text()

converted = {}


def convert(match):
    src = match.group(1)
    if src not in converted:
        name = src.replace("/", "_").rsplit(".", 1)[0] + ".stl"
        mesh = trimesh.load(urdf_path.parent / src, force="scene").dump(concatenate=True)
        # trimesh は .dae の <unit meter="0.001"> を反映しないので、自分で倍率をかける
        unit = re.search(r'<unit[^>]*meter="([0-9.eE+-]+)"', (urdf_path.parent / src).read_text(errors="ignore"))
        if unit:
            mesh.apply_scale(float(unit.group(1)))
        mesh.export(mesh_dir / name)
        converted[src] = name
        print(f"{src} → meshes/{name}")
    return f'filename="{converted[src]}"'


urdf = re.sub(r'filename="([^"]+\.dae)"', convert, urdf, flags=re.IGNORECASE)
# MuJoCo 用の設定：メッシュの場所、見た目用のメッシュも残す、慣性が無いリンクは形から計算
urdf = re.sub(
    r"(<robot[^>]*>)",
    r'\1\n  <mujoco><compiler meshdir="meshes" discardvisual="false" balanceinertia="true"'
    r' inertiafromgeom="auto" fusestatic="false"/></mujoco>',
    urdf,
    count=1,
)
tmp_urdf = out_dir / urdf_path.name
tmp_urdf.write_text(urdf)

model = mujoco.MjModel.from_xml_path(str(tmp_urdf))
name = urdf_path.stem
mujoco.mj_saveLastXML(str(out_dir / f"{name}.xml"), model)
tmp_urdf.unlink()
(out_dir / "scene.xml").write_text(f"""<mujoco model="{name} scene">
  <include file="{name}.xml"/>
  <visual><headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/></visual>
  <asset>
    <texture type="2d" name="grid" builtin="checker" mark="edge" rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3"
             markrgb="0.8 0.8 0.8" width="300" height="300"/>
    <material name="grid" texture="grid" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
  </asset>
  <worldbody>
    <light pos="0 0 3" dir="0 0 -1" directional="true"/>
    <geom name="floor" size="0 0 0.05" type="plane" material="grid"/>
  </worldbody>
</mujoco>
""")
joints = [model.joint(i).name for i in range(model.njnt)]
print(f"保存：{out_dir / (name + '.xml')}、{out_dir / 'scene.xml'}（関節 {len(joints)} 個：{joints}）")
