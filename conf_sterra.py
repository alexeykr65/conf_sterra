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

description = "S-Terra: Configure S-Terra, v1.0"
epilog = "Alexey: alexeykr@gmail.ru"

flagDebug = int()
fileName = ""
fileNameOut = ""
sshTimeout = 2

passWords = []
flagCountPassword = 2
listHosts = list()

userName = "root"
listCommSterraAllConfig = [
    'lic_mgr show',
    'cat /opt/l2svc/etc/*.lic',
    'cat /etc/ifaliases.cf',
    'cat /etc/network/interfaces'
]


def dbgLog(flagD, strO):
    global flagDebug
    if flagDebug >= flagD:
        print(strO)


def cmdArgsParser():
    dbgLog(2, "Analyze options ... ")
    parser = argparse.ArgumentParser(description=description, epilog=epilog)
    parser.add_argument('-f', '--file', help='File name input', dest="fileName", default='sterra.conf')
    parser.add_argument('-c', '--command', help='Run command', dest="commandRun", default='')
    parser.add_argument('-i', '--init', help='Initialyze S-Terra', dest="init", action="store_true")
    parser.add_argument('-ga', '--getall', help='Get All Configs from S-Terra', dest="getall", action="store_true")
    parser.add_argument('-hi', '--hostip', help='IP address of Hosts', dest="hostip", default='')
    parser.add_argument('-tm', '--sshtimeout', help='SSH timeout in sec', dest="sshtimeout", default=5)
    parser.add_argument('-ps', '--passwords', help='Set passwords', dest="passwords", default='')
    parser.add_argument('-pn', '--numpass', help='Number passwords', dest="numpass", default='')
    parser.add_argument('-d', '--debug', help='Debug information view(1 - standart, 2 - more verbose)', dest="Debug", default=0)

    return parser.parse_args()


def getNamesFromFile(nameFile):
    global listHosts
    f = open(nameFile, 'r')
    for sLine in f:
        dbgLog(2, sLine)
        if sLine.strip() != '':
            listHosts.append(list(sLine.strip().split(';')))
    f.close()


def runCommands(aCommands, passW, hostN):
    global fileName, userName, sshTimeout, passWords, flagCountPassword
    try:
        prmCon = paramiko.SSHClient()
        prmCon.load_system_host_keys()
        prmCon.set_missing_host_key_policy(paramiko.WarningPolicy)
        prmCon.connect(hostN, username=userName, password=passW, timeout=sshTimeout)
        chan = prmCon.invoke_shell()
        sResp = ""
        while not re.search("#", sResp):
            while not chan.recv_ready():
                time.sleep(0.05)
            sResp = chan.recv(9999).decode('ascii')
        dbgLog(1, sResp)
        dbgLog(1, "Received command promt \'#\': OK")
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
                dbgLog(2, "====" + sResp + "=====")
                buff += sResp
            dbgLog(1, "Command \'" + sComm + "\' run OK")
        buff += "\n!==================================\n"
        # dbgLog(0, buff)
        cleanBuff(buff)
        # dbgLog(0, buff)
        prmCon.close()

    except paramiko.AuthenticationException:
        print("Authentication problem ...")
        if flagCountPassword > 1:
            print("Connecting with another password ...")
            flagCountPassword -= 1
            runCommands(aCommands, passWords[len(passWords) - flagCountPassword], hostN)

    except paramiko.SSHException as sshException:
        print("Could not establish SSH connection: %s" % sshException)
    except socket.error as e:
        print("Socket error: ", e)
    else:
        pass
    finally:
        flagCountPassword = len(passWords)
        pass


def cleanBuff(sBuff):
    for s in sBuff.split("\n"):
        if not re.search(":~#", s.strip()):
            dbgLog(0, s.strip())


def setLicenseSterra(lH):
    global listHosts, passWords
    licCommand = "lic_mgr set -p " + lH[2] + " -c " + lH[3] + " -n " + lH[4] + " -l " + lH[5]
    dbgLog(1, licCommand)
    runCommands(list(licCommand.split(',')), passWords[0], lH[0])


def runRND(passW, hostN):
    global fileName, hostName, userName, passWords, flagCountPassword
    rndCommand = "/opt/VPNagent/bin/rnd_mgr -once"
    try:
        dbgLog(0, "RND host: " + h[0] + " " + h[1])
        prmCon = paramiko.SSHClient()
        prmCon.load_system_host_keys()
        prmCon.set_missing_host_key_policy(paramiko.WarningPolicy)

        prmCon.connect(hostN, username=userName, password=passW, timeout=sshTimeout)
        chan = prmCon.invoke_shell()

        sResp = ""
        while not re.search("#", sResp):
            while not chan.recv_ready():
                time.sleep(0.05)
            sResp = chan.recv(9999).decode('ascii')
        dbgLog(1, sResp)
        dbgLog(0, "Received command promt \'#\': OK")

        chan.send(rndCommand + "\n")
        while not chan.recv_ready():
            time.sleep(0.05)
        dbgLog(0, "Command \'" + rndCommand + "\'run OK")
        buff = ""
        sResp = chan.recv(9999).decode('ascii')
        if re.search("Already", sResp):
            buff = "Already initialized RNG."
        while not re.search("#", sResp):
            for sLine in sResp.split("\n"):
                # print (sLine)
                if re.search("Press", sLine):
                    dbgLog(2, "Character:" + sLine.split(':')[1].strip() + "")
                    chan.send(sLine.split(':')[1].strip())
                    while not chan.recv_ready():
                        time.sleep(0.05)
                    break
            sResp = chan.recv(9999).decode('ascii')
            dbgLog(1, sResp)
            if re.search("initialized", sResp):
                buff = "Successfully initialized RNG."
        dbgLog(0, buff)
        prmCon.close()
    except paramiko.AuthenticationException:
        print("Authentication problem ...")
        if flagCountPassword > 1:
            print("Connecting with another password ...")
            flagCountPassword -= 1
            runRND(passWords[len(passWords) - flagCountPassword], hostN)

    except paramiko.SSHException as sshException:
        print("Could not establish SSH connection: %s" % sshException)
    except socket.error as e:
        print("Socket error: ", e)
    else:
        pass
    finally:
        flagCountPassword = len(passWords)


if __name__ == '__main__':
    listComm = list()
    # Disable warning from python
    if not sys.warnoptions:
        import warnings
        warnings.simplefilter("ignore")
# Parser arguments
    arg = cmdArgsParser()
    # Other arguments
    fileName = arg.fileName
    flagDebug = int(arg.Debug)
    sshTimeout = int(arg.sshtimeout)
    # Filename with hostnames and other information
    if arg.fileName:
        getNamesFromFile(arg.fileName)
    # Set passwords for ssh
    if arg.numpass:
        for n in range(int(arg.numpass)):
            passWords.append(getpass.getpass("Password Number " + str(n + 1) + " :"))
        flagCountPassword = len(passWords)
    elif arg.passwords:
        for n in arg.passwords.split(','):
            passWords.append(n.strip())
        flagCountPassword = len(passWords)
    else:
        passWords.append('cisco')
    dbgLog(2, "Count pass: " + str(flagCountPassword))
    # Run commands
    if arg.commandRun:
        for c in arg.commandRun.split(','):
            listComm.append(c)
        for h in listHosts:
            dbgLog(0, "!----------------------" + h[0] + "(" + h[1] + ")----------------------")
            runCommands(listComm, passWords[0], h[0])
    # Run commands for get all configs s-terra
    if arg.getall:
        for h in listHosts:
            dbgLog(0, "!----------------------" + h[0] + "(" + h[1] + ")----------------------")
            runCommands(listCommSterraAllConfig, passWords[0], h[0])
    # Run Initialization s-terra
    if arg.init:
        for h in listHosts:
            dbgLog(0, "!----------------------" + h[0] + "(" + h[1] + ")----------------------")
            runRND(passWords[0], h[0])
            setLicenseSterra(h)

    dbgLog(0, "Script complete successful!!! ")
    sys.exit()
