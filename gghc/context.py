#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# context.py
#     System processing context class
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
#      gghc/context.py
# ----------------------------------------------------------------------------


import os
import traceback
from xml.dom.minidom import parse
from log import system_log
from xml.dom import minidom
from const import const


class Context():
    '''
    classdocs
    '''


    
    def __init__(self):
        '''
        Constructor
        '''
        self.hasStatusFile = False
        self.fileFullName = ""
        self.fileName = ""
        self.filePath = ""
               
        self.__unfinishedOperations = []
        self.__floatIpStates = []
        
    def hasUnfinishOpers(self):
        return len(self.__unfinishedOperations) != 0
    
    def setUnfinishOper(self, unfinishOper):
        if not (unfinishOper in self.__unfinishedOperations):
            self.__unfinishedOperations.append(unfinishOper)
            
    def removeUnfinishOper(self, unfinishOper):
        if (unfinishOper in self.__unfinishedOperations):
            context.__unfinishedOperations.remove(unfinishOper)
            
    def needDBRefreshConf(self):
        return const.CLUSTER_REFRESH_CONFIG in self.__unfinishedOperations
    
    def needClearFloatIp(self):
        return const.CLEAR_FLOAT_IP in self.__unfinishedOperations            
    
    def setFloatIpStates(self, floatIpStates):
        self.__floatIpStates = floatIpStates
        
    def setFloatIpState(self, idx, floatIpState):
        while(idx >= len(self.__floatIpStates)):
            self.__floatIpStates.append(const.FLOATIP_NORMAL)
        self.__floatIpStates[idx] = floatIpState
        
    def getFloatIpState(self, idx):
        while(idx >= len(self.__floatIpStates)):
            self.__floatIpStates.append(const.FLOATIP_NORMAL)
        return self.__floatIpStates[idx]
        
    def readConfig(self, fileFullName):      
        self.fileName = os.path.basename(fileFullName)
        self.filePath = os.path.dirname(fileFullName)
        self.fileFullName = fileFullName

        if(not os.path.exists(fileFullName)):
            system_log.info("no status file: %s is existed." % fileFullName)        
            return True
        
        
        self.hasStatusFile = True
        try:
            domTree = parse(fileFullName)
            rootNode = domTree.documentElement
            
            
            unfinished_operation_nodes = rootNode.getElementsByTagName("unfinished_operations")[0].childNodes
            if(len(unfinished_operation_nodes) == 0):
                self.__unfinishedOperations = []
            else:
                unfinished_operations = unfinished_operation_nodes[0].data.split(",")
                arr = list(map(int,unfinished_operations))
                self.__unfinishedOperations = arr
            
            float_ip_state_nodes = rootNode.getElementsByTagName("float_ip_state")[0].childNodes
            if(len(float_ip_state_nodes) == 0):
                self.__floatIpStates = []
            else:                
                float_ip_state = float_ip_state_nodes[0].data.split(",")
                arr = list(map(int,float_ip_state))
                self.__floatIpStates = arr

            system_log.info("load status file: %s succeed." % fileFullName)        
            system_log.info(str(self))

            return True
        except BaseException:
            system_log.error(traceback.format_exc())
            system_log.fatal("load status file: %s failed, system exits." % fileFullName)        
            return False 
            
    def __str__(self):
        
        if(self.hasStatusFile):
            retStr = ("\nunfinishedOperations=%s\nfloatIpState=%s\n") %(
                self.__unfinishedOperations, self.__floatIpStates)           
            return retStr
        else: return "Has not status file"

    def saveToFile(self):
        impl = minidom.getDOMImplementation()
        doc = impl.createDocument(None, None, None)
        root = doc.createElement('Config')
        
        # 每一组信息先创建节点<order>，然后插入到父节点<orderlist>下
        unfinished_operations_comment = doc.createComment(" 1: unfinished float ip opearation, 2: unfinished cluster config refresh")
        root.appendChild(unfinished_operations_comment)

        unfinished_operations = doc.createElement('unfinished_operations')
        unfinished_operations_text = doc.createTextNode(str(self.__unfinishedOperations)[1:-1])
        unfinished_operations.appendChild(unfinished_operations_text)
        root.appendChild(unfinished_operations)

        float_ip_state_comment = doc.createComment("1: normal primary, 0: normal standby, -1: unclear primary floatip")
        root.appendChild(float_ip_state_comment)

        float_ip_state = doc.createElement('float_ip_state')
        float_ip_state_text = doc.createTextNode(str(self.__floatIpStates)[1:-1])
        float_ip_state.appendChild(float_ip_state_text)
        root.appendChild(float_ip_state)
        
        doc.appendChild(root)
        
        # 将dom对象写入本地xml文件
        try:
            tmpFileFullName = self.filePath + os.sep + self.fileName + ".tmp"
            tmpFile = open(tmpFileFullName, 'w')        
            doc.writexml(tmpFile,  addindent="    ", newl='\n', encoding='utf-8')            
                
            if os.path.exists(self.fileFullName + ".bak"):
                os.remove(self.fileFullName + ".bak")
                
            if os.path.exists(self.fileFullName):
                os.renames(self.fileFullName, self.fileFullName + ".bak")
                
            os.renames(tmpFileFullName, self.fileFullName)
                    
        except BaseException:
            system_log.error("Save status file failed\n\%s" % traceback.format_exc())
            return False
        
        return True

context = Context()
