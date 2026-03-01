#!/bin/sh

./launch_bkchem-qt_gui.sh >/tmp/bkchem.log 2>&1 & \
while ! ~/nsh/easy-screenshot/run.sh -A Python; do sleep 0.7; done; \
osascript -e 'tell application "Python" to quit'
