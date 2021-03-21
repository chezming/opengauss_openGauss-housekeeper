#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# config.py
#     GGHC configuration file management
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
#      gghc/config.py
# ----------------------------------------------------------------------------


from xml.dom.minidom import parse
import traceback
from log import system_log

class Config():
    '''
    classdocs
    '''
    def __init__(self):
        '''
        Constructor
        '''
        pass
    
    def readConfig(self, path):        
        try:
            domTree = parse(path)
            rootNode = domTree.documentElement

            self.dbNodeIps = rootNode.getElementsByTagName("db_listen_addresses")[0].childNodes[0].data.split(",")
            self.dbNodePort = rootNode.getElementsByTagName("db_listen_port")[0].childNodes[0].data
            self.dbDatanodePaths = rootNode.getElementsByTagName("db_datanode_path")[0].childNodes[0].data
            self.dbUser = rootNode.getElementsByTagName("db_user")[0].childNodes[0].data
            self.floatIp = rootNode.getElementsByTagName("float_ip")[0].childNodes[0].data
            self.floatipEth = rootNode.getElementsByTagName("floatip_eth")[0].childNodes[0].data
            self.gghcConnectIp = rootNode.getElementsByTagName("gghc_connect_ip")[0].childNodes[0].data
            self.gghcPrivateKeyFile = rootNode.getElementsByTagName("gghc_private_key_file")[0].childNodes[0].data
            self.gghsAgentPath = rootNode.getElementsByTagName("gghs_agent_path")[0].childNodes[0].data
            self.stateCheckPeriod = rootNode.getElementsByTagName("state_check_period")[0].childNodes[0].data
            self.sshTimeout = rootNode.getElementsByTagName("ssh_timeout")[0].childNodes[0].data
            self.logLevel = rootNode.getElementsByTagName("log_level")[0].childNodes[0].data
            
            system_log.info("load config file %s succeed." % path) 
            system_log.info(str(self))  
            system_log.setLevel((self.logLevel).upper())                 
            return True
        except BaseException:
            system_log.error(traceback.format_exc())
            system_log.fatal("load config file %s failed, system exits." % path)            
            return False
        
    def __str__(self):
        resStr = ("\ndbNodeIps=%s\ndbNodePort=%s\ndbDatanodePaths=%s\ndbUser=%s\nfloatIp=%s"
                  "\nfloatipEth=%s\ngghcConnectIp=%s\ngghcPrivateKeyFile=%s"
                  "\ngghsAgentPath=%s\nstateCheckPeriod=%s\nsshTimeout=%s\nlogLevel=%s") % (
                   self.dbNodeIps, self.dbNodePort, self.dbDatanodePaths,
                   self.dbUser, self.floatIp, self.floatipEth,
                   self.gghcConnectIp, self.gghcPrivateKeyFile, self.gghsAgentPath,
                   self.stateCheckPeriod, self.sshTimeout, self.logLevel
                   )
        return resStr
    
config = Config()