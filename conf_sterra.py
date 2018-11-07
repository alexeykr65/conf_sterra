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

description_argument_parser = "S-Terra: Configure S-Terra, v3.0"
epilog_argument_parser = "Alexey: alexeykr@gmail.ru"

__level_debug__ = int()

__timeout_ssh__ = 5
__list_passwords_ssh__ = []
__list_passwords_enable__ = ['csp']
__number_passwords_ssh__ = 2
__flag_print_onscreen__ = False
__log_output_file__ = "log_output"

__list_hosts_ssh__ = []
__dict_hosts_ssh__ = []
__username_ssh__ = "root"
__output_dir__ = ""
__name_list_dict__ = ['ip', 'host', 'product', 'customer', 'lic_num', 'lic_code', 'ip_host', 'ip_mask', 'ip_default', 'eth']
__all_config_list_command__ = [
    'lic_mgr show',
    'cat /opt/l2svc/etc/l2.lic',
    'find /opt/l2svc/etc/ -iname "*.conf" -exec echo {} \; -exec cat {} \;',
    'cat /etc/ifaliases.cf',
    'cat /etc/network/interfaces',
    'dp_mgr show'
]

__ifaliases_file_ = [
    'cat << EOF > /etc/ifaliases.cf',
    'interface (name="GigabitEthernet0/0" pattern="eth0")',
    'interface (name="GigabitEthernet0/1" pattern="eth1")',
    'interface (name="GigabitEthernet0/2" pattern="eth2")',
    'interface (name="default" pattern="*")',
    'EOF'
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

__init_config_network_interfaces__ = """
cat << EOF > /etc/network/interfaces
############################################################
# CAUTION: lines under special marker: ###netifcfg-*###
# contains autogenerated information. You can add/modify
# lines outside of those markers
############################################################

# loopback configuration
auto lo
iface lo inet loopback

###netifcfg-begin###

"""


def check_argument_parser():
    log_message(2, "Analyze options ... ")
    parser = argparse.ArgumentParser(description=description_argument_parser, epilog=epilog_argument_parser)
    parser.add_argument('-f', '--file', help='File name input', dest="file_name", default='')
    parser.add_argument('-c', '--command', help='Run commands', dest="command_run", default='')
    parser.add_argument('-i', '--init', help='Initialyze S-Terra', dest="init", action="store_true")
    parser.add_argument('-ga', '--getall', help='Get All Configs from S-Terra', dest="get_all", action="store_true")
    parser.add_argument('-gc', '--getcisco', help='Get cisco config', dest="get_config_cisco", action="store_true")
    parser.add_argument('-hi', '--hostip', help='IP address of Hosts', dest="host_ip", default='')
    parser.add_argument('-tm', '--sshtimeout', help='SSH timeout in sec', dest="ssh_timeout", default=2)
    parser.add_argument('-ps', '--passwords', help='Set passwords', dest="passwords", default='')
    parser.add_argument('-pe', '--passenable', help='Set enable password', dest="get_enable_password", action="store_true")
    parser.add_argument('-pn', '--numpass', help='Number passwords', dest="number_pass", default='')
    parser.add_argument('-od', '--outdir', help='Output dir for writing files', dest="output_dir", default='./output/')
    parser.add_argument('-t', '--testing', help='For testing other features', dest="testing", action="store_true")
    parser.add_argument('-p', '--print', help='Output on screen ', dest="print_onscreen", action="store_true")
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


def get_list_hosts_from_file(name_config_file):
    global __list_hosts_ssh__
    id_config_file = open(name_config_file, 'r', encoding="utf-8")
    for line_config_file in id_config_file:
        if line_config_file.strip() != '' and not re.search("!", line_config_file):
            __list_hosts_ssh__.append(list(line_config_file.strip().split(';')))
    id_config_file.close()
    log_message(2, __list_hosts_ssh__)


def get_dict_hosts_from_file(name_config_file):
    global __dict_hosts_ssh__
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
            __dict_hosts_ssh__.append(data)

    log_message(2, __dict_hosts_ssh__)
    id_config_file.close()


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
        id_conn_paramiko.load_system_host_keys()
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
        # log_buff = cleanBuff(log_buff)

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


def cleanBuff(tmp_buff):
    return_clean_buff = ""
    for one_str_buff in tmp_buff.split("\n"):
        if not re.search(":~#", one_str_buff.strip()):
            log_message(2, one_str_buff.strip())
            return_clean_buff += one_str_buff.strip()
    return return_clean_buff


def set_license_sterra(info_host_ssh):
    global __list_hosts_ssh__, __list_passwords_ssh__, __dict_hosts_ssh__
    lic_command = ' lic_mgr set -p {product:s} -c {customer:s} -n  {lic_num:s}  -l {lic_code:s}'.format_map(info_host_ssh)
    log_message(0, lic_command)
    log_buff = cmd_run_command(list(lic_command.split(',')), __list_passwords_ssh__[0], info_host_ssh['ip'])
    if re.search("Wrong", log_buff):
        log_message(0, "Wrong license !!!!!")


def csconsole_run_command(run_commands, password_ssh, ip_host_ssh):
    global __number_passwords_ssh__
    csconsole_command = "su cscons"
    enable_command = "enable"
    null_terminal_length_command = "terminal length 0"
    log_buff = ""
    log_message(2, "run_cs_console_command ..")
    try:
        log_message(1, "Try to connect host: " + ip_host_ssh)
        id_conn_paramiko = paramiko.SSHClient()
        id_conn_paramiko.load_system_host_keys()
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
                log_message(1, resp_ssh)
            log_message(0, "Command \'" + run_command + "\' run OK")
        log_message(2, log_buff)

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
        id_conn_paramiko.load_system_host_keys()
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
    __output_dir__ = arg.output_dir
    if arg.print_onscreen:
        __flag_print_onscreen__ = True
    # Filename with hostnames and other information
    if arg.file_name:
        get_list_hosts_from_file(arg.file_name)
        get_dict_hosts_from_file(arg.file_name)
    if arg.host_ip:
        for ip_host in arg.host_ip.split(','):
            data = dict()
            data['ip'] = ip_host.strip()
            data['host'] = ""
            __dict_hosts_ssh__.append(data)
        log_message(2, __dict_hosts_ssh__)

    # Set passwords for ssh
    if arg.number_pass:
        for n in range(int(arg.number_pass)):
            __list_passwords_ssh__.append(getpass.getpass("Password Number " + str(n + 1) + " :"))
        __number_passwords_ssh__ = len(__list_passwords_ssh__)
    elif arg.passwords:
        for n in arg.passwords.split(','):
            __list_passwords_ssh__.append(n.strip())
        __number_passwords_ssh__ = len(__list_passwords_ssh__)
    else:
        __list_passwords_ssh__.append('cisco')
    log_message(2, "Count pass: " + str(__number_passwords_ssh__))
    if arg.get_enable_password:
        __list_passwords_enable__[0] = getpass.getpass("Enable Password :")
        __list_passwords_enable__.append("csp")

    # Run commands
    if arg.command_run:
        for c in arg.command_run.split(','):
            listComm.append(c.strip())
        for h in __dict_hosts_ssh__:
            log_message(0, "!=======================================================================")
            log_message(0, '+++++++++++++++++++ {ip:s} ({host:s}) +++++++++++++++++++'.format_map(h))
            if h['host'] == '':
                hostname = get_hostname(__list_passwords_ssh__[0], h['ip']).strip()
            else:
                hostname = h['host']
            ret_log_buff = cmd_run_command(listComm, __list_passwords_ssh__[0], h['ip'])
            log_message(2, "!----------------------" + h['ip'] + "(" + h['host'] + ")----------------------")
            log_message(2, ret_log_buff)
            if ret_log_buff:
                write_to_file_result("command", hostname, h['ip'], ret_log_buff)
    # Run commands for get all configs s-terra
    if arg.get_all:
        for h in __dict_hosts_ssh__:
            log_message(0, "!=======================================================================")
            log_message(0, '+++++++++++++++++++ {ip:s} ({host:s}) +++++++++++++++++++'.format_map(h))
            if h['host'] == '':
                hostname = get_hostname(__list_passwords_ssh__[0], h['ip']).strip()
            else:
                hostname = h['host']
            # print("Hostname : " + hostname + "===")
            ret_log_buff = cmd_run_command(__all_config_list_command__, __list_passwords_ssh__[0], h['ip'])
            log_message(2, "!----------------------" + h['ip'] + "(" + hostname + ")----------------------")
            log_message(2, ret_log_buff)
            if ret_log_buff:
                write_to_file_result("sterra", hostname, h['ip'], ret_log_buff)
    # Run Initialization s-terra
    if arg.init:
        __init_commands__.append('\n'.join(__ifaliases_file_))
        __init_commands__.append(__init_ifaliases_file__)
        __init_commands__.append(__init_default_vpngate__)
        __init_commands__.append(__init_conf_forwarding_network__)
        __init_commands__.append(__vpndrv_start_services_sterra__)
        __init_commands__.append(__vpnlog_start_services_sterra__)
        __init_commands__.append(__vpngate_start_services_sterra__)
        __init_commands__.append('')

        log_message(2, __init_commands__)
        for h in __dict_hosts_ssh__:
            if (len(h) - 1) >= 6:
                print("length dict: " + str(len(h)))
                __init_commands__[len(__init_commands__) - 1] = __init_config_network_interfaces__
                __init_commands__[len(__init_commands__) - 1] += 'auto {eth:s} \niface {eth:s} inet static\nmtu 1500\n'.format_map(h)
                __init_commands__[len(__init_commands__) - 1] += 'address {ip_host:s}\nnetmask {ip_mask:s}\n###netifcfg-end###\nEOF\n'.format_map(h)

            # print(__init_commands__)
            ret_log_buff = ""
            tmp_ret_log_buff = ""
            log_message(0, "!=======================================================================")
            log_message(0, '+++++++++++++++++++ {ip:s} ({host:s}) +++++++++++++++++++'.format_map(h))
            log_message(0, "+++++++++++++++++++ Run initializing RND +++++++++++++++++++  ")
            ret_log_buff = rnd_run_command(__list_passwords_ssh__[0], h['ip'])
            tmp_ret_log_buff += ret_log_buff
            log_message(0, ret_log_buff)
            log_message(0, "+++++++++++++++++++ Set license +++++++++++++++++++ ")
            set_license_sterra(h)
            ret_log_buff = cmd_run_command(__init_commands__, __list_passwords_ssh__[0], h['ip'])
            tmp_ret_log_buff += ret_log_buff
            log_message(0, ret_log_buff)
            time.sleep(2)
            ip_route_command = 'ip route 0.0.0.0 0.0.0.0  {ip_default:s}'.format_map(h)
            ret_log_buff = csconsole_run_command(['conf t', ip_route_command, 'end', 'exit'], __list_passwords_ssh__[0], h['ip'])
            tmp_ret_log_buff += ret_log_buff
            log_message(0, ret_log_buff)
            if ret_log_buff:
                write_to_file_result("initialize", h['host'], h['ip'], tmp_ret_log_buff)

    # Get cisco like console from s-terra
    if arg.get_config_cisco:
        for h in __dict_hosts_ssh__:
            log_message(0, "!=======================================================================")
            log_message(0, '+++++++++++++++++++ {ip:s} ({host:s}) +++++++++++++++++++'.format_map(h))
            if h['host'] == '':
                hostname = get_hostname(__list_passwords_ssh__[0], h['ip']).strip()
            else:
                hostname = h['host']
            log_message(1, "Host to connect : " + hostname + "---" + h['ip'])
            ret_log_buff = csconsole_run_command(['show run'], __list_passwords_ssh__[0], h['ip'])
            log_message(2, ret_log_buff)
            if ret_log_buff:
                write_to_file_result("csconsole", hostname, h['ip'], ret_log_buff)

    if arg.testing:
        get_dict_hosts_from_file(arg.file_name)
        print(__list_hosts_ssh__)
        for x in __list_hosts_ssh__:
            print(' lic_mgr set -p {ip:s} -c {customer:s} -n  {lic_num:s}  -l {lic_code:s}'.format_map(x))
        getpass.getpass()

    log_message(0, "Script complete successful!!! ")
    sys.exit()
