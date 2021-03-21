#!/usr/bin/bash

appName="GGHC.py"
appId=$(ps -ef|grep GGHC.py |grep -v "grep"|awk '{printf$2}')

#echo appName: $appName
#echo appId: $appId

status(){
  echo "appName: $appName, pid: $appId"  
}

stop(){
if [ ! $appId  ]; then
        echo "can not find pid of $appName"  
else
        echo "get $appName pid: $appId"  
        kill -9 $appId
        echo "succeed to stop it."  
fi
}


start(){
appId=$(ps -ef|grep GGHC.py |grep -v "grep"|awk '{printf$2}')
if [ $appId  ]; then
        echo "appName: $appName, pid: $appId exists, please confirm and kill first by manual"  
        exit 1
fi

nohup python3 -u $HOME/gghc/GGHC.py > $HOME/start.log 2>&1 &
echo $appName started, pid is $!
echo please use command \'tail -F \$HOME/start.log\' to get more detail
}

restart(){
        stop
        start
}

usage(){
     echo "Usage: GGHC [start|stop|restart|status]"  
     exit 1
}


case "$1" in
  "start")
    start
    ;;
  "stop")
    stop
    ;;
  "status")
    status
    ;;
  "restart")
    restart
    ;;
  *)
    usage
    ;;
esac
