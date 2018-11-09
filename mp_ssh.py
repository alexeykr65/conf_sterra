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
import datetime
import re
import os
import sys
import socket
import getpass
import multiprocessing as mp
import netmiko as nm
from functools import partial

description_argument_parser = "S-Terra: Configure S-Terra, v3.0"
epilog_argument_parser = "Alexey: alexeykr@gmail.ru"

__level_debug__ = int()

__timeout_ssh__ = 10
__name_list_dict__ = ['ip', 'host', 'product', 'customer', 'lic_num', 'lic_code', 'ip_host', 'ip_mask', 'ip_default', 'eth']

__all_config_list_command__ = [
    'lic_mgr show',
    'cat /opt/l2svc/etc/l2.lic',
    'find /opt/l2svc/etc/ -iname "*.conf" -exec echo {} \; -exec cat {} \;',
    'cat /etc/ifaliases.cf',
    'cat /etc/network/interfaces',
    'dp_mgr show'
]


def check_argument_parser():
    log_message(2, "Analyze options ... ")
    parser = argparse.ArgumentParser(description=description_argument_parser, epilog=epilog_argument_parser)
    parser.add_argument('-f', '--file', help='File name input', dest="file_name", default='')
    parser.add_argument('-c', '--command', help='List commands to run', dest="command_run", default='')
    # parser.add_argument('-i', '--init', help='Initialyze S-Terra', dest="init", action="store_true")
    parser.add_argument('-gs', '--getsterra', help='Get All Configs from S-Terra', dest="get_all", action="store_true")
    parser.add_argument('-gc', '--getcscons', help='Get Cscons Sterra config', dest="get_config_cscons", action="store_true")
    parser.add_argument('-gr', '--getrouter', help='Get Cisco router config', dest="get_config_router", action="store_true")
    parser.add_argument('-hi', '--hostip', help='IP address of Hosts', dest="host_ip", default='')
    parser.add_argument('-tm', '--sshtimeout', help='SSH timeout in sec', dest="ssh_timeout", default=10)
    parser.add_argument('-ps', '--passwords', help='Set passwords', dest="passwords", default='')
    # parser.add_argument('-pe', '--passenable', help='Set enable password', dest="get_enable_password", action="store_true")
    parser.add_argument('-pn', '--numpass', help='Number passwords', dest="number_pass", default='')
    parser.add_argument('-np', '--numproc', help='Number processes', dest="number_proc", default=100)
    # parser.add_argument('-od', '--outdir', help='Output dir for writing files', dest="output_dir", default='./output/')
    parser.add_argument('-t', '--testing', help='For testing other features', dest="testing", action="store_true")
    parser.add_argument('-p', '--print', help='Output on screen ', dest="print_onscreen", action="store_true")
    parser.add_argument('-d', '--debug', help='Debug information view(1 - standart, 2 - more verbose)', dest="debug", default=0)
    return parser.parse_args()


def log_message(level_debug, message_log):
    output_dir = "./output/"
    log_output_file = "log_output.txt"
    if __level_debug__ >= level_debug:
        print(message_log)
        id_config_file = open(output_dir + log_output_file, 'a+')
        id_config_file.write(message_log)
        id_config_file.write("\n")
        id_config_file.close()


def get_date():
    '''
    This function returns a tuple of the year, month and day.
    '''
    # Get Date
    now = datetime.datetime.now()
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


def write_to_file_result(pre_name_file, namehost, iphost, write_messsage, flagNewFile=True):
    year, month, day, hour, minute = get_date()
    output_dir = "./output/"
    list_names = [pre_name_file, namehost, iphost, day, month, year, hour, minute + ".txt"]
    file_name = '_'.join(list_names)
    id_config_file = open(output_dir + file_name, 'w')
    id_config_file.write(write_messsage)
    id_config_file.write("\n\n")
    id_config_file.close()


def get_dict_hosts_from_file(name_config_file, device_type='cisco_ios_ssh'):
    dict_hosts_ssh = []
    id_config_file = open(name_config_file, 'r', encoding="utf-8")
    for line_config_file in id_config_file:
        data = dict()
        line_list = list()
        if line_config_file.strip() != '' and not re.search("!", line_config_file):
            line_list = line_config_file.strip().split(';')
            for i in range(0, len(line_list)):
                data[__name_list_dict__[i]] = line_list[i]
            if __name_list_dict__[1] not in data:
                data[__name_list_dict__[1]] = ""
            # data['username'] = 'root'
            # data['password'] = 'cisco'
            data['timeout'] = __timeout_ssh__
            data['device_type'] = device_type
            dict_hosts_ssh.append(data)
    log_message(2, dict_hosts_ssh)
    id_config_file.close()
    return dict_hosts_ssh


def connect_to_host(username, passwords, list_commands, list_devices, flag_emu_cisco=False, flag_cisco=False, prefix_to_write="sterra"):
    proc = os.getpid()
    dict_netmiko = dict()
    dict_netmiko['ip'] = list_devices['ip']
    dict_netmiko['ip'] = list_devices['ip']
    dict_netmiko['device_type'] = list_devices['device_type']
    dict_netmiko['timeout'] = list_devices['timeout']
    dict_netmiko['username'] = username
    hostname = "noname"
    for passw in passwords:
        dict_netmiko['password'] = passw
        # print('Netmiko Dict : {}'.format(dict_netmiko))
        return_message = ""

        try:
            id_ssh = nm.ConnectHandler(**dict_netmiko)
            id_ssh.read_channel()
            find_hostname = id_ssh.find_prompt()
            if not find_hostname:
                time.sleep(0.5)
                find_hostname = id_ssh.find_prompt()

            if flag_cisco:
                hostname = re.match("([^#]*)#", find_hostname).group(1).strip()
            else:
                hostname = re.match("root@([^:]*):~#", find_hostname).group(1).strip()
            
            # log_message(1, 'Find Prompt : {!r}'.format(find_hostname))
            # print('Find Prompt : {!r}'.format(find_hostname))

            # log_message(1, 'Hostname : {!r}'.format(hostname))
            return_message += '!#host:{}:{}\n'.format(list_devices['ip'], hostname)
            print('Process pid: {} Connected to hostname: {} with Ip : {} ... OK'.format(proc, hostname, dict_netmiko['ip']))            
            if flag_emu_cisco:
                cisco_emu_prompt = hostname + "#"
                # log_message(1, 'Cisco Emu prompt: {}'.format(cisco_emu_prompt))
                cmd_return = id_ssh.send_command("su cscons", expect_string=cisco_emu_prompt)
                cmd_return = id_ssh.send_command("terminal length 0", expect_string=cisco_emu_prompt)
                for cmd in list_commands:
                    cmd_return = id_ssh.send_command(cmd, expect_string=cisco_emu_prompt)
                    return_message += cmd_return
                prefix_to_write = "cscons"
            else:
                for cmd in list_commands:
                    # log_message(1, 'Command Send : {!r} '.format(cmd))
                    return_message += '!#cmd:{}\n'.format(cmd)
                    cmd_return = id_ssh.send_command(cmd)
                    return_message += '{}\n'.format(cmd_return)
                    # log_message(1, 'Command Return : \n{} '.format(cmd_return))
            write_to_file_result(prefix_to_write, hostname, dict_netmiko['ip'], return_message)
            return return_message
        except Exception as error:
            # print('{}\n'.format(error))
            return_message += '!#host_error:{}:{}\n'.format(list_devices['ip'], hostname)
            return_message += '{}\n'.format(error)
            if(re.search("timed-out", str(error))):
                # print("Timed-out.....")
                return return_message
            elif(re.search("Authentication fail", str(error))):
                continue
            else:
                return_message += '!#host_error:{}:{}\n'.format(list_devices['ip'], hostname)
                return_message += '{}\n'.format(error)
    return return_message


def analyze_result_for_errors(result):
    print("============================== HOST ERRORS ==============================")
    for rs in result:
        if(re.search('!#host_error', rs)):
            if re.match("!#host_error:(\d*\.\d*\.\d*\.\d*):.*", rs):
                ip_host = re.match("!#host_error:(\d*\.\d*\.\d*\.\d*):.*", rs).group(1)
            if(re.search('Authentication', rs)):
                name_error = "Authentication Failed"
            elif(re.search('timed-out', rs)):
                name_error = "Timed-out"
            else:
                name_error = rs
            print('Host Error: {:15s} - {:s}'.format(ip_host, name_error))
    print("=========================================================================")


if __name__ == '__main__':
    mp.freeze_support()
    start_time = time.time()
    listComm = list()
    username_ssh = "root"
    list_passwords_ssh = list()
    list_dict_hosts_ssh = []
    year, month, day, hour, minute = get_date()
    list_names = ["log_output", day, month, year, hour, minute + ".txt"]
    __log_output_file__ = '-'.join(list_names)
    list_comm = []

    # Disable warning from python
    if not sys.warnoptions:
        import warnings
        warnings.simplefilter("ignore")
    # Parser arguments
    arg = check_argument_parser()
    # Other arguments
    # conf_file_name = arg.file_name
    __level_debug__ = int(arg.debug)
    __timeout_ssh__ = int(arg.ssh_timeout)
    __output_dir__ = "./output/"
    __num_processes_ssh__ = int(arg.number_proc)
    log_message(0, 'Maximum of processes ssh allow : {}'.format(__num_processes_ssh__))
    log_message(0, 'Count CPU : {}'.format(mp.cpu_count()))
    if __num_processes_ssh__ == 0:
        __num_processes_ssh__ = int(mp.cpu_count())*2
        log_message(0, 'Maximum of processes ssh allow : {}'.format(__num_processes_ssh__))

    if arg.number_pass:
        username_ssh = input("Login: ")
        for n in range(int(arg.number_pass)):
            list_passwords_ssh.append(getpass.getpass("Password Number " + str(n + 1) + " :"))    
    elif arg.passwords:
        for n in arg.passwords.split(','):
            list_passwords_ssh.append(n.strip())
    else:
        list_passwords_ssh.append('cisco')

    if not list_passwords_ssh:
        list_passwords_ssh.append(getpass.getpass("Password :"))

    if arg.file_name:
        list_dict_hosts_ssh = get_dict_hosts_from_file(arg.file_name)

    if not list_dict_hosts_ssh:
        log_message(0, "No hosts ip ....")
        exit(1)
    if arg.command_run:
        list_comm = arg.command_run.split(',')
        print("List command to run: \n" + '\n'.join(list_comm))
        # exit(1)
    # =======================================================================
    # Get cisco-like config from sterra
    # =======================================================================    
    if arg.get_config_cscons:
        if len(list_comm) == 0:
            list_comm.append('show run')
        pool = mp.Pool(processes=__num_processes_ssh__, )
        mp_short_connect = partial(connect_to_host, username_ssh, list_passwords_ssh, list_comm, flag_emu_cisco=True)
        result = pool.map(mp_short_connect, list_dict_hosts_ssh)
        pool.close()
        pool.join()
        write_to_file_result("total", "output", "cscons", '\n'.join(result))
        analyze_result_for_errors(result)
    # =======================================================================
    # Get Sterra configs
    # =======================================================================    
    if arg.get_all:
        if len(list_comm) == 0:
            list_comm = __all_config_list_command__
        pool = mp.Pool(processes=__num_processes_ssh__, )
        mp_short_connect = partial(connect_to_host, username_ssh, list_passwords_ssh, list_comm)
        result = pool.map(mp_short_connect, list_dict_hosts_ssh)
        pool.close()
        pool.join()
        write_to_file_result("total", "output", "sterra", '\n'.join(result))
        analyze_result_for_errors(result)
    # =======================================================================        
    # Get Cisco 2911 configs
    # =======================================================================    
    if arg.get_config_router:
        if len(list_comm) == 0:
            list_comm.append('show run')
        pool = mp.Pool(processes=__num_processes_ssh__, )
        mp_short_connect = partial(connect_to_host, username_ssh, list_passwords_ssh, list_comm, flag_cisco=True, prefix_to_write="cisco")
        result = pool.map(mp_short_connect, list_dict_hosts_ssh)
        pool.close()
        pool.join()
        write_to_file_result("total", "output", "cisco", '\n'.join(result))
        analyze_result_for_errors(result)

    # for list_hosts_ssh in list_dict_hosts_ssh:
    #     connect_to_host(username_ssh, list_passwords_ssh, ['show run'], list_hosts_ssh)

    log_message(0, "Script complete successful!")
    log_message(0, 'Running time: {0:.2f} secunds'.format(time.time() - start_time))
    sys.exit(0)
