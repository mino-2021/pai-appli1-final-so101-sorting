# 環境に合わせて変更してください
FOLLOWER_PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B7B008454-if00
LEADER_PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B7B015153-if00
FOLLOWER_ID=my_awesome_follower_arm
LEADER_ID=my_awesome_leader_arm
CAMERAS="{ front: {type: opencv, index_or_path: /dev/video0, width: 640, height: 360, fps: 30, fourcc: MJPG, backend: 200}}"
TASK="Put the green sponge in the box"
