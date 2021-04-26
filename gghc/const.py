#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# const.py
#     GGHC constant management class
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
#      gghc/const.py
# ----------------------------------------------------------------------------


class _const:
    class ConstError(TypeError):pass
    def __setattr__(self,name,value):
        if name in self.__dict__:
            raise self.ConstError("Can't rebind const (%s)" %name)
        self.__dict__[name]=value
        
const = _const()
const.FLOATIP_NORMAL = 0    # Primary正常浮动IP或Standby无浮动IP
const.STANDBY_UNCLEAR_FLOATIP = -1   # Standby因主备切换，没有清除配置文件的浮动IP

const.CLUSTER_REFRESH_CONFIG = 1
const.CLEAR_FLOAT_IP = 2