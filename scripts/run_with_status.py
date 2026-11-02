"""lerobot-record / lerobot-rollout を、録画中／リセット中がターミナルで分かる表示付きで実行する。

使い方：python run_with_status.py record|rollout <lerobot-record / lerobot-rollout と同じ引数>

LeRobot 本体は変更せず、状態の切り替わりで呼ばれる log_say を差し替えて
色付きの表示と残り時間を出す（音声は出さない）。
"""

import sys
import threading
import time

MODE = sys.argv.pop(1) if len(sys.argv) > 1 else ""
if MODE == "record":
    import lerobot.scripts.lerobot_record as entry

    patched = [entry]
    RUN_HINT = "  （終わったら n）"
    RESET_HINT = "  （準備できたら n で次の録画）"
elif MODE == "rollout":
    import lerobot.rollout.strategies.episodic as episodic
    import lerobot.scripts.lerobot_rollout as entry

    patched = [episodic]
    RUN_HINT = "  （AIで自動動作中、キーは押さない）"
    RESET_HINT = "  （初期姿勢に戻る。次の位置にスポンジを置く）"
else:
    sys.exit("usage: run_with_status.py record|rollout [args...]")

RED = "\033[1;97;41m"
YELLOW = "\033[1;30;43m"
CYAN = "\033[1;30;46m"
RESET = "\033[0m"


def arg_value(name, default):
    for a in sys.argv[1:]:
        if a.startswith(f"--{name}="):
            return float(a.split("=", 1)[1])
    return default


EPISODE_S = arg_value("dataset.episode_time_s", 60)
RESET_S = arg_value("dataset.reset_time_s", 60)
NUM_EPISODES = int(arg_value("dataset.num_episodes", 50))

state = {"label": None, "color": "", "start": 0.0, "limit": 0.0, "count": 0}


def show(label, color, limit, note=""):
    state.update(label=label, color=color, start=time.time(), limit=limit)
    sys.stdout.write(f"\033]0;{label}\007")  # ウィンドウのタイトルにも表示
    sys.stdout.write(f"\n{color}{'':>4}{label}{note}{'':>4}{RESET}\n")
    sys.stdout.flush()


def ticker():
    while True:
        time.sleep(0.5)
        if state["limit"]:
            left = max(0, state["limit"] - (time.time() - state["start"]))
            sys.stdout.write(f"\r\033[K{state['color']} {state['label']} 残り {left:4.0f}秒 {RESET}")
            sys.stdout.flush()


def log_say(text, play_sounds=True, blocking=False):
    if text.startswith("Recording episode"):
        state["count"] += 1
        show(f"● 録画中 {state['count']}/{NUM_EPISODES}", RED, EPISODE_S, RUN_HINT)
    elif text == "Reset the environment":
        show("■ リセット中", YELLOW, RESET_S, RESET_HINT)
    elif text == "Re-record episode":
        state["count"] -= 1
        show("↺ 撮り直し", CYAN, 0)
    elif text == "Stop recording":
        show("■ 収録終了（保存中、閉じずに待つ）", CYAN, 0)
    else:
        show(text, CYAN, 0)


for module in patched:
    module.log_say = log_say
threading.Thread(target=ticker, daemon=True).start()
entry.main()
