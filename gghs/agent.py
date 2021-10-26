#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# agent.py
#     Accept the remote call of gghc and complete the command processing
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
#      gghs/agent.py
# ----------------------------------------------------------------------------


import sys
import traceback
import re
import os


def doCommand(command):        
    try:
        f = os.popen('bash --login -c  "%s"'  % command, 'r')
        outstr = f.read()
        f.close()
        return (True, outstr)
    except BaseException:
        return (False, traceback.format_exc())

# params： datanode_path
def getClusterListenipConfig(argv):
    ''' 执行gs_guc check -D /opt/software/install/data/db1  -c "listen_addresses" -N all '''
    argv2 = argv[2] 
    cmd = 'gs_guc check -D %s -c \\"listen_addresses\\" -N all ' % argv2  # 注意：这里的双引号需要转义,因为doCommand会有重复引号
    (rst, cmdout) = doCommand(cmd)

    return "%d#%s" % (int(rst), cmdout)

#
def getClusterState(argv):
    ''' 执行 gs_om -t status --detail '''
    cmd = 'gs_om -t status --detail'

    (rst, cmdout) = doCommand(cmd)
    return "%d#%s" % (int(rst), cmdout)


def refreshclusterConfig(argv):
    ''' 执行 gs_om -t refreshconf '''
    cmd = 'gs_om -t refreshconf'
    (rst, cmdout) = doCommand(cmd)
    
    if(not rst):
        return "0#%s" % cmdout
     
    if ("Successfully generated dynamic configuration file" in cmdout):
        return "1#succeed to refresh db cluster config"
    else: return "0#failed to refresh db cluster config \n%s" % cmdout   

def buildStandbyNode(datanodePath):
    cmd = "gs_ctl build -D %s" % datanodePath
    (rst, cmdout) = doCommand(cmd) 

    if(rst and ("server started" in cmdout)):
        return (True, "succeed to build the node to standby")
    
    cmd = "gs_ctl restart -M standby -D %s" % datanodePath
    (rst, cmdout) = doCommand(cmd) 

    if(rst and ("server started" in cmdout)):
        return (True, "succeed to restart -M the node to standby")    
    else: return (True, "failed to restart -M the node to standby for the reason: \n%s" % cmdout)

def setFloatIpState(state):
    ''' 设置浮动IP状态，state: up, down'''
    (rst, cmdout) = doCommand("sudo floatip.sh %s" % state)    
    if(not rst or re.match("success", cmdout) == None):
        return (False, cmdout)    
    else: return (True, cmdout)

def modifyListenAddress(listenAddr, nodeName, datanodePath):
    # 注意下面cmd中的双引号需要转义，否则会与doCommand中bash命令使用的双引号提前匹配
    cmd = '''gs_guc set -D %s -c \\"listen_addresses = '%s'\\" -N %s''' % (datanodePath, listenAddr, nodeName)
    (rst, cmdout) = doCommand(cmd)
    if(not rst): 
        return  (False, cmdout)
    
    matchval = re.findall('(?s)Total instances:\s+(\d+).+Failed instances:\s+(\d+).+Success to perform gs_guc', cmdout, 0)
    if(len(matchval) == 0 or (matchval[0][0] != '1' and matchval[0][1] != '0')):
        return (False, cmdout)
    else:
        return (True, "success modify  %s's listen address to %s" % (nodeName, listenAddr)) 

# 修改节点浮动IP状态
def modifyNodeFloatIpState(state, nodeListenAddr, nodeName, datanodePath):
    ''' 关闭节点浮动IP'''
    (rst, cmdout1) = setFloatIpState(state)    
    if(not rst):
        return (False, "failed to do floatip down, the reason is\n %s" % cmdout1)
    
    ''' 恢复节点ip地址'''
    (rst, cmdout2) = modifyListenAddress(nodeListenAddr, nodeName, datanodePath)
    
    return (rst, "succeed to do floatip %s.\n%s" % (state, cmdout2))


def clearNodeFloatIp(argv):
    nodeListenAddr = argv[2]
    nodeName = argv[3]
    datanodePath = argv[4]
    
    ''' 关闭节点浮动IP'''
    (rst, cmdout) = modifyNodeFloatIpState("down", nodeListenAddr, nodeName, datanodePath)
    return "%d#%s" % (int(rst), cmdout)

# CLEAR_NODE_FLOATIP_BUILD
def clearNodeFloatIpBuild(argv):
    nodeListenAddr = argv[2]
    nodeName = argv[3]
    datanodePath = argv[4]

    ''' 关闭节点浮动IP'''
    (rst, cmdout1) = modifyNodeFloatIpState("down", nodeListenAddr, nodeName, datanodePath)
    if(not rst):
        return "0#%s" % cmdout1    

    '''build节点为备节点'''
    (rst, cmdout2) = buildStandbyNode(datanodePath)
    return "%d#%s\n%s" % (int(rst), cmdout1, cmdout2)

# params： network card， ip
def confirmIpNetwork(argv):
    ''' 执行ifconfig enp0s3:1'''
    cardName = argv[2]  # network card name
    ip = argv[3]  # float ip
    dataNodePort = argv[4]
    
    cmd = 'ifconfig %s' % cardName
    
    matchStr = "(?s).*%s.*<UP,.*inet.%s" % (cardName, ip) 
    
    (rst, cmdoutstr) = doCommand(cmd)

    if(not rst or re.match(matchStr, cmdoutstr) == None):
        return "0#failed to confirm '%s' on network card '%s\n%s" % (ip, cardName, cmdoutstr) 

    cmd = "netstat -an |grep %s | grep %s" % (ip, dataNodePort)
    (rst, cmdout) = doCommand(cmd)
    if(not rst): 
        return "0#%s" % cmdout
    elif(len(cmdout.strip()) > 1):
        return "1#succeed to confirm '%s' on network card '%s' and become effective in postgresql.conf" % (ip, cardName)
    else: 
        return "0#confirmed '%s' on network card '%s' but not become effective in postgresql.conf" % (ip, cardName)        

def buildAsStandbyNode(argv):
    ''' 先强制stop，然后启动为备节点 '''
    dataNodePath = argv[2]
    dbPort = argv[3]
    
    # 查看进程是否存在
    cmd = "netstat -an |grep tcp | grep %s" % dbPort
    (rst, cmdout) = doCommand(cmd)
    # 若查询操作失败       
    if(not rst):   
        return "0#%s" % cmdout    
    
    cmdout1 = ""
    # 如果进程存在
    if(len(cmdout.strip()) > 1):
        cmd = "gs_ctl -m immediate stop -D %s" % dataNodePath
        (rst, cmdout1) = doCommand(cmd)
    
        if(not rst or not ("server stopped" in cmdout1)):
            return "0#%s" % cmdout1
    
    (rst, cmdout2) = buildStandbyNode(dataNodePath)    
    
    return "%d#%s\n%s" % (int(rst), cmdout1, cmdout2)

def forceNodePrimary(dataNodePath):
    cmd = "gs_ctl restart -M primary -D %s -m immediate" % dataNodePath
    (rst, cmdout) = doCommand(cmd)
    if(rst and ("server started" in cmdout)):
        return (True, "force to primary node succeed")
    else:
        return (False, cmdout) 


def checkRecoveryPrimaryNode(argv):
    '''
    0# failed
    1# force to primary node succeed
    2# The database process is existed
    '''
    dataNodePath = argv[2]
    dataNodePort = argv[3]
    cmd = "netstat -an |grep tcp | grep %s" % dataNodePort
    (rst, cmdout) = doCommand(cmd)
    if(not rst): 
        return "0#%s" % cmdout
    
    if(len(cmdout.strip()) > 1):
        return "2#The database process is existed"
    
    (rst, msg) = forceNodePrimary(dataNodePath)

    '''0#:失败，1#：成功'''
    return "%d#%s" %(int(rst), msg)

def recoveryUnknownNodeTargetState(argv):    
    dataNodePath = argv[2]
    dataNodePort = argv[3]
    targetState = argv[4]
    
    cmd = "netstat -an |grep tcp | grep %s" % dataNodePort
    (rst, cmdout) = doCommand(cmd)
    if(not rst): 
        return "0#%s" % cmdout
    if(len(cmdout.strip()) > 1):
        return "2#The database process exists"
    
    if (targetState.lower() == 'standby'):
        (rst, cmdout) = buildStandbyNode(dataNodePath)
    else:
        (rst, cmdout) = forceNodePrimary(dataNodePath)
    
    return "%d#%s" %(int(rst), cmdout)

def queryNodeTermLsn(argv):
    dataNodePort = argv[2]
    cmd = "gsql -d postgres -p %s -c 'select term, lsn from pg_last_xlog_replay_location()'" % dataNodePort
    (rst, cmdout) = doCommand(cmd)
    return "%d#%s" %(int(rst), cmdout)

def setFloatIpFailover(argv):
    nodeListenAddr = argv[2]
    nodeName = argv[3]
    dataNodePath = argv[4]
    
    '''主备切换'''
    cmd = "gs_ctl failover -D %s" % dataNodePath
    (rst, cmdout) = doCommand(cmd)
    if(not rst or not("failover completed" in cmdout)):
        return "0#db cluster failover failed\n%s" % cmdout
    
    msg = "db cluster failover succeed"
    
    '''修改浮动IP'''
    (rst, cmdout) = modifyNodeFloatIpState("up", nodeListenAddr, nodeName, dataNodePath)
    if(not rst):
        return "2#%s" % cmdout  # 修改浮动IP失败
    
    msg += "\n%s" % cmdout 
    
    ''' 重新拉起为启动 '''
    (rst, cmdout) = forceNodePrimary(dataNodePath)
    if(not rst):
        return "3#%s" % cmdout  # 重新拉起主节点失败
    
    msg += "\n%s" % cmdout
    
    ''' 刷新集群配置'''
    cmd = 'gs_om -t refreshconf'
    (rst, cmdout) = doCommand(cmd)
    if(not rst):
        return "4#%s\n%s" % (msg, cmdout)
    else:
        return "1#%s\n%s" % (msg, "db cluster refresh config succeed")

def primaryAddFloatIp(argv):
    nodeListenAddr = argv[2]
    nodeName = argv[3]
    dataNodePath = argv[4]

    '''修改浮动IP'''
    (rst, cmdout) = modifyNodeFloatIpState("up", nodeListenAddr, nodeName, dataNodePath)
    if(not rst):
        return "2#%s" % cmdout  # 修改浮动IP失败
    
    msg = cmdout 
    
    ''' 重新拉起为启动 '''
    (rst, cmdout) = forceNodePrimary(dataNodePath)    
    return "%d#%s\n%s" % (int(rst), msg, cmdout)  # 重新拉起主节点失败


def forceRecoverPrimaryNode(argv):
    '''
    将故障前的主节点继续强制恢复为Primary
    '''

    (rst, cmdout1) = setFloatIpState("up")
    if(not rst):
        return "0#failed to do floatIp up, the reason is\n %s" % cmdout1

    msg = "succeed to do floatIp up."

    dataNodePath = argv[2]
    ''' 重新拉起为启动 '''
    (rst, cmdout) = forceNodePrimary(dataNodePath)    
    return "%d#%s\n%s" % (int(rst), msg, cmdout)  # 重新拉起主节点失败
    
        
msg = ""
if (sys.argv[1] == 'GET_CLUSTER_LISTENIP_CONFIG'):   # params：datanode_path
    msg =  getClusterListenipConfig(sys.argv)
elif (sys.argv[1] == 'CONFIRM_FLOATIP_NETWORK'):   # params： network card, ip, dataNodePort
    msg = confirmIpNetwork(sys.argv)
elif (sys.argv[1] == 'GET_CLUSTER_STATUS'):      # params： null 
    msg = getClusterState(sys.argv)
elif (sys.argv[1] == 'CLUSTER_REFRESH_CONFIG'):  # params： null
    msg = refreshclusterConfig(sys.argv)
elif (sys.argv[1] == "CLEAR_NODE_FLOATIP"):  #  params： nodeListenAddr, nodeName, datanodePath
    msg = clearNodeFloatIp(sys.argv)
elif (sys.argv[1] == 'CLEAR_NODE_FLOATIP_BUILD'): # params: nodeListenAddr, nodeName, datanodePath
    msg = clearNodeFloatIpBuild(sys.argv)
elif (sys.argv[1] == 'BUILD_AS_STANDBY_NODE'): # params: datanodePath, dataNodePort
    msg = buildAsStandbyNode(sys.argv)
elif (sys.argv[1] == 'CHECK_AND_RECOVERY_PRIMARY_NODE'):   # params:  dataNodePath, dataNodePort
    msg = checkRecoveryPrimaryNode(sys.argv)        
elif (sys.argv[1] == 'RECOVERY_UNKNOWN_NODE_TARGETSTATE'): # params: dbDatanodePaths, dbNodePort, targetState
    msg = recoveryUnknownNodeTargetState(sys.argv)
elif (sys.argv[1] == 'QUERY_NODE_TERM_LSN'): # params: dbNodePort    
    msg = queryNodeTermLsn(sys.argv)
elif (sys.argv[1] == 'SET_FLOATIP_FAILOVER'):  # nodeListenAddr, nodeName, datanodePath
    msg = setFloatIpFailover(sys.argv)
elif (sys.argv[1] == 'PRIMARY_ADD_FLOATIP'):  # nodeListenAddr, nodeName, datanodePath
    msg = primaryAddFloatIp(sys.argv)
elif (sys.argv[1] == 'FORCE_RECOVERY_PRIMARY_NODE'):  # datanodePath
    msg = forceRecoverPrimaryNode(sys.argv)
else: 
    msg = "0#the command key %s is not existed or is error." % sys.argv[1]
    
        
    
    
print(msg)
