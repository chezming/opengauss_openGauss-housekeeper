#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sshclient.py
#     GGHC remote SSH connection communication class
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

import paramiko
import traceback
from log import system_log
from config import config


class SSH_Client():
    def __init__(self, host, username, private_key_file, port=22):
        self.host = host
        self.username = username
        self.private_key_file = private_key_file
        self.port = port
        self.ssh = None

    def connect(self, nodeId):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key = paramiko.RSAKey.from_private_key_file(self.private_key_file)
            self.ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                pkey=key,
                timeout=10)
            return True
        except BaseException:
            system_log.fatal("nodeId %d, %s" % (nodeId + 1, traceback.format_exc()))
            return False

    def execute(self, sshClients, nodeId, execmd, params=[]):
        revc_str = ""
        cmdLine = "%s %s" % (config.gghsAgentPath, execmd)
        for p in params:
            cmdLine = "%s %s" % (cmdLine, p)

        system_log.debug("Send request to nodeId %d: \n%s" % ((nodeId + 1), cmdLine))
        try:

            _, stdout, _ = self.ssh.exec_command(cmdLine, timeout=int(config.sshTimeout), get_pty=True)
            for info in stdout.readlines():
                revc_str += info
        except BaseException:
            self.close()
            sshClients[nodeId] = None
            system_log.fatal("The network card may be failure in the connection of nodeId %d at sending '%s'.\n%s"
                             % ((nodeId + 1), execmd, traceback.format_exc()))
            return (False, traceback.format_exc())

        system_log.debug("Receive Response from nodeId %d: \n>>>>>>>>>>\n%s<<<<<<<<<<\n" % ((nodeId + 1), revc_str))
        return (True, revc_str)

    def close(self):
        self.ssh.close()
