#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# dbcluster.py
#     GGHC cluster class
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
#      gghc/dbcluster.py
# ----------------------------------------------------------------------------


import re
import time
from dbnode import DbNode
import copy


class DbCluster():
    """
    classdocs
    """

    def __init__(self):
        """
        Constructor
        """
        self.state = ""
        self.nodes = []
        self.timeStamp = None

    def clear(self):
        self.state = ""
        self.nodes = []
        self.timeStamp = None

    def buildByQuery(self, clusterInfo):
        self.clear()
        flag1 = False
        dbClusterFormatter = None

        for info in clusterInfo.split("\n"):
            info = info.strip()
            if len(info) == 0:
                continue

            if (self.state == ""):
                if "cluster_state" in info:
                    self.state = info.split(":")[-1].strip()
                    flag1 = True

                continue
            # 判定节点状态是否竖线分割。等于1是为竖线分割，等于2分行显示
            if dbClusterFormatter is None:
                if re.search(r"(node\s+node_ip\s+instance\s+state\s+\|)+", info) is not None:
                    dbClusterFormatter = "v1"
                elif re.search(r"(node\s+node_ip\s+port\s+instance\s+state)", info) is not None:
                    dbClusterFormatter = "v2"

                continue

            # 所有datanode的状态竖线分割
            if dbClusterFormatter == 'v1':
                if re.search(r"(([0-9]{1,3}\.){3}[0-9]{1,3}.*\|)+", info) is not None:
                    for nodeInfo in info.split("|"):
                        dbNode = DbNode()
                        dbNode.buildByQuery(nodeInfo, dbClusterFormatter)
                        self.nodes.append(dbNode)
            # 每个datanode的状态分行显示
            elif dbClusterFormatter == 'v2':
                dbNode = DbNode()
                dbNode.buildByQuery(info, dbClusterFormatter)
                self.nodes.append(dbNode)

        self.timeStamp = time.localtime()
        return flag1 and len(self.nodes) > 0

    def getPrimaryNodeIds(self):
        nodeIds = []
        for nodeId in range(len(self.nodes)):
            node = self.nodes[nodeId]
            if((node.state).lower() == "primary"):
                nodeIds.append(nodeId)

        return nodeIds

    def getStandbyNodeIds(self):
        nodeIds = []
        for nodeId in range(len(self.nodes)):
            node = self.nodes[nodeId]
            if(node.state.lower() == "standby"):
                nodeIds.append(nodeId)

        return nodeIds

    def getNodeState(self, nodeId):
        if(nodeId >= len(self.nodes)):
            return None
        node = self.nodes[nodeId]
        return node.state

    def existsPendingNode(self):
        for node in self.nodes:
            if node.isPendingNode():
                return True
        return False

    def getClusterStateStr(self):
        return "%s[%s]" % (self.state, time.strftime("%Y-%m-%d %H:%M:%S", self.timeStamp))

    def __str__(self):

        nodeStr = ""
        for node in self.nodes:
            nodeStr += "%s;" % str(node)

        return "%s;%s" % (self.state, nodeStr[:-1])

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        super(DbCluster, result).__init__()
        return result



