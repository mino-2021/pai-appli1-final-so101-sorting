# PAI最終課題 提出作業まとめ（SO-101 × ACT スポンジ仕分け）

このファイルは、Physical AI応用1講座 最終課題の提出に向けた作業内容・現状・残タスクをまとめたものです。
AIアシスタントはこの内容を前提に、提出物（README、レポート、動画、スクリプト）の作成を支援してください。

---

## 1. 課題要件

- 課題名：AI×ロボティクスによる創造的タスクの実現
- 必須：何らかの形でAIを使用（推論のみでも可、学習は任意）
- ツール：ROS/Gazebo/Genesis想定だが、他ツール・実機も可
- 合格ライン：ロボットがタスクを実行する動画と提出物を提出
- 加点要素：創造性、技術力、実用性、表現力（動画構成・説明のわかりやすさ）
- サンプルはベースライン扱い。丸写しは修了判定対象外 → **工夫点・発展部分をレポートに明記**
- 失敗しても、反省点・考察をレポートに書けば評価対象になり得る

### 締切
- **2026年11月2日（月）AM10:00**

### 提出物と命名規則
| 提出物 | 形式・場所 | 名前・設定 |
|---|---|---|
| レポート | PDF / omnicampus | `説明資料_PAI最終課題_<omnicampusアカウント名>.pdf` |
| コード一式 | GitHub（**public**）のURL / omnicampus | https://github.com/mino-2021/pai-appli1-final-so101-sorting |
| 動画 | MP4 → YouTube、URLをomnicampusで提出 | タイトル `PAI最終課題_<omnicampusアカウント名>` |

### 動画の要件
- 長さ1〜3分（2倍速可。倍速の場合は動画内または概要欄に明記）
- 公開設定：限定公開が必須、**公開（全体）を推奨**（優秀生選出で加点）
- 「子ども向け動画」「年齢制限」は「いいえ」
- 「インスタントプレミアム公開」はチェックしない
- 採点完了まで削除・非公開にしない

### 個人情報の注意
- 動画・コード・レポートに**氏名・所属・メールアドレスを含めない**（omnicampusアカウント名は可）
- git の `user.email` は GitHub の noreply アドレスを使用
- 動画に顔、画面上の個人名、部屋の掲示物などが映らないようにする

---

## 2. タスク設計

- **タスク**：緑のスポンジを掴んで箱に入れる（第1段階）
- **拡張予定**：白のスポンジは箱に入れず、横へよける／決めた範囲に置く（検品工程の「良品は箱へ、不良品は除外」に見立てる）
- 箱は1つ（半透明の白い箱）
- 1エピソードにつきスポンジ1個
- 製造現場の仕分け・検品工程を想定 → **実用性**の説明に使う

---

## 3. 使用技術

- ロボット：SO-101（フォロワー＋リーダー、STS3215サーボ）
- フレームワーク：LeRobot（ROS2は不使用。Pythonから直接USB経由でサーボ制御）
- LeRobot：commit `22bd7a2f489b367d8df42de803b1e8c4ca63a3f9`（`~/work/robo/lerobot` から editable インストール）
- AIモデル：**ACT（Action Chunking with Transformers）**
  - Zhaoら（2023, Stanford ALOHA）が提案した模倣学習アルゴリズム
  - 入力：カメラ画像＋関節角度、出力：今後の行動チャンク（初期設定100ステップ）
  - 画像エンコーダ：ResNet-18（ImageNet事前学習）、本体：Transformerエンコーダ・デコーダ、CVAEで学習
  - 損失：L1損失＋KLダイバージェンス
- PC：Ubuntu、NVIDIA RTX A5000
- カメラ：USBカメラ1台（640×360、30fps、MJPG、V4L2）

---

## 4. 現在の進捗

- [x] SO-101設置、リーダー・フォロワーのキャリブレーション
- [x] テレオペ動作確認
- [x] カメラ設置・画角調整
- [x] 試し収録（緑、10エピソード）：`mino/so101_green_test_20261026_001122`
- [x] ACT試し学習（20,000ステップ、約20分、最終loss 約0.13）：`outputs/train/act_green_test`
- [x] 推論で「スポンジを掴んで箱に入れる」動作に成功（`max_relative_target=20`）
- [x] GitHubリポジトリ作成（scripts/、README雛形）
- [ ] 推論の成功率を計測（例：5回中◯回）
- [ ] 提出動画の撮影・編集・YouTubeアップロード
- [ ] レポート（PDF）作成
- [ ] README完成（動画URL、結果、工夫点）
- [ ] omnicampusで提出

### 改善版（時間があれば）
- [ ] 緑で本収録（40〜50エピソード）→ 本学習（50,000ステップ程度）
- [ ] 白スポンジを追加し、仕分けタスクに拡張
- [ ] 色別の成功率を評価
- [ ] 動画・レポートを改善版に差し替え

---

## 5. 環境設定（scripts/env.sh）

```bash
FOLLOWER_PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B7B008454-if00
LEADER_PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B7B015153-if00
FOLLOWER_ID=my_awesome_follower_arm
LEADER_ID=my_awesome_leader_arm
CAMERAS="{ front: {type: opencv, index_or_path: /dev/video0, width: 640, height: 360, fps: 30, fourcc: MJPG, backend: 200}}"
TASK="Put the green sponge in the box"
```

- 電源：フォロワー 12V（キット付属、2A）、リーダー 5V
- キャリブレーションファイル：`~/.cache/huggingface/lerobot/calibration/{robots/so_follower, teleoperators/so_leader}/`
- データセット保存先：`~/.cache/huggingface/lerobot/mino/`

---

## 6. 主要コマンド

### 収録
```bash
lerobot-record \
  --robot.type=so101_follower --robot.port=$FOLLOWER_PORT --robot.id=$FOLLOWER_ID \
  --robot.max_relative_target=20 --robot.cameras="$CAMERAS" \
  --teleop.type=so101_leader --teleop.port=$LEADER_PORT --teleop.id=$LEADER_ID \
  --display_data=true \
  --dataset.repo_id=mino/so101_green \
  --dataset.num_episodes=50 --dataset.single_task="$TASK" \
  --dataset.episode_time_s=40 --dataset.reset_time_s=600 \
  --dataset.push_to_hub=false
```
- キー操作：→ 録画終了／リセット中に押すと次の録画開始、← 撮り直し、Esc 収録終了
- 終了はEscで行い、保存処理が終わるまで待つ（Ctrl+Cやウィンドウを閉じると保存されない）

### 学習
```bash
lerobot-train \
  --dataset.repo_id=mino/<データセット名> \
  --policy.type=act --policy.device=cuda --policy.push_to_hub=false \
  --output_dir=outputs/train/<名前> --job_name=<名前> \
  --wandb.enable=false --steps=20000
```

### 推論
```bash
lerobot-rollout \
  --strategy.type=episodic \
  --policy.path=outputs/train/act_green_test/checkpoints/last/pretrained_model \
  --robot.type=so101_follower --robot.port=$FOLLOWER_PORT --robot.id=$FOLLOWER_ID \
  --robot.max_relative_target=20 --robot.cameras="$CAMERAS" \
  --task="$TASK" --duration=40 \
  --dataset.repo_id=mino/rollout_green_test --dataset.single_task="$TASK" \
  --dataset.push_to_hub=false --display_data=true
```

### 確認
```bash
lerobot-dataset-viz --repo-id mino/<データセット名> --episode-index 0
```

---

## 7. このバージョンのLeRobotでの注意点（ハマりどころ）

- 推論は `lerobot-record --policy.path` ではなく **`lerobot-rollout`** を使う
- 推論データセット名は **`rollout_` で始める**必要がある
- `episodic` モードは `--dataset.repo_id` が必須
- 収録時、データセット名に**日時が自動付与**される（無効化は `--dataset.no_stamp=true`）
- `push_to_hub` のデフォルトがtrueの場合があり、HFの名前空間 `mino` に権限がないと終了時にエラー → `--dataset.push_to_hub=false`
- カメラは640×480非対応。**640×360**を使用
- 動画はAV1形式。通常のプレーヤーでは黒く表示されることがある → `ffmpeg -i in.mp4 -c:v libx264 out.mp4` で変換
- USB抜き差しでACM番号が入れ替わる → `/dev/serial/by-id/` の固定パスを使用
- シリアルポートの権限 → `sudo usermod -aG dialout $USER` 後に再ログイン
- フォロワーとリーダーのキャリブレーションは、**同じ中央姿勢**で行うこと（ずれると角度がずれて追従する）
- `max_relative_target=5` では推論時に動きがかくかくし掴めなかった → 20で成功

---

## 8. レポートに書く内容（構成案）

1. **概要・目的**：SO-101とACTによる仕分けタスク。製造現場の検品・仕分け工程への応用を想定
2. **システム構成**：ハードウェア（SO-101、カメラ、PC）、ソフトウェア（LeRobot、ACT）、構成図
3. **手順**：キャリブレーション → テレオペでデータ収集 → ACT学習 → 推論
4. **結果**：エピソード数、学習時間、loss推移、推論の成功率
5. **工夫点**（サンプル「SO-101入門」からの発展部分）
   - タスクを製造現場の仕分け・検品に見立てた設計
   - スポンジ（柔らかく掴みやすい）と濃い色の机による認識しやすい環境設計
   - カメラ画角・背景・照明の固定
   - `max_relative_target` の調整による動作の改善（5 → 20）
   - USB固定パスの利用など、再現性を高める環境構築
6. **課題と今後の展望**
   - データ量（10エピソード）による成功率の限界
   - 電源容量（12V 2A）の制約
   - 色による仕分けへの拡張、ねじ締めなど精密作業への挑戦
   - 工程作業分析（物体検出）との連携、産業用ロボットへの展開

---

## 9. 動画構成案（1〜3分）

1. タイトル・タスク説明（テキスト）
2. システム構成（ロボット、カメラ、リーダーアーム）
3. テレオペによるデータ収集の様子
4. 学習（lossのグラフ、画面録画など）
5. **AIによる自律動作**（リーダーに誰も触れていないことが分かる外部視点＋ロボット視点）
6. まとめ・今後の展望（テキスト）
