#!/bin/bash
# 提出用動画を作成（OP → タイトル → データ収集 → 自律動作 → まとめ → ED、本編は2倍速）
cd "$(dirname "$0")/.."
FONT=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc
SPEED=2
OUT=${1:-movie/submission.mp4}
OLIVE=0xb0af8f

# テンプレートに合わせた白地のカード: $1=秒数 $2=大見出し $3=小見出し1行目 $4=小見出し2行目（省略可）
card() {
  echo "color=c=white:s=1920x1080:r=30:d=$1,drawbox=x=0:y=0:w=24:h=ih:color=$OLIVE:t=fill,drawbox=x=0:y=ih-24:w=iw:h=24:color=$OLIVE:t=fill,drawtext=fontfile=$FONT:text='$2':fontsize=84:fontcolor=black:x=150:y=380,drawtext=fontfile=$FONT:text='$3':fontsize=44:fontcolor=0x444444:x=150:y=540,drawtext=fontfile=$FONT:text='${4:- }':fontsize=44:fontcolor=0x444444:x=150:y=620"
}
# 本編: $1=入力番号 $2=左上ラベル $3=下部の注記
clip() {
  echo "[$1:v]setpts=PTS/$SPEED,fps=30,scale=1920:1080:flags=lanczos,setsar=1,drawbox=x=0:y=0:w=iw:h=96:color=black@0.55:t=fill,drawtext=fontfile=$FONT:text='$2':fontsize=48:fontcolor=white:x=36:y=20,drawtext=fontfile=$FONT:text='${SPEED}倍速再生':fontsize=48:fontcolor=0xffd84d:x=w-tw-36:y=20,drawtext=fontfile=$FONT:text='$3':fontsize=40:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=16:x=(w-tw)/2:y=h-th-44"
}
# OP/ED: 1080p・30fpsに揃える
tmpl() {
  echo "[$1:v]fps=30,scale=1920:1080,setsar=1"
}

ffmpeg -y \
  -i "template/PAI応用1_最終課題_OP.mp4" -i movie/train.mp4 -i movie/rollout.mp4 -i "template/PAI応用1_最終課題_ED.mp4" \
  -filter_complex "
$(tmpl 0)[op];
$(card 5 'SO-101 × ACT  スポンジ箱入れタスク' '模倣学習（ACT）で「緑のスポンジを掴んで箱に入れる」' '製造現場の仕分け・検品工程を想定')[t0];
$(card 3 '① データ収集' 'リーダーアームによるテレオペ（ロボット搭載カメラの映像）')[t1];
$(clip 1 '① テレオペでデータ収集（10エピソード）' 'この映像と関節角度をACTの学習データにする')[v1];
$(card 3 '② AIによる自律動作' '学習したACTモデルで推論（人は操作していません）')[t2];
$(clip 2 '② ACTによる自律動作（推論）' '※スポンジの置き直しのみ人の手で行っています')[v2];
$(card 6 'まとめ' 'データ10エピソード・学習2万ステップ（約20分）で自律的な箱入れに成功' '今後：白スポンジを除外する仕分け（検品工程）へ拡張')[t3];
$(tmpl 3)[ed];
[op][t0][t1][v1][t2][v2][t3][ed]concat=n=8:v=1:a=0,format=yuv420p[v]
" -map "[v]" -c:v libx264 -preset slow -crf 20 -movflags +faststart "$OUT"
