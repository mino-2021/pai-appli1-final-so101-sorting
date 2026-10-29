"""フォロワーのモーター（ID 1〜6）の応答・電圧・温度・エラー状態を読み取る（書き込みはしない）

使い方: source scripts/env.sh && python scripts/check_motors.py $FOLLOWER_PORT
"""

import sys

import scservo_sdk as scs

PORT = sys.argv[1]
BAUDRATE = 1_000_000
NAMES = {1: "shoulder_pan", 2: "shoulder_lift", 3: "elbow_flex", 4: "wrist_flex", 5: "wrist_roll", 6: "gripper"}
# STS3215 のアドレス（lerobot/motors/feetech/tables.py と同じ）
ADDR_VOLTAGE, ADDR_TEMPERATURE, ADDR_STATUS = 62, 63, 65
STATUS_BITS = {0: "電圧", 1: "センサー", 2: "温度", 3: "電流", 5: "過負荷"}

port = scs.PortHandler(PORT)
packet = scs.PacketHandler(0)
if not port.openPort() or not port.setBaudRate(BAUDRATE):
    sys.exit(f"ポートを開けません: {PORT}")

for motor_id, name in NAMES.items():
    model, comm, err = packet.ping(port, motor_id)
    if comm != scs.COMM_SUCCESS:
        print(f"ID {motor_id} {name:13s} 応答なし ({packet.getTxRxResult(comm)})")
        continue
    volt, _, _ = packet.read1ByteTxRx(port, motor_id, ADDR_VOLTAGE)
    temp, _, _ = packet.read1ByteTxRx(port, motor_id, ADDR_TEMPERATURE)
    status, _, _ = packet.read1ByteTxRx(port, motor_id, ADDR_STATUS)
    errors = [label for bit, label in STATUS_BITS.items() if status & (1 << bit)]
    print(
        f"ID {motor_id} {name:13s} OK  電圧 {volt / 10:.1f}V  温度 {temp}℃  "
        f"エラー: {'・'.join(errors) if errors else 'なし'}"
    )

port.closePort()
