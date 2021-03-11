#!/bin/sh

cwd=`basename "$PWD"`
if hash python3 2>/dev/null; then
      echo "Python 3.5+ installed."
      echo "Running $cwd with Auto-Restart!"
      while :
      do
            sudo pip3.7 install -U discord
            python3 $cwd.py | tee ${cwd}.log
            sleep 5s
	  done
      echo "Done"
      exit 0
else
      echo "Python 3.5+ is not installed. Refer to Linux guide!"
      exit 1
fi
