#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GGHC.py
#     GGHC system operation entry class
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
#      gghc/GGHC.py
# ----------------------------------------------------------------------------

import os
from config import config
from context import context
from log import system_log

from checker import ClusterStateChecker

if __name__ == "__main__":
    workDir = os.getcwd()
    confPath = "%s/../conf/config.xml" % workDir
    contextPath = "%s/../conf/status.xml" % workDir
    
    print("system begin to start...")
    
    if(not config.readConfig(confPath)):
        print("system stop for reading %s." % confPath)
        os._exit(-1)
        
    if(not context.readConfig(contextPath)):
        print("system stop for reading %s." % contextPath)
        os._exit(-1)
        
    checker = ClusterStateChecker()
    checker.check()
    
