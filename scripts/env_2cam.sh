# 2台構成（前方＋手首）。env.sh を読み込み、CAMERAS だけ上書き
# 2台だと /dev/videoN の番号が入れ替わることがあるので by-id で指定
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
CAMERAS="{ front: {type: opencv, index_or_path: /dev/v4l/by-id/usb-GENERAL_GENERAL_WEBCAM-video-index0, width: 640, height: 360, fps: 30, fourcc: MJPG, backend: 200}, wrist: {type: opencv, index_or_path: /dev/v4l/by-id/usb-Innomaker_Innomaker-U20CAM-1080p-S1_SN0001-video-index0, width: 640, height: 360, fps: 30, fourcc: MJPG, backend: 200}}"
