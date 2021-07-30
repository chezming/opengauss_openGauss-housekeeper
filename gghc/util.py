#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sshclient.py
#     GGHC tool class
# Copyright (c) 2021 Chinasoft International Co., Ltd.
#
# gghc is licensed under Mulan PSL v2.
# You can use this software according to the terms
# and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#
#          http://license.coscl.org.cn/MulanPSL2
#
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
#
# IDENTIFICATION
#      gghc/sshclient.py
# ----------------------------------------------------------------------------

import re
from config import config
from log import system_log

class Util:
    
    @classmethod
    def parseListenAddressMsg(cls, msg):
        summaryFlag = False
        nodeListenIps = []
        nodeNames = []
        if(msg.startswith('1#')):
            msg = msg[2:]
            for info in msg.split("\n"):
                if (not summaryFlag):
                    matches = re.findall("Total GUC values:\s+(\d+).+Failed GUC values:\s+(\d+)", info)
                    if(len(matches) == 0):
                        continue
                    elif(int(matches[0][0]) != len(config.dbNodeIps) and int(matches[0][1]) != 0):
                        system_log.error("Get db_listen_address failure: \n%s " % msg)
                        return (False, [])
                    summaryFlag = True
                else:
                    matches = re.match(".*\[(.*)\]\s*.*\'((?:[0-9,\.\s]*))\'", info)
                    if(matches == None):
                        continue
                    
                    nodeNames.append(matches.groups()[0])
                    str1 = matches.groups()[1]
                    #去除IP地址间可能存在的空格
                    str2 = "".join(str1.split())   
                    ips = str2.split(",")
                    if(config.floatIp in ips):
                        ips.remove(config.floatIp)
                        
                    if(len(ips) != 1):
                        system_log.error("Get db_listen_address failure: \n%s " % msg)
                        return (False, [])       
                    nodeListenIps.append(ips[0])
                    
        system_log.info("dbNodenames: %s" % nodeNames)
        system_log.info("nodeListenIps: %s" % nodeListenIps)
        return (True, nodeNames, nodeListenIps)                       
                                            
    @classmethod
    def parseRefreshClusterConfMsg(cls, msg):        
        return msg.startswith(r"1#") 
        
    @classmethod
    def parseTermLsn(cls, msg):
        matches = re.findall(r"(?s)\s*(term).*(lsn).*(\d+)\s+\|\s+([0-9/A-Z]+).*\(1 row\)", msg)
        if(len(matches) != 1):
            return (False, None)
        else:
            match = matches[0]
            # 返回（term, lsn）二元组
            return (True, (match[2], match[3]))
           

    
            
