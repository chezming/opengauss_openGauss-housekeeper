#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# log.py
#     GGHC log file definition class
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
#      gghc/log.py
# ----------------------------------------------------------------------------

import logging
import os
from logging.handlers import RotatingFileHandler

workDir = os.getcwd()

__log_path__ = "%s/../log" % workDir


if not os.path.exists(__log_path__):
    os.makedirs(__log_path__)

#file_handle = logging.FileHandler('%s/system.log'%__log_path__, mode='a', encoding='utf-8')
file_handle = RotatingFileHandler('%s/system.log'%__log_path__,  
            mode='a', encoding='utf-8',
            maxBytes=10*1024*1024, 
            backupCount=5, 
           ) 

file_handle.setFormatter(logging.Formatter(
    fmt='%(asctime)s - %(levelname)s:[%(filename)s(%(lineno)d)] %(message)s',))
file_handle.setLevel(logging.DEBUG)


system_log = logging.Logger('system')
system_log.addHandler(file_handle)


#file_handle2 = logging.FileHandler('%s/state.log'%__log_path__, 'a', encoding='utf-8')
file_handle2 = RotatingFileHandler('%s/state.log'%__log_path__, 
            mode='a', encoding='utf-8',
            maxBytes=5*1024*1024, 
            backupCount=2, 
           ) 
file_handle2.setFormatter(logging.Formatter(
    fmt='%(asctime)s \n%(message)s',))

state_log = logging.Logger('state')
state_log.addHandler(file_handle2)
