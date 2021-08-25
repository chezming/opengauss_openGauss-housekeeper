#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# dbnode.py
#     GGHC cluster node class
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
#      gghc/dbnode.py
# ----------------------------------------------------------------------------

import re
import time
import copy


class DbNode():
    """
    classDocs
    """

    def __init__(self):
        """
        Constructor
        """
        self.nodeId = ""
        self.nodeName = ""
        self.nodeIp = ""
        self.deployState = ""
        self.state = ""
        self.subState = ""
        self.supplementInfo = ""
        self.timeStamp = None

    def clear(self):
        self.nodeId = ""
        self.nodeName = ""
        self.nodeIp = ""
        self.deployState = ""
        self.state = ""
        self.subState = ""
        self.supplementInfo = ""
        self.timeStamp = None

    def buildByStatus(self, nodeInfo):
        info = nodeInfo.split(",")
        self.nodeId = info[0]
        self.nodeName = info[1]
        self.nodeIp = info[2]
        self.deployState = info[3]
        self.state = info[4]
        self.subState = info[5].strip()

        if(len(info) >= 7):
            self.supplementInfo = info[6]
        else:
            self.supplementInfo = ''

        self.timeStamp = time.localtime()

    def buildByQuery(self, nodeInfo, version):
        tmp_info = None
        if version == 'v1':
            # 格式： 1 gauss11 90.90.169.51 6001 /home/huawei/install/data/dn P
            # Primary Normal
            tmp_info = re.findall(
                r"(\d+)\s+(.*)\s+(\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)\s+(\d+)\s+(/.*)\s+(P|S)"
                "\\s+([\\w]*)\\s+([\\w\\s]+)(\\(.*\\))?", nodeInfo)
        elif version == 'v2':
            # 格式： 1 openGauss163 90.28.44.123 27790 6001
            # /data/liumin/pkg0720/cluster/dn1 P Primary Normal
            tmp_info = re.findall(
                r"(\d+)\s+(.*)\s+(\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)\s+\d+\s+(\d+)\s+(/.*)\s+(P|S)"
                "\\s+([\\w]*)\\s+([\\w\\s]+)(\\(.*\\))?", nodeInfo)

        self.nodeId = tmp_info[0][0]
        self.nodeName = tmp_info[0][1]
        self.nodeIp = tmp_info[0][2]
        #self.instance = tmp_info[0][3]
        #self.datanodePath = tmp_info[0][4]
        self.deployState = tmp_info[0][5]
        self.state = tmp_info[0][6]
        self.subState = tmp_info[0][7].strip()
        if(len(tmp_info[0][8]) > 2):
            self.supplementInfo = (tmp_info[0][8])[1:-1]
        else:
            self.supplementInfo = ''
        self.timeStamp = time.localtime()

    def isPendingNode(self):
        return (self.state == "Pending") \
               or (self.subState == "Starting") \
               or (self.subState == "Promoting") \
               or (self.subState == "Wait promoting") \
               or (self.subState == "Demoting") \
               or (self.subState == "Building")



    def getStateStr(self):
        return "%s %s(%s) [%s]" % (self.state,
                                   self.subState,
                                   self.supplementInfo,
                                   time.strftime(
                                       "%Y-%m-%d %H:%M:%S",
                                       self.timeStamp))

    def __str__(self):
        return "(%s,%s,%s,%s,%s,%s,%s)" % (self.nodeId,
                                           self.nodeName,
                                           self.nodeIp,
                                           self.deployState,
                                           self.state,
                                           self.subState,
                                           self.supplementInfo)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        super(DbNode, result).__init__()
        return result
