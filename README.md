# SO-101 × ACT によるスポンジ仕分けタスク

Physical AI応用1講座 最終課題

## 概要
SO-101ロボットアームとLeRobotを用い、テレオペで収集したデモデータから
ACT（Action Chunking with Transformers）を模倣学習し、
緑色のスポンジを箱に入れるタスクを自律実行させた。

## 動画
（YouTubeのURL）

## 環境
- ロボット：SO-101（フォロワー／リーダー）
- カメラ：USBカメラ 1台（640×360, 30fps）
- PC：Ubuntu, NVIDIA RTX A5000
- LeRobot：commit （コミットID）

## 実行手順
1. `scripts/env.sh` のポート・IDを環境に合わせて変更
2. データ収集：`scripts/record.sh`
3. 学習：`scripts/train.sh`
4. 推論：`scripts/rollout.sh`

## 結果
（成功回数など）

## 工夫点・今後の展望
（記載予定）
