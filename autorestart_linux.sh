#!/bin/sh

cwd=`basename "$PWD"`
if hash python3 2>/dev/null; then
      echo "Python 3.5+ installed."
      echo "Running $cwd with Auto-Restart!"
      counter=0
      while [ $counter -le 100 ]
      do
            pip3 install -U discord pymysql sshtunnel
            python3 -u $cwd.py | tee -a ${cwd}.log 2>&1
            sleep 5s
            counter=$(($counter+1))
      done
      echo "Done"
      exit 0
else
      echo "Python 3.5+ is not installed. Refer to Linux guide!"
      exit 1
fi
