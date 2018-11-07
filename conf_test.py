#!/usr/bin/env python3
#
#
import netmiko 
import argparse
import os
import re
import time
import multiprocessing
from datetime import datetime
from netmiko.ssh_exception import NetMikoTimeoutException, NetMikoAuthenticationException
# import logging

# logging.basicConfig(filename='test.log', level=logging.DEBUG)
# logger = logging.getLogger("netmiko")

fileName = ""
flagDebug = 1
flagPrint = False
flagSave = False
flagLoad = False
flagRunConfig = False
listDevices = dict()
__log_output_file__ = "log_output_cisco.txt"
__ssh_timeout__ = 5
__output_dir__ = "output/"
listParamNetmiko = ['device_type', 'ip', 'username', 'password', 'port', 'verbose', 'secret']
commandDefault = "sh version"
grepRunConfig = "sh runn | "

description = "Cisco_Net: Configure cisco devices and get information from it, v1.0"
epilog = "http://ciscoblog.ru\nhttps://github.com/alexeykr65"


def log_message(level_debug, message_log):
    # global __flag_debug__
    if flagDebug > level_debug:
        print(message_log)
        id_config_file = open(__output_dir__ + __log_output_file__, 'a+')
        id_config_file.write(message_log)
        id_config_file.write("\n")
        id_config_file.close()


def GetDate():
    '''
    This function returns a tuple of the year, month and day.
    '''
    # Get Date
    now = datetime.now()
    day = str(now.day)
    month = str(now.month)
    year = str(now.year)
    hour = str(now.hour)
    minute = str(now.minute)

    if len(day) == 1:
        day = '0' + day
    if len(month) == 1:
        month = '0' + month

    return year, month, day, hour, minute


def CmdArgsParser():
    global flagDebug, fileName, commandDefault, flagPrint, flagSave, flagLoad, grepRunConfig
    log_message(0, "Analyze options ... ")
    parser = argparse.ArgumentParser(description=description, epilog=epilog)
    parser.add_argument('-f', '--file', help='File name with cisco devices', dest="fileName", default='cisco_devices.conf')
    parser.add_argument('-d', '--debug', help='Debug information view(default =1, 2- more verbose)', dest="flagDebug", default=1)
    parser.add_argument('-cmd', '--command', help='Get command from routers', dest="command", default="")
    parser.add_argument('-cr', '--runconfig', help='Get running config from routers', dest="runconfig", default="")
    parser.add_argument('-p', '--printdisplay', help='View on screen', action="store_true")
    parser.add_argument('-s', '--savetofile', help='Save to Files', action="store_true")
    parser.add_argument('-l', '--loadfiles', help='Load from Files', action="store_true")

    arg = parser.parse_args()

    flagDebug = int(arg.flagDebug)
    fileName = arg.fileName
    log_message(0, "File config: " + fileName)
    if arg.command:
        commandDefault = arg.command
    if arg.printdisplay:
        flagPrint = True
    if arg.savetofile:
        flagSave = True
    if arg.loadfiles:
        flagLoad = True
    if arg.runconfig:
        commandDefault = grepRunConfig + arg.runconfig


def FileConfigAnalyze():
    global listDevices
    log_message(0, "Analyze source file : " + fileName + " ...")
    if not os.path.isfile(fileName):
        log_message(0, "Configuration File : " + fileName + " does not exist")
        return
    f = open(fileName, 'r')
    countDevices = 0
    for sLine in f:
        if re.match("^\s*$", sLine) or re.match("^#.*", sLine):
            continue
        listDevices[countDevices] = dict({'ip': sLine.split(';')[0].strip()})
        listDevices[countDevices]['device_type'] = "cisco_ios"
        listDevices[countDevices]['username'] = "root"
        listDevices[countDevices]['password'] = "cisco"
        listDevices[countDevices]['secret'] = "cisco"
        countDevices += 1

    f.close()
    log_message(1, str(listDevices))


def getStructureNetmiko(infoDevice):
    resNetmiko = dict()
    for tParam in listParamNetmiko:
        if tParam in infoDevice:
            resNetmiko[tParam] = infoDevice[tParam]
    resNetmiko['timeout'] = __ssh_timeout__
    return resNetmiko


def ConnectToRouter(infoDevice, runCommand, mp_queue):
    return_data = dict()
    proc = os.getpid()
    netmikoInfo = getStructureNetmiko(infoDevice)
    log_message(1, "NetmikoInfo : " + str(netmikoInfo))
    try:
        SSH = netmiko.ConnectHandler(**netmikoInfo)
        SSH.read_channel()
        find_hostname = SSH.find_prompt()
        hostname = re.match("root@([^:]*):~#", find_hostname).group(1).strip()
        print("Hostname : " + hostname)
        new_prompt = hostname + "#"
        commandReturn = SSH.send_command("su cscons", expect_string=new_prompt)
        print("Command return: " + commandReturn)
        commandReturn = SSH.send_command("terminal length 0", expect_string=new_prompt)
        print("Command return: " + commandReturn)
        log_message(0, "Process pid: " + str(proc) + ' Hostname: {0}'.format(hostname) + ' IpDevice: {ip}'.format(**infoDevice))
        if flagLoad:
            # print "Name File: " + infoDevice['conf_file']
            commandReturn = SSH.send_config_from_file(infoDevice['conf_file'])
        else:
            log_message(0, "commandSend : " + str(runCommand))
            commandReturn = SSH.send_command(runCommand, expect_string=new_prompt)
            log_message(1, "commandReturn : " + str(commandReturn))
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print("Cannot connect to ip : " + 'IpDevice: {ip}'.format(**infoDevice))
        print("Error: " + str(e))
        return None
    return_data['{}_{}'.format(infoDevice['ip'], hostname)] = commandReturn
    mp_queue.put(return_data)
    SSH.disconnect()


def main():
    CmdArgsParser()
    FileConfigAnalyze()
    mp_queue = multiprocessing.Queue()
    processes = []
    max_number_processes = multiprocessing.cpu_count() - 2
    print("CPU_COUNT: " + str(max_number_processes))

    print("\nStart time: " + str(datetime.now()))
    for numDevice in listDevices:
        p = multiprocessing.Process(target=ConnectToRouter, args=(listDevices[numDevice], commandDefault, mp_queue))
        processes.append(p)
        p.start()
    results = []
    while any(p.is_alive() for p in processes):
        time.sleep(0.1)
        while not mp_queue.empty():
            results.append(mp_queue.get())

    for p in processes:
        p.join()
    # print(results)
    for listRes in results:
        for res in listRes:
            if flagPrint:
                print("=" * 100)
                print("Router : " + res)
                print(listRes[res])
            if flagSave:
                year, month, day, hour, minute = GetDate()
                # Create Filename
                filebits = [res, "config", day, month, year, hour, minute + ".txt"]
                fileSave = '_'.join(filebits)
                f = open(__output_dir__ + fileSave, 'w')
                f.write(listRes[res])
                f.close()
    print("\nEnd time: " + str(datetime.now()))

if __name__ == '__main__':

    main()
