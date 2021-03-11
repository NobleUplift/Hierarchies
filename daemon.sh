#!/bin/bash

cwd=`basename "$PWD"`
screen -dmS $cwd ./autorestart_linux.sh
screen -r $cwd
