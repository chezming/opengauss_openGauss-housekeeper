#!/bin/sh

# Opengauss监听地址所属网卡
netcard='enp0s3'
# 浮动IP网卡标签名称
float_card_label='enp0s3:1'
# 浮动IP地址
floatip='10.88.50.254'

find_netcard()
{
    my_netcard=$1;
    my_ip=$2

    result=`echo $(ifconfig $my_netcard | grep $my_ip)`
    if [[ ${#result} > 0 ]]; then
       echo 1
    else
       echo 0
    fi
}

param=$1

find_flag=$(find_netcard $float_card_label $floatip)

if [ $param == "up" ]; then
   if [ $find_flag == 0 ]; then
       ip addr add $floatip/24 dev $netcard label $float_card_label
       float_set=`find_netcard $float_card_label $floatip`
   else
       float_set=1
   fi
elif [ $param == "down" ]; then
   if [ $find_flag == 1 ]; then
       ip addr del $floatip/24 dev $netcard label $float_card_label
       float_set=`find_netcard $float_card_label $floatip`
   else
       float_set=0
   fi
fi

if [[ $param == "up" && $float_set == 1 ]] || [[ $param == "down" && $float_set == 0 ]]; then
   echo "success"
else 
   echo "failure"
fi
