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

description_argument_parser = "S-Terra: Configure S-Terra, v1.0"
epilog_argument_parser = "Alexey: alexeykr@gmail.ru"

__level_debug__ = int()

__timeout_ssh__ = 2
__list_passwords_ssh__ = []
__list_passwords_enable__ = ['csp']
__number_passwords_ssh__ = 2
__list_hosts_ssh__ = list()
__username_ssh__ = "root"
__output_dir__ = ""

__all_config_list_command__ = [
    'lic_mgr show',
    'cat /opt/l2svc/etc/*.lic',
    'cat /etc/ifaliases.cf',
    'cat /etc/network/interfaces'
]


def log_message(level_debug, message_log):
    # global __flag_debug__
    if __level_debug__ >= level_debug:
        print(message_log)


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


def write_to_file_result(pre_name_file, namehost, iphost, write_messsage):
    year, month, day, hour, minute = get_date()
    list_names = [pre_name_file, hostname, iphost, day, month, year, hour, minute + ".txt"]
    file_name = '-'.join(list_names)
    id_config_file = open(__output_dir__ + file_name, 'w')
    id_config_file.write(write_messsage)
    id_config_file.write("\n\n")
    id_config_file.close()    


def check_argument_parser():
    log_message(2, "Analyze options ... ")
    parser = argparse.ArgumentParser(description=description_argument_parser, epilog=epilog_argument_parser)
    parser.add_argument('-f', '--file', help='File name input', dest="file_name", default='sterra.conf')
    parser.add_argument('-c', '--command', help='Run command', dest="command_run", default='')
    parser.add_argument('-i', '--init', help='Initialyze S-Terra', dest="init", action="store_true")
    parser.add_argument('-ga', '--getall', help='Get All Configs from S-Terra', dest="get_all", action="store_true")
    parser.add_argument('-gc', '--getcisco', help='Get cisco config', dest="get_config_cisco", action="store_true")
    parser.add_argument('-hi', '--hostip', help='IP address of Hosts', dest="host_ip", default='')
    parser.add_argument('-tm', '--sshtimeout', help='SSH timeout in sec', dest="ssh_timeout", default=5)
    parser.add_argument('-ps', '--passwords', help='Set passwords', dest="passwords", default='')
    parser.add_argument('-pe', '--passenable', help='Set enable password', dest="get_enable_password", action="store_true")
    parser.add_argument('-pn', '--numpass', help='Number passwords', dest="number_pass", default='')
    parser.add_argument('-od', '--outdir', help='Output dir for writing files', dest="output_dir", default='./output/')
    parser.add_argument('-d', '--debug', help='Debug information view(1 - standart, 2 - more verbose)', dest="debug", default=0)

    return parser.parse_args()


def get_list_hosts_from_file(name_config_file):
    global __list_hosts_ssh__
    id_config_file = open(name_config_file, 'r')
    for line_config_file in id_config_file:
        log_message(2, line_config_file)
        if line_config_file.strip() != '' and not re.search("!", line_config_file):
            __list_hosts_ssh__.append(list(line_config_file.strip().split(';')))
    id_config_file.close()


def get_hostname(password_ssh, ip_host_ssh):
    run_hostname_command = ['hostname']
    hostname = ""
    tmp_buff = ""
    tmp_buff = run_command(run_hostname_command, password_ssh, ip_host_ssh)
    log_message(2, "tmp_buff for ip : " + ip_host_ssh + "  include: " + tmp_buff)
    for line_hostname in tmp_buff.split("\n"):
        # or (not re.search('#', line_hostname))
        if not re.search("hostname|#|!=", line_hostname):
            if line_hostname.strip():
                hostname += line_hostname
                # print("line_hostname: " + line_hostname)
    return hostname


def run_command(run_commands, password_ssh, ip_host_ssh):
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
            log_buff += "\n!===============================================================\n"
            chan.send(str_command + "\n")
            # dbgLog(0, sComm)
            while not re.search("#", resp_ssh):
                while not chan.recv_ready():
                    time.sleep(0.05)
                resp_ssh = chan.recv(9999).decode('ascii')
                log_message(2, "====" + resp_ssh + "=====")
                log_buff += resp_ssh
            log_message(1, "Command \'" + str_command + "\' run OK")
        log_buff += "\n!===============================================================\n"
        # log_buff = cleanBuff(log_buff)

    except paramiko.AuthenticationException:
        print("Authentication problem with host ip: " + ip_host_ssh + " ... access denied")
        if __number_passwords_ssh__ > 1:
            print("Connecting with another password ...")
            __number_passwords_ssh__ -= 1
            id_conn_paramiko.close()
            log_buff = run_command(run_commands, __list_passwords_ssh__[len(__list_passwords_ssh__) - __number_passwords_ssh__], ip_host_ssh)

    except paramiko.SSHException as sshException:
        print("Could not establish SSH connection with host ip: " + ip_host_ssh + " : %s" % sshException)
    except socket.error as e:
        print("Socket error with host ip: " + ip_host_ssh + " : ", e)
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
    global __list_hosts_ssh__, __list_passwords_ssh__
    lic_command = "lic_mgr set -p " + info_host_ssh[2] + " -c " + info_host_ssh[3] + " -n " + info_host_ssh[4] + " -l " + info_host_ssh[5]
    log_message(1, lic_command)
    run_command(list(lic_command.split(',')), __list_passwords_ssh__[0], info_host_ssh[0])


def get_show_run_cs_console(password_ssh, ip_host_ssh):
    global __number_passwords_ssh__
    csconsole_command = "/usr/bin/cs_console"
    enable_command = "enable"
    null_terminal_length_command = "terminal length 0"
    get_config_command = "show run"
    log_buff = ""
    log_message(2, "Module get_show_run_cs_console ..")
    try:
        log_message(0, "Try to connect host: " + ip_host_ssh)
        id_conn_paramiko = paramiko.SSHClient()
        id_conn_paramiko.load_system_host_keys()
        id_conn_paramiko.set_missing_host_key_policy(paramiko.WarningPolicy)

        id_conn_paramiko.connect(ip_host_ssh, username=__username_ssh__, password=password_ssh, timeout=__timeout_ssh__)
        chan = id_conn_paramiko.invoke_shell()

        resp_ssh = ""
        log_message(0, "Connected to host : " + ip_host_ssh)
        while not re.search("#", resp_ssh):
            while not chan.recv_ready():
                time.sleep(0.05)
            resp_ssh = chan.recv(9999).decode('ascii')
        log_message(2, resp_ssh)
        log_message(1, "Received command promt \'#\': OK")

        chan.send(csconsole_command + "\n")
        resp_ssh = ""
        while not re.search(">", resp_ssh):
            while not chan.recv_ready():
                time.sleep(0.05)
            resp_ssh = chan.recv(9999).decode('ascii')
            if re.search("Could not establish", resp_ssh):
                log_message(0, "ERROR: Could not establish connection with daemon on host: "  + ip_host_ssh)
                log_message(0, "Return without cisco configuration ...  ")
                return log_buff
            log_message(2, resp_ssh)
        log_message(1, "Command \'" + csconsole_command + "\'run OK")

        chan.send(enable_command + "\n")
        resp_ssh = ""
        log_message(1, "Running command \'" + enable_command + "\' ...")
        while not re.search("assword", resp_ssh):
            while not chan.recv_ready():
                time.sleep(0.05)
            resp_ssh = chan.recv(9999).decode('ascii')
            log_message(1, resp_ssh)
        num_list_password = len(__list_passwords_enable__)
        log_message(1, "Num enable password: " + str(num_list_password))
        for enable_password in __list_passwords_enable__:
            log_message(1, "Current num enable password: " + str(num_list_password))
            log_message(1, "Enable pass: " + enable_password)
            chan.send(enable_password + "\n")
            resp_ssh = ""
            while not re.search("#", resp_ssh):
                while not chan.recv_ready():
                    time.sleep(0.05)
                resp_ssh = chan.recv(9999).decode('ascii')
                log_message(2, resp_ssh)
                if re.search("denied", resp_ssh):
                    log_message(1, "Enable password is incorect for host: " + ip_host_ssh)                    
                    num_list_password -= 1
                    if num_list_password == 0:
                        log_message(1, "Return without enable ")
                        __number_passwords_ssh__ = len(__list_passwords_ssh__)
                        id_conn_paramiko.close()
                        return ""
                    else:
                        log_message(1, "Break if")
                        chan.send(enable_command + "\n")
                        break
                log_message(2, resp_ssh)
        log_message(1, "Command \'" + enable_command + "\' run OK")

        log_message(1, "Run null terminal length")
        chan.send(null_terminal_length_command + "\n")
        resp_ssh = ""
        while not re.search("#", resp_ssh):
            while not chan.recv_ready():
                time.sleep(0.05)
            resp_ssh = chan.recv(9999).decode('ascii')
            log_message(2, resp_ssh)
        log_message(1, "Command \'" + null_terminal_length_command + "\' run OK")

        chan.send(get_config_command + "\n")
        resp_ssh = ""
        while not re.search("#", resp_ssh):
            while not chan.recv_ready():
                time.sleep(0.05)
            resp_ssh = chan.recv(9999).decode('ascii')
            log_buff += resp_ssh
            log_message(2, resp_ssh)
        log_message(1, "Command \'" + get_config_command + "\' run OK")
        log_message(2, log_buff)

    except paramiko.AuthenticationException:
        print("Authentication problem ...")
        if __number_passwords_ssh__ > 1:
            print("Connecting with another password ...")
            __number_passwords_ssh__ -= 1
            log_buff = get_show_run_cs_console(__list_passwords_ssh__[len(__list_passwords_ssh__) - __number_passwords_ssh__], ip_host_ssh)

    except paramiko.SSHException as sshException:
        print("Could not establish SSH connection: %s" % sshException)
        __number_passwords_ssh__ = len(__list_passwords_ssh__)
    except socket.error as e:
        print("Socket error: ", e)
    else:
        log_message(0, "Connected ... OK")
        __number_passwords_ssh__ = len(__list_passwords_ssh__)
    finally:
        id_conn_paramiko.close()
        return log_buff


def rnd_run_command(password_ssh, ip_host_ssh):
    global __number_passwords_ssh__
    rnd_command = "/opt/VPNagent/bin/rnd_mgr -once"
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
                time.sleep(0.05)
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
                    log_message(2, "Character:" + line_resp_ssh.split(':')[1].strip() + "")
                    chan.send(line_resp_ssh.split(':')[1].strip())
                    while not chan.recv_ready():
                        time.sleep(0.05)
                    break
            resp_ssh = chan.recv(9999).decode('ascii')
            log_message(1, resp_ssh)
            if re.search("initialized", resp_ssh):
                log_buff = "Successfully initialized RNG."
        log_message(0, log_buff)
        id_conn_paramiko.close()
    except paramiko.AuthenticationException:
        print("Authentication problem ...")
        if __number_passwords_ssh__ > 1:
            print("Connecting with another password ...")
            __number_passwords_ssh__ -= 1
            rnd_run_command(__list_passwords_ssh__[len(__list_passwords_ssh__) - __number_passwords_ssh__], ip_host_ssh)

    except paramiko.SSHException as sshException:
        print("Could not establish SSH connection: %s" % sshException)
    except socket.error as e:
        print("Socket error: ", e)
    else:
        log_message(0, "Connected ... OK")
        __number_passwords_ssh__ = len(__list_passwords_ssh__)
    finally:
        id_conn_paramiko.close()
        return log_buff


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
    __level_debug__ = int(arg.debug)
    __timeout_ssh__ = int(arg.ssh_timeout)
    __output_dir__ = arg.output_dir
    # Filename with hostnames and other information
    if arg.file_name:
        get_list_hosts_from_file(arg.file_name)
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
            listComm.append(c)
        for h in __list_hosts_ssh__:
            hostname = get_hostname(__list_passwords_ssh__[0], h[0]).strip()            
            ret_log_buff = run_command(listComm, __list_passwords_ssh__[0], h[0])
            log_message(2, "!----------------------" + h[0] + "(" + h[1] + ")----------------------")
            log_message(2, ret_log_buff)
            write_to_file_result("command", hostname, h[0], ret_log_buff)

    # Run commands for get all configs s-terra
    if arg.get_all:
        for h in __list_hosts_ssh__:
            log_message(0, "!-----------------------------------------------------------------------")
            hostname = get_hostname(__list_passwords_ssh__[0], h[0]).strip()
            ret_log_buff = run_command(__all_config_list_command__, __list_passwords_ssh__[0], h[0])
            log_message(2, "!----------------------" + h[0] + "(" + hostname + ")----------------------")
            log_message(2, ret_log_buff)
            if ret_log_buff:
                write_to_file_result("config", hostname, h[0], ret_log_buff)

    # Run Initialization s-terra
    if arg.init:
        for h in __list_hosts_ssh__:
            log_message(0, "!----------------------" + h[0] + "(" + h[1] + ")----------------------")
            rnd_run_command(__list_passwords_ssh__[0], h[0])
            set_license_sterra(h)
    # Get cisco like console from s-terra
    if arg.get_config_cisco:
        for h in __list_hosts_ssh__:
            log_message(0, "!-----------------------------------------------------------------------")
            hostname = get_hostname(__list_passwords_ssh__[0], h[0]).strip()
            log_message(1, "Host to connect : " + hostname + "---" + h[0])
            ret_log_buff = get_show_run_cs_console(__list_passwords_ssh__[0], h[0])
            log_message(2, ret_log_buff)
            if ret_log_buff:
                write_to_file_result("csconsole", hostname, h[0], ret_log_buff)

    log_message(0, "Script complete successful!!! ")
    sys.exit()
