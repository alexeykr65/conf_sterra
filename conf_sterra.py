#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Configure S-Terra
#
# alexeykr@gmail.com
# coding=utf-8
# import codecs
import argparse
import paramiko
import time
import re
import sys
import socket
import getpass

description_argument_parser = "S-Terra: Configure S-Terra, v1.0"
epilog_argument_parser = "Alexey: alexeykr@gmail.ru"

__flag_debug__ = int()
__ssh_timeout__ = 2

__ssh_passwords_list__ = []
__number_passwords__ = 2
__list_hosts__ = list()
__username_ssh__ = "root"

__all_config_list_command__ = [
    'lic_mgr show',
    'cat /opt/l2svc/etc/*.lic',
    'cat /etc/ifaliases.cf',
    'cat /etc/network/interfaces'
]


def log_message(num_debug, message_log):
    # global __flag_debug__
    if __flag_debug__ >= num_debug:
        print(message_log)


def check_argument_parser():
    log_message(2, "Analyze options ... ")
    parser = argparse.ArgumentParser(description=description_argument_parser, epilog=epilog_argument_parser)
    parser.add_argument('-f', '--file', help='File name input', dest="file_name", default='sterra.conf')
    parser.add_argument('-c', '--command', help='Run command', dest="command_run", default='')
    parser.add_argument('-i', '--init', help='Initialyze S-Terra', dest="init", action="store_true")
    parser.add_argument('-ga', '--getall', help='Get All Configs from S-Terra', dest="get_all", action="store_true")
    parser.add_argument('-hi', '--hostip', help='IP address of Hosts', dest="host_ip", default='')
    parser.add_argument('-tm', '--sshtimeout', help='SSH timeout in sec', dest="ssh_timeout", default=5)
    parser.add_argument('-ps', '--passwords', help='Set passwords', dest="passwords", default='')
    parser.add_argument('-pn', '--numpass', help='Number passwords', dest="number_pass", default='')
    parser.add_argument('-d', '--debug', help='Debug information view(1 - standart, 2 - more verbose)', dest="debug", default=0)

    return parser.parse_args()


def getNamesFromFile(nameFile):
    global __list_hosts__
    f = open(nameFile, 'r')
    for sLine in f:
        log_message(2, sLine)
        if sLine.strip() != '':
            __list_hosts__.append(list(sLine.strip().split(';')))
    f.close()


def runCommands(aCommands, ssh_password, ssh_host_name):
    global __number_passwords__
    try:
        prmCon = paramiko.SSHClient()
        prmCon.load_system_host_keys()
        prmCon.set_missing_host_key_policy(paramiko.WarningPolicy)
        prmCon.connect(ssh_host_name, username=__username_ssh__, password=ssh_password, timeout=__ssh_timeout__)
        chan = prmCon.invoke_shell()
        sResp = ""
        while not re.search("#", sResp):
            while not chan.recv_ready():
                time.sleep(0.05)
            sResp = chan.recv(9999).decode('ascii')
        log_message(1, sResp)
        log_message(1, "Received command promt \'#\': OK")
        buff = ""
        for sComm in aCommands:
            sResp = ""
            buff += "\n!========= " + sComm + " =========\n"
            chan.send(sComm + "\n")
            # dbgLog(0, sComm)
            while not re.search("#", sResp):
                while not chan.recv_ready():
                    time.sleep(0.05)
                sResp = chan.recv(9999).decode('ascii')
                log_message(2, "====" + sResp + "=====")
                buff += sResp
            log_message(1, "Command \'" + sComm + "\' run OK")
        buff += "\n!==================================\n"
        # dbgLog(0, buff)
        cleanBuff(buff)
        # dbgLog(0, buff)
        prmCon.close()

    except paramiko.AuthenticationException:
        print("Authentication problem ...")
        if __number_passwords__ > 1:
            print("Connecting with another password ...")
            __number_passwords__ -= 1
            runCommands(aCommands, __ssh_passwords_list__[len(__ssh_passwords_list__) - __number_passwords__], ssh_host_name)

    except paramiko.SSHException as sshException:
        print("Could not establish SSH connection: %s" % sshException)
    except socket.error as e:
        print("Socket error: ", e)
    else:
        pass
    finally:
        __number_passwords__ = len(__ssh_passwords_list__)
        pass


def cleanBuff(sBuff):
    for s in sBuff.split("\n"):
        if not re.search(":~#", s.strip()):
            log_message(0, s.strip())


def setLicenseSterra(lH):
    global __list_hosts__, __ssh_passwords_list__
    licCommand = "lic_mgr set -p " + lH[2] + " -c " + lH[3] + " -n " + lH[4] + " -l " + lH[5]
    log_message(1, licCommand)
    runCommands(list(licCommand.split(',')), __ssh_passwords_list__[0], lH[0])


def runRND(passW, hostN):
    global hostName, __username_ssh__, __ssh_passwords_list__, __number_passwords__
    rndCommand = "/opt/VPNagent/bin/rnd_mgr -once"
    try:
        log_message(0, "RND host: " + h[0] + " " + h[1])
        prmCon = paramiko.SSHClient()
        prmCon.load_system_host_keys()
        prmCon.set_missing_host_key_policy(paramiko.WarningPolicy)

        prmCon.connect(hostN, username=__username_ssh__, password=passW, timeout=__ssh_timeout__)
        chan = prmCon.invoke_shell()

        sResp = ""
        while not re.search("#", sResp):
            while not chan.recv_ready():
                time.sleep(0.05)
            sResp = chan.recv(9999).decode('ascii')
        log_message(1, sResp)
        log_message(0, "Received command promt \'#\': OK")

        chan.send(rndCommand + "\n")
        while not chan.recv_ready():
            time.sleep(0.05)
        log_message(0, "Command \'" + rndCommand + "\'run OK")
        buff = ""
        sResp = chan.recv(9999).decode('ascii')
        if re.search("Already", sResp):
            buff = "Already initialized RNG."
        while not re.search("#", sResp):
            for sLine in sResp.split("\n"):
                # print (sLine)
                if re.search("Press", sLine):
                    log_message(2, "Character:" + sLine.split(':')[1].strip() + "")
                    chan.send(sLine.split(':')[1].strip())
                    while not chan.recv_ready():
                        time.sleep(0.05)
                    break
            sResp = chan.recv(9999).decode('ascii')
            log_message(1, sResp)
            if re.search("initialized", sResp):
                buff = "Successfully initialized RNG."
        log_message(0, buff)
        prmCon.close()
    except paramiko.AuthenticationException:
        print("Authentication problem ...")
        if __number_passwords__ > 1:
            print("Connecting with another password ...")
            __number_passwords__ -= 1
            runRND(__ssh_passwords_list__[len(__ssh_passwords_list__) - __number_passwords__], hostN)

    except paramiko.SSHException as sshException:
        print("Could not establish SSH connection: %s" % sshException)
    except socket.error as e:
        print("Socket error: ", e)
    else:
        pass
    finally:
        __number_passwords__ = len(__ssh_passwords_list__)


if __name__ == '__main__':
    listComm = list()
    # Disable warning from python
    if not sys.warnoptions:
        import warnings
        warnings.simplefilter("ignore")
# Parser arguments
    arg = check_argument_parser()
    # Other arguments
    # conf_file_name = arg.file_name
    __flag_debug__ = int(arg.debug)
    __ssh_timeout__ = int(arg.ssh_timeout)
    # Filename with hostnames and other information
    if arg.file_name:
        getNamesFromFile(arg.file_name)
    # Set passwords for ssh
    if arg.number_pass:
        for n in range(int(arg.number_pass)):
            __ssh_passwords_list__.append(getpass.get_pass("Password Number " + str(n + 1) + " :"))
        __number_passwords__ = len(__ssh_passwords_list__)
    elif arg.passwords:
        for n in arg.passwords.split(','):
            __ssh_passwords_list__.append(n.strip())
        __number_passwords__ = len(__ssh_passwords_list__)
    else:
        __ssh_passwords_list__.append('cisco')
    log_message(2, "Count pass: " + str(__number_passwords__))
    # Run commands
    if arg.command_run:
        for c in arg.command_run.split(','):
            listComm.append(c)
        for h in __list_hosts__:
            log_message(0, "!----------------------" + h[0] + "(" + h[1] + ")----------------------")
            runCommands(listComm, __ssh_passwords_list__[0], h[0])
    # Run commands for get all configs s-terra
    if arg.get_all:
        for h in __list_hosts__:
            log_message(0, "!----------------------" + h[0] + "(" + h[1] + ")----------------------")
            runCommands(__all_config_list_command__, __ssh_passwords_list__[0], h[0])
    # Run Initialization s-terra
    if arg.init:
        for h in __list_hosts__:
            log_message(0, "!----------------------" + h[0] + "(" + h[1] + ")----------------------")
            runRND(__ssh_passwords_list__[0], h[0])
            setLicenseSterra(h)

    log_message(0, "Script complete successful!!! ")
    sys.exit()
