#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# checker.py
#     Opengauss cluster detection core class
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
#      gghc/checker.py
# ----------------------------------------------------------------------------

import traceback
import time
import copy
from config import config
from context import context
from const import const
from sshclient import SSH_Client
from log import system_log
from log import state_log
from dbcluster import DbCluster
from util import Util
import os


class ClusterStateChecker():
    """
    classdocs
    """

    def __init__(self):
        """
        Constructor
        """

        self.sshClients = [None] * len(config.dbNodeIps)
        self.dbClusterBeforeUnavailable = None    # 集群Unaviable前的状态
        self.lastDbCluster = DbCluster()    # 最近一次的集群状态
        self.lastCheckNodeid = 0
        self.dbNodeListenIps = []
        self.dbNodeNames = []

    def setDbNodeListenIp(self, msg):
        (rst, nodeNames, nodeListenIps) = Util.parseListenAddressMsg(msg)
        if (rst):
            self.dbNodeListenIps = nodeListenIps
            self.dbNodeNames = nodeNames

    def getSSHClient(self, nodeId):
        if self.sshClients[nodeId] is not None:
            return (True, self.sshClients[nodeId])

        hostIp = config.dbNodeIps[nodeId]
        username = config.dbUser
        privateKeyFile = config.gghcPrivateKeyFile
        sshClient = SSH_Client(hostIp, username, privateKeyFile)
        rst = sshClient.connect(nodeId)
        if rst:
            self.sshClients[nodeId] = sshClient
            system_log.info("get ssh connection for node %s succeed!" % (nodeId + 1))
            return (True, sshClient)
        else:
            self.sshClients[nodeId] = None
            system_log.fatal("gets ssh connection for node %s failed, it needs manual support" % (nodeId + 1))
            return (False, None)

    def initDbSSHClients(self):
        nodeSize = len(config.dbNodeIps)
        rstssh = []
        for nodeid in range(nodeSize):
            self.getSSHClient(nodeid)
            rstssh.append(self.sshClients[nodeid] is not None)

        system_log.info("finished to init ssh clients, the result is: %s", str(rstssh))

    def closeSSHClient(self, nodeId):
        sshClient = self.sshClients[nodeId]
        if (sshClient is not None):
            try:
                sshClient.close()
                system_log.info("Close ssh connect for node %d success!" % (nodeId + 1))
            except BaseException:
                system_log.fatal(traceback.format_exc())

    def closeDbSSHClients(self):
        nodeSize = len(config.dbNodeIps)
        for nodeId in range(nodeSize):
            self.closeSSHClient(nodeId)
        system_log.info("finished closing all ssh connections!")

    def getClusterListenIpConfig(self):
        (rst, sshClient) = self.getSSHClient(0)
        if (not rst):
            system_log.error("Get SSH Client failed at querying cluster listen ip")
            os._exit(-1)

        exeOut = ""
        for i in range(3):
            (rst, exeOut) = sshClient.execute(self.sshClients, 0, "GET_CLUSTER_LISTENIP_CONFIG",
                                              [config.dbDatanodePaths])
            if (rst): break

            system_log.error("Get SSH Client failed at querying cluster listen ip")
            if (i == 2):
                os._exit(-1)

        self.setDbNodeListenIp(exeOut)
        if (len(config.dbNodeIps) != len(self.dbNodeListenIps)):
            system_log.error("failed to get the db cluster listen addresses to check, maybe network error, system exited!")
            os._exit(-1)

        for nodeId in range(len(config.dbNodeIps)):
            if (config.dbNodeIps[nodeId] != self.dbNodeListenIps[nodeId]):
                system_log.error("by checking, the configed listen ips %s is not same as the queried %s, system exited! " % (config.dbNodeIps, self.dbNodeListenIps))
                os._exit(-1)
        system_log.info("finished getting the db cluster listen addresses!")

    def doUnfinishedOperations(self, sshClient, nodeId):
        '''
        context.unfinishedOperations操作  1: 主备切换后配置未能刷,  2: 浮动IP处理未完成
        context.float_ip_state: 1: Primary正常启动floatip，0: Standby正常清除floatip，-1: 故障主节点未能清除floatip 
        '''
        if (not context.hasUnfinishOpers()):
            system_log.debug("context has no unfinished operations.")
            return

        system_log.debug("to do unfinished operations")

        stateModFlag = False  # context是否变化
        floatIpAllModifyFlag = True  # 浮动IP是否存在修改失败

        # 主备切换后配置未能刷新配置
        if context.needDBRefreshConf():
            system_log.debug("need to refresh db cluster config")
            (rst, rsp) = sshClient.execute(self.sshClients, nodeId, "CLUSTER_REFRESH_CONFIG")
            if (not rst or not Util.parseRefreshClusterConfMsg(rsp)):
                system_log.info("Cluster config refreshing failed, and will try again in the next round")
            else:
                system_log.info("Cluster config refreshing success")
                context.removeUnfinishOper(const.CLUSTER_REFRESH_CONFIG)
                stateModFlag = True
                # 浮动IP处理
        elif (context.needClearFloatIp()):
            system_log.debug("need to clear standby node float ip")
            dbNodesSize = len(self.dbNodeListenIps)
            for idx in range(dbNodesSize):
                if (context.getFloatIpState(idx) == const.STANDBY_UNCLEAR_FLOATIP):  # 说明该节点浮动IP没有消除成功，需获取其sshClient进行
                    (rst, sshClientTmp) = self.getSSHClient(idx)
                    if (not rst):
                        system_log.debug("Cannot get ssh connection for nodeId %d, will try delete the float ip in the next round" % (idx + 1))
                        floatIpAllModifyFlag = False
                        continue

                    (rst, rsp) = sshClientTmp.execute(self.sshClients, idx, "CLEAR_NODE_FLOATIP_BUILD",
                                                      [self.dbNodeListenIps[idx], self.dbNodeNames[idx],
                                                       config.dbDatanodePaths])
                    if (not rst or not Util.parseRefreshClusterConfMsg(rsp)):
                        system_log.info("float ip clear failed on nodeId %d, will try it in the next round" % (idx + 1))
                        floatIpAllModifyFlag = False
                    else:
                        system_log.info("float ip clear succeed on nodeId %d" % (idx + 1))
                        context.setFloatIpState(idx, const.FLOATIP_NORMAL)
                        stateModFlag = True

            if (floatIpAllModifyFlag):
                context.removeUnfinishOper(const.CLEAR_FLOAT_IP)
                system_log.info("DB cluster's float ip on non primary nodes written in status file are all cleared.")

        if (stateModFlag):
            context.saveToFile()
            system_log.debug("context save to file.")

    def getClusterDbState(self):
        ''' 循环选择集群节点进行检测'''
        nodeSize = len(config.dbNodeIps)
        sshClient = None

        for _ in range(nodeSize):
            self.lastCheckNodeid = (self.lastCheckNodeid + 1) % nodeSize
            (rst, sshClient) = self.getSSHClient(self.lastCheckNodeid)
            if (rst): break

        if (None == sshClient):
            system_log.error("Cannot get SSH Connect, Cluster checking failed")
            return None

        self.doUnfinishedOperations(sshClient, self.lastCheckNodeid)

        system_log.debug("to get db cluster state on nodeId %d" % (self.lastCheckNodeid + 1))
        (rst, cmdOut) = sshClient.execute(self.sshClients, self.lastCheckNodeid, "GET_CLUSTER_STATUS")
        if (not rst):
            system_log.error("For ssh client reason, failed to get the cluster state and will try it in the next round")
            return None

        tmpDbCluster = DbCluster()
        rst = tmpDbCluster.buildByQuery(cmdOut[2:])
        if (rst):
            system_log.debug("current db cluster state is: %s" % (str(tmpDbCluster)))
            return tmpDbCluster
        else:
            system_log.error("current db cluster state is: %s" % (str(tmpDbCluster)))
            return None

    def confirmPrimaryFloatIp(self, primaryNodeId):
        '''检测Primary是否存在浮动IP，如果不存在则进行配置'''
        (rst, sshClient) = self.getSSHClient(primaryNodeId)
        if (not rst):
            system_log.fatal("Can not get ssh connection to primary nodeId %d to confirm float ip, system exit" % (
                        primaryNodeId + 1))
            os._exit(-1)

        (rst, msg) = sshClient.execute(self.sshClients, primaryNodeId, 'CONFIRM_FLOATIP_NETWORK',
                                       [config.floatipEth, config.floatIp, config.dbNodePort])
        if (not rst):
            system_log.fatal(
                "ssh connect to primary nodeId %d to confirm float ip failed, system exit" % (primaryNodeId + 1))
            os._exit(-1)

        if (msg.startswith('1#')):
            system_log.info("successfully confirmed primary node has float ip %s on network card %s" % (
            config.floatIp, config.floatipEth))
        else:
            system_log.info(
                "Find primary node has no float ip %s on network card %s or not become effective in postgresql.conf" % (
                config.floatIp, config.floatipEth))
            (rst, msg) = sshClient.execute(self.sshClients, primaryNodeId, 'PRIMARY_ADD_FLOATIP',
                                           [self.dbNodeListenIps[primaryNodeId] + ",%s" % config.floatIp,
                                            self.lastDbCluster.nodes[primaryNodeId].nodeName,
                                            config.dbDatanodePaths])
            if (not rst):
                system_log.fatal("set float ip on primary node %d failed, system exited" % (primaryNodeId + 1))
                os._exit(-1)
            else:
                system_log.info("set float ip on primary node %d succeed" % (primaryNodeId + 1))

    def processStatusDegrade(self, currDbClusterState, exceptNodeIds):
        self.recoveryFaultStandby(currDbClusterState, exceptNodeIds)

    def prcessClusterState(self, currDbClusterState):
        stateModFlag = False

        if (self.lastDbCluster.state == ''):
            self.lastDbCluster = currDbClusterState
            stateModFlag = True

        stateInfo = "cluser_state: %s" % self.lastDbCluster.getClusterStateStr()

        if (currDbClusterState.state != self.lastDbCluster.state):
            stateInfo += " --> %s" % currDbClusterState.getClusterStateStr()
            self.lastDbCluster.state = currDbClusterState.state
            stateModFlag = True

        for nodeId in range(len(self.lastDbCluster.nodes)):
            currNode = currDbClusterState.nodes[nodeId]
            lastNode = self.lastDbCluster.nodes[nodeId]
            stateInfo += "\n%s[%s]: %s" % (lastNode.nodeName, lastNode.nodeIp, lastNode.getStateStr())
            if (currNode.state != lastNode.state
                    or currNode.subState != lastNode.subState
                    or currNode.supplementInfo != lastNode.supplementInfo):
                stateInfo += " --> %s" % currNode.getStateStr()
                stateModFlag = True
            self.lastDbCluster.nodes[nodeId] = currDbClusterState.nodes[nodeId]

        if (stateModFlag):
            state_log.info(stateInfo)

    def buildStanbyForNode(self, nodeId):
        (rst, sshClient) = self.getSSHClient(nodeId)
        if (not rst):
            return
        system_log.info("build the nodeId %d to standby" % (nodeId + 1))
        (rst, msg) = sshClient.execute(self.sshClients, nodeId, 'BUILD_AS_STANDBY_NODE',
                                       [config.dbDatanodePaths, config.dbNodePort])
        if (not rst or not msg.startswith("1#")):
            system_log.fatal("DB nodeId %d needs manual to recover, the reason is:\n%s" % ((nodeId + 1), msg))

    def buildStandbyForNotLastPrimary(self, primaryNodeIds):
        primaryNodeIdBeforeUnaviables = self.dbClusterBeforeUnavailable.getPrimaryNodeIds()
        if (len(primaryNodeIdBeforeUnaviables) != 1):
            system_log.fatal("Can not getting Primary node before Cluster unavailable, DB Cluster needs manual to recover")
            return

        '''恢复非持续时间最长的Primary为Standby'''
        needRecoveryNodeids = list(set(primaryNodeIds) - set(primaryNodeIdBeforeUnaviables))
        needRecoveryNodeidsOut = [x + 1 for x in needRecoveryNodeids]
        system_log.info("the not last primary nodeIds needed to recover to standby are: %s" % needRecoveryNodeidsOut)
        for nodeId in needRecoveryNodeids:
            self.buildStanbyForNode(nodeId)

    def recoveryPrimaryNodeBeforeUnaviable(self, oldPrimaryNodeId, currDbClusterState):
        '''检测故障前主节点是否因为网络故障导致集群状态Unavailable，如果是DB进程故障，则强制拉起'''
        (rst, sshClient) = self.getSSHClient(oldPrimaryNodeId)
        if (not rst):
            return False

        if (currDbClusterState.getNodeState(oldPrimaryNodeId).lower() == "unknown"):
            (rst, msg) = sshClient.execute(self.sshClients, oldPrimaryNodeId, "CHECK_AND_RECOVERY_PRIMARY_NODE",
                                           [config.dbDatanodePaths, config.dbNodePort])
        else:
            (rst, msg) = sshClient.execute(self.sshClients, oldPrimaryNodeId, "FORCE_RECOVERY_PRIMARY_NODE",
                                           [config.dbDatanodePaths])

        if (not rst):
            return False
        elif (msg.startswith("0#")):
            system_log.error("Recover the primary nodeId %d before unavailable failed for the reason:\n%s" % ((oldPrimaryNodeId + 1), msg[2:]))
            return False
        elif (msg.startswith("1#")):
            system_log.info("Recover the nodeId %d to primary succeed." % (oldPrimaryNodeId + 1))
            return True
        elif (msg.startswith("2#")):
            system_log.fatal("The database process is existed on nodeId %s, please check its ssh newwork card." % (
                        oldPrimaryNodeId + 1))
            return True
        else:
            system_log.fatal("The nodeId %s state is unknown and can not connect to it, it needs manual support" % (
                        oldPrimaryNodeId + 1))
            return True

    def recoveryUnknownNode(self, nodeId, targetState):
        ''' 检测unknown状态的节点，如果是进程问题，则恢复到目标状态，否则是SSH网卡问题，需要人工修复'''
        (rst, sshClient) = self.getSSHClient(nodeId)
        if (not rst):
            return False

        (rst, msg) = sshClient.execute(self.sshClients, nodeId, "RECOVERY_UNKNOWN_NODE_TARGETSTATE",
                                       [config.dbDatanodePaths, config.dbNodePort, targetState])

        if (not rst):
            return False
        elif (msg.startswith("0#")):
            system_log.error("Recover standby nodeId %d failed for reason:\n%s" % ((nodeId + 1), msg[2:]))
            return False
        elif (msg.startswith("1#")):
            system_log.info("Recover standby nodeId %d succeed:\n" % (nodeId + 1))
            return True
        elif (msg.startswith("2#")):
            system_log.fatal(
                "There may be have ssh network card failure in the nodeId %s, it needs manual support" % (nodeId + 1))
            return False

    def recoveryFaultStandby(self, currDbClusterState, exceptNodeIds=None):
        if exceptNodeIds is None:
            exceptNodeIds = []
        for tmpNodeid in range(len(currDbClusterState.nodes)):
            if (tmpNodeid in exceptNodeIds): continue

            node = currDbClusterState.nodes[tmpNodeid]

            if node.isPendingNode():
                system_log.debug("the node state '%s' is pending, wait for it to recover automatically" % str(node))
                continue
            elif (node.state == "Standby"):
                if (node.subState == "Normal"):
                    continue
                elif (node.subState == "Need repair"):
                    if (node.supplementInfo.startswith("WAL")):
                        system_log.info("the node is in state '%s', build it to standby" % str(node))
                        self.buildStanbyForNode(tmpNodeid)
                    else:
                        system_log.debug("the node is in state '%s', wait for it to recover automatically" % str(node))
                        continue
                elif (node.subState == "Coredump" or node.subState == "Unknown"):
                    system_log.info("the node is in state '%s', build it to standby" % str(node))
                    self.buildStanbyForNode(tmpNodeid)
                else:
                    system_log.info("the node is in state '%s', wait for it to recover automatically" % str(node))
            elif (node.state == "Normal" or node.state == "Down"
                  or node.state == "Manually stopped" or node.state == "Abnormal"):
                system_log.info("the node is in state '%s', build it to standby" % str(node))
                self.buildStanbyForNode(tmpNodeid)
            elif (node.state == "Unknown"):
                system_log.info("the node is in state '%s', build it to standby" % str(node))
                self.recoveryUnknownNode(tmpNodeid, 'standby')
            elif (node.state == "Primary" and node.subState == "Normal"):
                continue
            else:
                system_log.info("the node is in state '%s', wait for it to recover automatically" % str(node))

    def getCandidatePrimary(self):
        """ 获取unavailable前的Standby节点，如果只有一个，则它是候选主节点；如果有多个，则按照算法进行选择；如果没有进行告警"""
        standbyNodeIdsBeforeUnavailable = self.dbClusterBeforeUnavailable.getStandbyNodeIds()
        standbyNodesCount = len(standbyNodeIdsBeforeUnavailable)

        if standbyNodesCount == 0:
            system_log.fatal("DB Cluster '%s' has not standby node before become unavailable,"
                             " so can not get candidate primary node. it needs manual support!"
                             % str(self.dbClusterBeforeUnavailable))
            return (False, -1)
        elif standbyNodesCount == 1:
            system_log.info("DB Cluster '%s' has only one standby node before become unavailable, so"
                            "it is the candidate primary node" % str(self.dbClusterBeforeUnavailable))
            return (True, standbyNodeIdsBeforeUnavailable[0])
        else:  # standbyNodesCount > 1
            candidateNodeId = -1
            candidateNodeTermlsn = ()
            for nodeId in standbyNodeIdsBeforeUnavailable:
                (rst, sshClient) = self.getSSHClient(nodeId)
                if not rst:
                    system_log.fatal("When the primary node failed, there were multiple standby nodes, but now because "
                                     "the SSH connection cannot be established, the term and LSN values of node %d "
                                     "cannot be queried, so the candidate primary node cannot be determined, and the "
                                     "primary / standby switching cannot be performed. Manual support is required."
                                     % (nodeId + 1))
                    return (False, -1)

                (rst, msg) = sshClient.execute(self.sshClients, nodeId, "QUERY_NODE_TERM_LSN", [config.dbNodePort])
                if not rst:
                    system_log.fatal("When the primary node failed, there were multiple standby nodes, but now because"
                                     " the reason: \n%s\n, the term and LSN values of node %d cannot be queried, so the "
                                     "candidate primary node cannot be determined, and the primary / standby switching "
                                     "cannot be performed. Manual support is required." % (msg, (nodeId + 1)))
                    return (False, -1)
                elif msg.startswith('1#'):
                    # termlsn 为（term, lsn）二元组
                    (rst, termlsn) = Util.parseTermLsn(msg[2:])
                    if (not rst):
                        system_log.fatal("When the primary node failed, there were multiple standby nodes, but now it is"
                                         "failed to parse the term lsn from \n'%s'\n of nodeId %d, so the candidate "
                                         "primary node cannot be determined, and the primary / standby switching cannot "
                                         "be performed. Manual support is required."  % (msg[2:], (nodeId + 1)))
                        return (False, -1)

                    if candidateNodeId == -1:
                        candidateNodeId = nodeId
                        candidateNodeTermlsn = termlsn
                    else:
                        if (candidateNodeTermlsn[0] > termlsn[0]  # 先比较term值，选择term值大的作为候选备机
                                # term相等，选择lsn值大的那个作为候选备机
                                or (candidateNodeTermlsn[0] == termlsn[0] and candidateNodeTermlsn[1] > termlsn[1])):
                            candidateNodeId = nodeId
                            candidateNodeTermlsn = termlsn
                        # else 保留nodeid小的作为候选备机
                else:  # msg.startswith('0#') 或其它原因
                    system_log.fatal("When the primary node failed, there were multiple standby nodes, but now because"
                                     " the reason: %s, the term and LSN values of node %d cannot be queried, so the "
                                     "candidate primary node cannot be determined, and the primary / standby switching "
                                     "cannot be performed. Manual support is required."  % (msg, (nodeId + 1)))
                    return (False, -1)

            system_log.info("get the candidate nodeId %d" % (candidateNodeId + 1))
            return (True, candidateNodeId)

    def clearNodeFloatIp(self, nodeId):
        clearFlag = True

        # (rst, sshClient) = self.getSSHClient(nodeId)   # 如果sshClient故障，说明网卡有问题，为加快恢复，不立即建立ssh连接
        sshClient = self.sshClients[nodeId]
        '''如果是单网卡，获取连接失败，说明主机故障或网卡故障；如果是双网卡说明监听网卡故障'''
        if (sshClient is None):
            clearFlag = False
        else:  # 获取连接成功，清除故障主节点浮动IP
            (rst, msg) = sshClient.execute(self.sshClients, nodeId, "CLEAR_NODE_FLOATIP",
                                           [self.dbNodeListenIps[nodeId], self.lastDbCluster.nodes[nodeId].nodeName,
                                            config.dbDatanodePaths])
            if not rst or not msg.startswith("1#"):
                clearFlag = False

        if not clearFlag:
            context.setFloatIpState(nodeId, const.STANDBY_UNCLEAR_FLOATIP)
            context.setUnfinishOper(const.CLEAR_FLOAT_IP)
            context.saveToFile()
            system_log.info("Cannot clear faulty primary node: %d float ip, write it to context and save to file" % (nodeId + 1))

        return clearFlag

    def nodeFailover(self, nodeId):
        (rst, sshClient) = self.getSSHClient(nodeId)
        '''如果是单网卡，获取连接失败，说明主机故障或网卡故障；如果是双网卡说明监听网卡故障'''
        if (not rst):
            system_log.fatal("Cannot ssh connect candidate primary nodeId %d, need manual support!" % (nodeId + 1))
            return False
        else:
            exeTimeout = 120   # 设置命令执行超时时间为120秒
            (rst, msg) = sshClient.execute(self.sshClients, nodeId, "SET_FLOATIP_FAILOVER",
                                           [self.dbNodeListenIps[nodeId] + ",%s" % config.floatIp,
                                            self.lastDbCluster.nodes[nodeId].nodeName,
                                            config.dbDatanodePaths],
                                            exeTimeout )
            if (not rst):
                return False
            else:
                if (msg.startswith('1#')):
                    system_log.info("the primary node has failed over to nodeId %d and has refreshed the cluster config" % (nodeId + 1))
                    return True
                elif (msg.startswith('4#')):
                    system_log.info("the primary node has failed over to nodeId %d but refresh the cluster config failed " % (nodeId + 1))
                    context.setUnfinishOper(const.CLUSTER_REFRESH_CONFIG)
                    context.saveToFile()
                    return True
                else:
                    system_log.info("Primary failover to nodeId %d failed, need manual support!" % (nodeId + 1))
                    return False

    def clusterFailover(self, lastPrimaryNodeId, candidatePrimaryNodeId, currDbClusterState):
        """
        1)关闭原先主节点浮动IP，并修改监听IP；
        2)开启候选节点浮动IP，修改监听IP，并failover为主节点；
        3)如果修改原主节点浮动IP成功，将原主节点Build为备节点，
        4)将其它故障节点恢复为备节点
        """
        # 浮动IP清除是否成功不影响下面操作，忽略其返回值
        system_log.info("to clear primary nodeId %d float ip" % (lastPrimaryNodeId + 1))
        clearFloatIpFlag = self.clearNodeFloatIp(lastPrimaryNodeId)

        rstFailOver = self.nodeFailover(candidatePrimaryNodeId)
        if (not rstFailOver):
            return False

        recoveryNodeIds = [candidatePrimaryNodeId]
        if (not clearFloatIpFlag):
            recoveryNodeIds.append(lastPrimaryNodeId)

        recoveryNodeIdsOut = [x + 1 for x in recoveryNodeIds]
        system_log.info("recovery all fault standby nodes except the nodeId %s" % recoveryNodeIdsOut)
        self.recoveryFaultStandby(currDbClusterState, recoveryNodeIds)

    def processStatusUnavailable(self, currDbClusterState):

        primaryNodeIds = currDbClusterState.getPrimaryNodeIds()
        if (len(primaryNodeIds) > 1):
            primaryNodeIdsOut = [x + 1 for x in primaryNodeIds]
            system_log.info("There are more than one primary nodeIds, current are %s" % primaryNodeIdsOut)
            self.buildStandbyForNotLastPrimary(primaryNodeIds)
            return
        elif currDbClusterState.existsPendingNode():
            system_log.info("Current DB Cluster exists pending nodes, Wait for it to recover automatically!")
            return

        primaryNodeIdBeforeUnaviables = self.dbClusterBeforeUnavailable.getPrimaryNodeIds()
        if (len(primaryNodeIdBeforeUnaviables) != 1):
            system_log.fatal("Can not getting Primary node before Cluster became unavailable, DB cluster needs manual to recover")
            return

        # 如果不是sshClient问题，则优先恢复故障前主节点
        if self.sshClients[primaryNodeIdBeforeUnaviables[0]] is not None:
            '''恢复故障前主节点'''
            rst = self.recoveryPrimaryNodeBeforeUnaviable(primaryNodeIdBeforeUnaviables[0], currDbClusterState)
            if (rst):  # 如果恢复主节点成功
                self.recoveryFaultStandby(currDbClusterState, primaryNodeIdBeforeUnaviables)
                return

            system_log.info("recover the nodeId %s to primary failed, so system will find the candidate primary node and make it to primary." % (
                            primaryNodeIdBeforeUnaviables[0] + 1))

        ''' 找到候选主节点进行主备切换 '''
        (rst, candidatePrimaryNodeId) = self.getCandidatePrimary()
        if (not rst):
            return

        system_log.info("the candidate primary nodeId is %d and will fail over to it" % (candidatePrimaryNodeId + 1))
        self.clusterFailover(primaryNodeIdBeforeUnaviables[0], candidatePrimaryNodeId, currDbClusterState)

    def check(self):
        try:
            self.initDbSSHClients()
            self.getClusterListenIpConfig()
            system_log.info("System successfully started.")
            print("System successfully started.")
            firstCheckFlag = True  # 首次测试
            while True:
                start = time.time()

                currDbClusterState = self.getClusterDbState()

                # if(system_log.level == logging.DEBUG):
                #    print("db current state is %s" % str(currDbClusterState))

                if (currDbClusterState is not None):

                    if (currDbClusterState.state != "Unavailable"):
                        self.dbClusterBeforeUnavailable = None

                    # 在初始进入unavailable状态时，保留之前的集群状态，以便必要时恢复故障前主机
                    elif (self.dbClusterBeforeUnavailable is None):
                        self.dbClusterBeforeUnavailable = copy.deepcopy(self.lastDbCluster)

                    try:
                        if (currDbClusterState.state == "Normal"):
                            self.dbClusterBeforeUnavailable = None
                            system_log.debug("db current state is normal, system does nothing")
                            pass
                        elif (currDbClusterState.state == "Degraded"):
                            self.dbClusterBeforeUnavailable = None
                            system_log.debug("db current state is degraded, system will process it")
                            self.processStatusDegrade(currDbClusterState, [currDbClusterState.getPrimaryNodeIds()])
                        else:  # Unavailable
                            if (firstCheckFlag):
                                system_log.error("when system start, DB cluster state is '%s'. "
                                                 "It should be Normal or Degraded and can successfully acquire db nodes' listen_addresses, "
                                                 "so system exits." % str(currDbClusterState))
                                os._exit(1)

                            system_log.debug("db current state is unavailable, system will process it")
                            self.processStatusUnavailable(currDbClusterState)
                    except BaseException:
                        system_log.error("%s", traceback.format_exc())
                        traceback.format_exc()

                    # 处理状态变化，记录状态日志,将currDbClusterState的变化复制给lastDbCluster，使其保持最新变化
                    self.prcessClusterState(currDbClusterState)
                    if (firstCheckFlag):
                        # 确保Primary节点配置有浮动ip，如果没有则进行配置
                        primaryNodeIds = currDbClusterState.getPrimaryNodeIds()
                        self.confirmPrimaryFloatIp(primaryNodeIds[0])

                    firstCheckFlag = False

                stop = time.time()
                wait = int(config.stateCheckPeriod) - (stop - start)
                if (wait > 0):
                    time.sleep(wait)

        finally:
            system_log.info("System stopped.")
            print("System stopped.")
            self.closeDbSSHClients()
        pass