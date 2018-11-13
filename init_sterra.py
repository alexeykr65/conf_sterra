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
import sys
import socket
import getpass
import os

description_argument_parser = "S-Terra: Configure S-Terra, v3.0"
epilog_argument_parser = "Alexey: alexeykr@gmail.ru"

__level_debug__ = int()

__timeout_ssh__ = 5
__list_passwords_ssh__ = []
__list_passwords_enable__ = ['csp']
__number_passwords_ssh__ = 2
__flag_print_onscreen__ = False
__log_output_file__ = "log_output"
__license_hosts_dict__ = dict()
__name_hosts_dict__ = dict()
__cscons_hosts_dict__ = dict()

__list_hosts_ssh__ = []
__dict_hosts_ssh__ = []
__username_ssh__ = "root"
__password_ssh__ = "cisco"
__output_dir__ = ""
__name_license_dict__ = ['cust_code_rvpn', 'prod_code_rvpn', 'lic_num_rvpn', 'lic_code_rvpn', 'cust_code_l2vpn', 'prod_code_l2vpn', 'lic_num_l2vpn', 'lic_code_l2vpn']
__all_config_list_command__ = [
    'lic_mgr show',
    'cat /opt/l2svc/etc/l2.lic',
    'find /opt/l2svc/etc/ -iname "*.conf" -exec echo {} \; -exec cat {} \;',
    'cat /etc/ifaliases.cf',
    'cat /etc/network/interfaces',
    'dp_mgr show'
]

__init_ifaliases_file__ = 'integr_mgr calc -f /etc/ifaliases.cf'
__init_default_vpngate__ = "/bin/sed -i --follow-symlinks 's/VPNGATE_CONFIGURED=no/VPNGATE_CONFIGURED=yes/' /etc/default/vpngate"
__init_conf_forwarding_network__ = "/bin/sed -i --follow-symlinks 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf"
__vpndrv_start_services_sterra__ = 'service vpndrv start'
__vpnlog_start_services_sterra__ = 'service vpnlog  start'
__vpngate_start_services_sterra__ = 'service vpngate start'
__check_list_services_sterra__ = [
    'cat /etc/sysctl.conf  | grep -i forwar',
    '/opt/VPNagent/bin/rnd_test',
    'cat /etc/default/vpngate',
    '/usr/bin/lic_mgr show'
]
__init_commands__ = []


def check_argument_parser():
    log_message(2, "Analyze options ... ")
    parser = argparse.ArgumentParser(description=description_argument_parser, epilog=epilog_argument_parser)
    parser.add_argument('-f', '--file', help='File name input', dest="file_name", default='')
    parser.add_argument('-c', '--command', help='Run commands', dest="command_run", default='')
    parser.add_argument('-i', '--init', help='Initialyze S-Terra', dest="init", action="store_true")
    parser.add_argument('-hi', '--hostip', help='IP address of Hosts', dest="host_ip", default='')
    parser.add_argument('-tm', '--sshtimeout', help='SSH timeout in sec', dest="ssh_timeout", default=2)
    parser.add_argument('-ps', '--passwords', help='Set passwords', dest="passwords", default='')
    parser.add_argument('-id', '--inputdir', help='Input dir for init S-Terra', dest="input_dir", default='./input/')
    # parser.add_argument('-p', '--print', help='Output on screen ', dest="print_onscreen", action="store_true")
    parser.add_argument('-d', '--debug', help='Debug information view(1 - standart, 2 - more verbose)', dest="debug", default=0)

    return parser.parse_args()


def log_message(level_debug, message_log):
    # global __flag_debug__
    if __level_debug__ >= level_debug:
        print(message_log)
        id_config_file = open(__output_dir__ + __log_output_file__, 'a+')
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

    list_names = [pre_name_file, namehost, iphost, day, month, year, hour, minute + ".txt"]
    file_name = '_'.join(list_names)
    id_config_file = open(__output_dir__ + file_name, 'w')
    id_config_file.write(write_messsage)
    if __flag_print_onscreen__:
        # print("\n!--------------------------Output-----------------------------\n")
        print(write_messsage)
    id_config_file.write("\n\n")
    id_config_file.close()


def get_license_hosts_from_file(name_config_file):
    global __license_hosts_dict__
    print('License file: {}'.format(name_config_file))
    lic_dict = dict()
    id_config_file = open(name_config_file, 'r', encoding="utf-8")
    for line_config_file in id_config_file:
        data = dict()
        line_list = list()
        if line_config_file.strip() != '' and not re.search("!", line_config_file):
            line_list = line_config_file.strip().split(';')
            for i in range(2, len(line_list)):
                data[__name_license_dict__[i-2]] = line_list[i]
            __license_hosts_dict__[line_list[0]] = data
    log_message(2, __license_hosts_dict__)
    id_config_file.close()


def get_dict_hosts_from_file(name_config_file):
    global __name_hosts_dict__
    id_config_file = open(name_config_file, 'r', encoding="utf-8")
    for line_config_file in id_config_file:
        data = dict()
        line_list = list()
        if line_config_file.strip() != '' and not re.search("!", line_config_file):
            line_list = line_config_file.strip().split(';')
            __name_hosts_dict__[line_list[0].strip()] = line_list[1].strip()

    log_message(2, __name_hosts_dict__)
    id_config_file.close()


def get_dict_cscons_config_from_file(ip_hosts, in_dir):
    global __cscons_hosts_dict__, __name_hosts_dict__

    for ip_host in ip_hosts:
        name_config_file = '{}cscons_{}_{}.txt'.format(in_dir, __name_hosts_dict__[ip_host], ip_host)
        # id_config_file = open(name_config_file, 'r', encoding="utf-8")
        list_all_line = [line_file.strip() for line_file in open(name_config_file, 'r') if line_file.strip() != '' and not re.search("#", line_file)]
        #        if line_config_file.strip() != '' and not re.search("!", line_config_file):
        __cscons_hosts_dict__[ip_host] = list_all_line
        __cscons_hosts_dict__[ip_host].insert(0, 'conf t')
        __cscons_hosts_dict__[ip_host].append('show load-message')
        # config_cscons = read
        # for line_config_file in id_config_file:
        #     data = dict()
        #     line_list = list()
        #     if line_config_file.strip() != '' and not re.search("!", line_config_file):
        #         line_list = line_config_file.strip().split(';')
        #         __name_hosts_dict__[line_list[0].strip()] = line_list[1].strip()

    log_message(2, __name_hosts_dict__)
    # id_config_file.close()


def get_hostname(password_ssh, ip_host_ssh):
    run_hostname_command = ['hostname']
    hostname = ""
    tmp_buff = ""
    tmp_buff = cmd_run_command(run_hostname_command, password_ssh, ip_host_ssh)
    log_message(2, "tmp_buff for ip : " + ip_host_ssh + "  include: " + tmp_buff)
    for line_hostname in tmp_buff.split("\n"):
        # or (not re.search('#', line_hostname))
        if not re.search("hostname|#|!-", line_hostname):
            if line_hostname.strip():
                hostname += line_hostname
                # print("line_hostname: " + line_hostname)
    return hostname


def cmd_run_command(run_commands, password_ssh, ip_host_ssh):
    global __number_passwords_ssh__
    log_buff = ""
    try:
        id_conn_paramiko = paramiko.SSHClient()
        #id_conn_paramiko.load_system_host_keys()
        id_conn_paramiko.set_missing_host_key_policy(paramiko.WarningPolicy)
        id_conn_paramiko.connect(ip_host_ssh, username=__username_ssh__, password=password_ssh, timeout=__timeout_ssh__)
        chan = id_conn_paramiko.invoke_shell()
        resp_ssh = ""
        while not re.search("#", resp_ssh):
            while not chan.recv_ready():
                time.sleep(0.05)
            resp_ssh = chan.recv(9999).decode('ascii')
        log_message(1, resp_ssh)
        log_message(1, "Received command promt \'#\': OK")
        for str_command in run_commands:
            resp_ssh = ""
            log_buff += "\n!-----------------------------------------------------------\n"
            chan.send(str_command + "\n")
            while not re.search("#", resp_ssh):
                while not chan.recv_ready():
                    time.sleep(0.05)
                resp_ssh = chan.recv(9999).decode('ascii')
                log_message(2, "====" + resp_ssh + "=====")
                log_buff += resp_ssh
            log_message(1, "Command \'" + str_command + "\' run OK")
        log_buff += "\n!-----------------------------------------------------------\n"

    except paramiko.AuthenticationException:
        log_message(0, "Authentication problem with host ip: " + ip_host_ssh + " ... access denied")
        if __number_passwords_ssh__ > 1:
            log_message(0, "Connecting with another password ...")
            __number_passwords_ssh__ -= 1
            id_conn_paramiko.close()
            log_buff = cmd_run_command(run_commands, __list_passwords_ssh__[len(__list_passwords_ssh__) - __number_passwords_ssh__], ip_host_ssh)

    except paramiko.SSHException as sshException:
        log_message(0, "Could not establish SSH connection with host ip: " + ip_host_ssh + " : " + str(sshException))
    except socket.error as e:
        log_message(0, "Socket error with host ip: " + ip_host_ssh + " : " + str(e))
    else:
        log_message(0, "Connected ... OK")
        __number_passwords_ssh__ = len(__list_passwords_ssh__)
    finally:
        id_conn_paramiko.close()
        return log_buff


def set_license_sterra(ip_host, info_host_ssh):
    lic_command = []
    lic_command.append(' lic_mgr set -p {prod_code_rvpn:s} -c {cust_code_rvpn:s} -n  {lic_num_rvpn:s}  -l {lic_code_rvpn:s}'.format_map(info_host_ssh))
    lic_command.append('cat <<EOF> /opt/l2svc/etc/l2.lic\n[license]\nCustomerCode={cust_code_l2vpn:s}\nProductCode={prod_code_l2vpn:s}\nLicenseNumber={lic_num_l2vpn:s}\nLicenseCode={lic_code_l2vpn}\nEOF\n'.format_map(info_host_ssh))
    lic_command.append('/opt/l2svc/bin/l2svc --license')

#    log_message(0, lic_command)
    log_buff = cmd_run_command(lic_command, __password_ssh__, ip_host)
    if re.search("Wrong", log_buff):
        log_message(0, "Wrong license !!!!!")
        log_message(0, log_buff)
    else:
        log_message(0, "Licenses installed ... OK")


def csconsole_run_command(run_commands, password_ssh, ip_host_ssh):
    global __number_passwords_ssh__
    csconsole_command = "su cscons"
    enable_command = "enable"
    null_terminal_length_command = "terminal length 0"
    log_buff = ""
    log_message(0, "run_cs_console_command ..")
    # print(run_commands)
    try:
        log_message(1, "Try to connect host: " + ip_host_ssh)
        id_conn_paramiko = paramiko.SSHClient()
        # id_conn_paramiko.load_system_host_keys()
        id_conn_paramiko.set_missing_host_key_policy(paramiko.WarningPolicy)

        id_conn_paramiko.connect(ip_host_ssh, username=__username_ssh__, password=password_ssh, timeout=__timeout_ssh__)
        chan = id_conn_paramiko.invoke_shell()

        resp_ssh = ""
        log_message(1, "Connected to host : " + ip_host_ssh)
        while not re.search("#", resp_ssh):
            while not chan.recv_ready():
                time.sleep(0.05)
            resp_ssh = chan.recv(9999).decode('ascii')
        log_message(2, resp_ssh)
        log_message(1, "Received command promt \'#\': OK")

        chan.send(csconsole_command + "\n")
        resp_ssh = ""
        while not re.search("#", resp_ssh):
            while not chan.recv_ready():
                time.sleep(0.05)
            resp_ssh = chan.recv(9999).decode('ascii')
            if re.search("Could not establish", resp_ssh):
                log_message(0, "ERROR: Could not establish connection with daemon on host: " + ip_host_ssh)
                log_message(0, "Return without cisco configuration ...  ")
                return log_buff
            log_message(2, resp_ssh)
        log_message(1, "Command \'" + csconsole_command + "\'run OK")

        log_message(1, "Run null terminal length")
        chan.send(null_terminal_length_command + "\n")
        resp_ssh = ""
        while not re.search("#", resp_ssh):
            while not chan.recv_ready():
                time.sleep(0.05)
            resp_ssh = chan.recv(9999).decode('ascii')
            log_message(2, resp_ssh)
        log_message(1, "Command \'" + null_terminal_length_command + "\' run OK")

        for run_command in run_commands:
            chan.send(run_command + "\n")
            resp_ssh = ""
            while not re.search("#", resp_ssh):
                while not chan.recv_ready():
                    time.sleep(0.05)
                resp_ssh = chan.recv(9999).decode('ascii')
                log_buff += resp_ssh
                
                if re.search("Invalid", resp_ssh):
                    log_message(1, resp_ssh)
                log_message(1, resp_ssh)
            log_message(1, "Command \'" + run_command + "\' run OK")
            log_message(1, resp_ssh)
        log_message(0, log_buff)

    except paramiko.AuthenticationException:
        log_message(0, "Authentication problem with host ip: " + ip_host_ssh + " ... access denied")
        if __number_passwords_ssh__ > 1:
            log_message(0, "Connecting with another password ...")
            __number_passwords_ssh__ -= 1
            log_buff = csconsole_run_command(run_commands, __list_passwords_ssh__[len(__list_passwords_ssh__) - __number_passwords_ssh__], ip_host_ssh)

    except paramiko.SSHException as sshException:
        log_message(0, "Could not establish SSH connection: " + str(sshException))
        __number_passwords_ssh__ = len(__list_passwords_ssh__)
    except socket.error as e:
        log_message(0, "Socket error: " + str(e))
    else:
        log_message(0, "Connected ... OK")
        __number_passwords_ssh__ = len(__list_passwords_ssh__)
    finally:
        id_conn_paramiko.close()
        return log_buff


def rnd_run_command(password_ssh, ip_host_ssh):
    global __number_passwords_ssh__
    rnd_command = "/opt/VPNagent/bin/rnd_mgr -once"
    log_buff = ""
    try:
        # log_message(0, "RND host: " + h[0] + " " + h[1])
        id_conn_paramiko = paramiko.SSHClient()
        # id_conn_paramiko.load_system_host_keys()
        id_conn_paramiko.set_missing_host_key_policy(paramiko.WarningPolicy)

        id_conn_paramiko.connect(ip_host_ssh, username=__username_ssh__, password=password_ssh, timeout=__timeout_ssh__)
        chan = id_conn_paramiko.invoke_shell()

        resp_ssh = ""
        while not re.search("#", resp_ssh):
            while not chan.recv_ready():
                time.sleep(0.09)
            resp_ssh = chan.recv(9999).decode('ascii')
        log_message(1, resp_ssh)
        log_message(0, "Received command promt \'#\': OK")

        chan.send(rnd_command + "\n")
        while not chan.recv_ready():
            time.sleep(0.05)
        log_message(0, "Command \'" + rnd_command + "\'run OK")
        log_buff = ""
        resp_ssh = chan.recv(9999).decode('ascii')
        if re.search("Already", resp_ssh):
            log_buff = "Already initialized RNG."
        while not re.search("#", resp_ssh):
            for line_resp_ssh in resp_ssh.split("\n"):
                # print (sLine)
                if re.search("Press", line_resp_ssh):
                    log_message(0, "Character:" + line_resp_ssh.split(':')[1].strip() + "")
                    chan.send(line_resp_ssh.split(':')[1].strip())
                    while not chan.recv_ready():
                        time.sleep(0.09)
                    break
            resp_ssh = chan.recv(9999).decode('ascii')
            log_message(0, resp_ssh)
            if re.search("initialized", resp_ssh):
                log_buff = "Successfully initialized RNG."
        log_message(0, log_buff)
        id_conn_paramiko.close()
    except paramiko.AuthenticationException:
        log_message(0, "Authentication problem ...")
        if __number_passwords_ssh__ > 1:
            log_message(0, "Connecting with another password ...")
            __number_passwords_ssh__ -= 1
            rnd_run_command(__list_passwords_ssh__[len(__list_passwords_ssh__) - __number_passwords_ssh__], ip_host_ssh)

    except paramiko.SSHException as sshException:
        log_message(0, "Could not establish SSH connection: " + str(sshException))
    except socket.error as e:
        log_message(0, "Socket error: " + str(e))
    else:
        log_message(0, "Connected ... OK")
        __number_passwords_ssh__ = len(__list_passwords_ssh__)
    finally:
        id_conn_paramiko.close()
        return log_buff


if __name__ == '__main__':
    listComm = list()
    year, month, day, hour, minute = get_date()
    list_names = ["log_output", day, month, year, hour, minute + ".txt"]
    __log_output_file__ = '-'.join(list_names)
    ip_host_ssh = []

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
    input_dir = arg.input_dir
    license_name_file = "list_license.txt"
    hosts_name_file = "hosts-sterra.txt"
    # Filename with hostnames and other information
    get_license_hosts_from_file(input_dir + license_name_file)
    get_dict_hosts_from_file(input_dir + hosts_name_file)

    # print(__license_hosts_dict)
    if arg.host_ip:
        ip_host_ssh = [x.strip() for x in arg.host_ip.split(',')]
    else:
        print("Need ip host ...programm exit")
        exit(1)
    get_dict_cscons_config_from_file(ip_host_ssh, input_dir)
    # print(__cscons_hosts_dict__)
    # exit()
    # Run Initialization s-terra
    if arg.init:
        __init_commands__.append(__init_ifaliases_file__)
        __init_commands__.append(__init_default_vpngate__)
        __init_commands__.append(__init_conf_forwarding_network__)
        __init_commands__.append(__vpndrv_start_services_sterra__)
        __init_commands__.append(__vpnlog_start_services_sterra__)
        __init_commands__.append(__vpngate_start_services_sterra__)
        __init_commands__.append('rm /etc/rc.local.inc ')
        __init_commands__.append('')

        log_message(2, __init_commands__)

        for h in ip_host_ssh:
            # print(__init_commands__)
            ret_log_buff = ""
            tmp_ret_log_buff = ""
            log_message(0, "!=======================================================================")
            log_message(0, '++++++++++++++++++++ {} ({}) ++++++++++++++++++++'.format(h, __name_hosts_dict__[h]))
            log_message(0, "+++++++++++++++++++ Run initializing RND +++++++++++++++++++  ")
            ret_log_buff = rnd_run_command(__password_ssh__, h)
            tmp_ret_log_buff += ret_log_buff
            log_message(0, ret_log_buff)
            reset_screen = '\033[0;0m'
            # print(reset_screen)
            os.system('/usr/bin/reset')
            time.sleep(5)
            log_message(0, "++++++++++++++++++++++++ Set license ++++++++++++++++++++++++ ")
            set_license_sterra(h, __license_hosts_dict__[h])
            log_message(0, "++++++++++++++++++++++++ Init S-Terra System ++++++++++++++++++++++++ ")
            ret_log_buff = cmd_run_command(__init_commands__, __password_ssh__, h)
            tmp_ret_log_buff += ret_log_buff
            log_message(0, ret_log_buff)
            time.sleep(30)
            cscons_commands = __cscons_hosts_dict__[h]
            log_message(0, "++++++++++++++++++++++++ Load Cscons Configuration ++++++++++++++++++++++++ ")
            ret_log_buff = csconsole_run_command(cscons_commands, __password_ssh__, h)
            tmp_ret_log_buff += ret_log_buff
            time.sleep(10)
            log_message(0, "++++++++++++++++++++++++ Reboot System ++++++++++++++++++++++++ ")
            reboots_commands = ['sed -i \'s/=7/=9/\' /etc/modprobe.d/vpndrvr.conf', 'reboot']
            ret_log_buff = cmd_run_command(reboots_commands, __password_ssh__, h)
            tmp_ret_log_buff += ret_log_buff
            log_message(0, ret_log_buff)

            # log_message(0, ret_log_buff)
            # if ret_log_buff:
            #      write_to_file_result("initialize", h['host'], h['ip'], tmp_ret_log_buff)

    log_message(0, "Script complete successful!!! ")
    sys.exit()
