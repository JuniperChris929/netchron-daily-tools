import os
import sys
import yaml
import time
import shutil
import getpass
import logging
import paramiko
import jnpr.junos
from pathlib import Path
from scp import SCPClient
from jnpr.junos import Device
from datetime import datetime
from jnpr.junos.factory.factory_loader import FactoryLoader

yml = """
---
bgpAdvertiseRoutes:
 rpc: get-route-information
 args:
  advertising-protocol-name: bgp
  extensive: True
 item: route-table/rt 
 key:  rt-destination
 view: bgpAdvertiseView

bgpAdvertiseView:
 fields:
  rt_destination: rt-destination
  rt_prefix_length: rt-prefix-length
  rt_protocol_name: rt-entry/protocol-name
  bgp_group_name: rt-entry/bgp-group-name
  bgp_nh: rt-entry/nh/to
  rt_med: rt-entry/med
  rt_local_preference: rt-entry/local-preference
  rt_as_path: rt-entry/as-path
  rt_communities: rt-entry/communities/community
  
bgpSummary:
 rpc: get-bgp-summary-information
 
 
  """


def login_details():
    global varIP
    global varUser
    global varPassword

    varIP = input("Please enter the Hostname or IP of your target Device: ")
    varUser = input("Please Enter a Username (NOT ROOT): ")
    varPassword = getpass.getpass()

    if str(varUser) == 'root':
        sys.exit(
            '                             .----------.\n                            /  .-.  .-.  \\\n                           /   | |  | |   \\\n                           \\   `-\'  `-\'  _/\n                           /\\     .--.  / |\n                           \\ |   /  /  / /\n                           / |  `--\'  /\\ \\\n                            /`-------\'  \\ \\      \n            By choosing the name root you have doomed us all!\nBuy fear not - I have ended this script so the apocalypse is not today ;)\n')


def bgp_adv():
    globals().update(FactoryLoader().load(yaml.safe_load(yml)))

    with Device(varIP, port='22', user=varUser, passwd=varPassword) as dev:
        op = dev.rpc.get_bgp_summary_information()
        for i in op.xpath('bgp-peer/peer-address'):
            # print(i.text)
            load_bgp = bgpAdvertiseRoutes(dev).get(neighbor=i.text)
            print("\n-----------------BGP Advertising Routes For:", i.text, "-----------------")
            for item in load_bgp:
                print('----------------------------------------------')
                print("Advertising_Route:", item.rt_destination, "Prefix_Lengh:", item.rt_prefix_length, "MED:",
                      item.rt_med, "LP:", item.rt_local_preference, "AS_Path:", item.rt_as_path, "Communities:",
                      item.rt_communities)

    print("\n")
    print("\n")


def set_vlan():
    devices = [
        varIP,
    ]

    varVlName = str(input("Please Enter the vlan Name to be deployed: "))

    while True:
        try:
            varintVlID = int(input("Please Enter the vlan ID for " + varVlName + " between 1 and 4092: "))
        except ValueError:
            print("That is not a number!")
        else:
            if 1 < varintVlID <= 4092:
                break
            else:
                print("Only numbers between 1 and 4092 are allowed. The IDs 0, 4093 and above are used internally.")

    varVlID = str(varintVlID)

    for switch in devices:
        # Connect to switch and build ssh connection
        remote_conn_pre = paramiko.SSHClient()
        remote_conn_pre.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        remote_conn_pre.connect(switch, username=varUser, password=varPassword, look_for_keys=False, allow_agent=False)
        print('SSH connection established to ' + switch)
        remote_conn = remote_conn_pre.invoke_shell()
        print('Interactive SSH session established')

        # Print terminal to screen
        output = remote_conn.recv(3000)
        remote_conn.send('\n')
        time.sleep(2)
        print(output.decode())

        # Username root requires getting into the cli
        if varUser == 'root':
            remote_conn.send('cli\n')
            time.sleep(3)
            output = remote_conn.recv(3000)
            print(output.decode())
        else:
            pass

        # Enter configuration mode
        remote_conn.send('configure\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        print(output.decode())

        # SNMP Configuration
        remote_conn.send('set vlans ' + varVlName + ' vlan-id ' + varVlID + '\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        print(output.decode())

        # Save configuration
        remote_conn.send("commit and-quit\n")
        time.sleep(6)
        output = remote_conn.recv(3000)
        print(output.decode())

        # Exit configuration mode
        remote_conn.send('exit\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        print(output.decode())

        if varUser == 'root':
            remote_conn.send('exit\n')
            time.sleep(2)
            output = remote_conn.recv(3000)
            print(output.decode())
        else:
            pass


def bgp_summary():
    port_arg = 22

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(varIP, username=varUser, password=varPassword, port=port_arg)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        channel = ssh.invoke_shell()
        stdin, stdout, stderr = ssh.exec_command(
            'show bgp summary\n')
        exit_status = stdout.channel.recv_exit_status()
        stdout = stdout.readlines()
        print('\n'.join(stdout))
        ssh.close()
        print("\n")
        print("\n")
    except paramiko.AuthenticationException as error:
        print("Error: The Credentials did not work or ssh / netconf is not enabled!")
        print("\n")
        print("\n")


def chassis_re():
    port_arg = 22

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(varIP, username=varUser, password=varPassword, port=port_arg)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        channel = ssh.invoke_shell()
        stdin, stdout, stderr = ssh.exec_command(
            'show chassis routing-engine\n')
        exit_status = stdout.channel.recv_exit_status()
        stdout = stdout.readlines()
        print('\n'.join(stdout))
        ssh.close()
        print("\n")
        print("\n")
    except paramiko.AuthenticationException as error:
        print("Error: The Credentials did not work or ssh / netconf is not enabled!")
        print("\n")
        print("\n")


def dev_script():
    port_arg = 22

    dev = Device(host=varIP, user=varUser, password=varPassword, gather_facts=True)
    dev.open()
    dev.timeout = 60
    facts = dev.facts
    print(dev.facts['serialnumber'])
    print("\n")
    print("\n")


def ospf_neighbors():
    port_arg = 22

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(varIP, username=varUser, password=varPassword, port=port_arg)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        channel = ssh.invoke_shell()
        stdin, stdout, stderr = ssh.exec_command(
            'show ospf neighbor\n')
        exit_status = stdout.channel.recv_exit_status()
        stdout = stdout.readlines()
        print('\n'.join(stdout))
        ssh.close()
        print("\n")
        print("\n")
    except paramiko.AuthenticationException as error:
        print("Error: The Credentials did not work or ssh / netconf is not enabled!")
        print("\n")
        print("\n")


def if_descr():
    port_arg = 22

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(varIP, username=varUser, password=varPassword, port=port_arg)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        channel = ssh.invoke_shell()
        stdin, stdout, stderr = ssh.exec_command(
            'show interfaces descriptions\n')
        exit_status = stdout.channel.recv_exit_status()
        stdout = stdout.readlines()
        print('\n'.join(stdout))
        ssh.close()
        print("\n")
        print("\n")
    except paramiko.AuthenticationException as error:
        print("Error: The Credentials did not work or ssh / netconf is not enabled!")
        print("\n")
        print("\n")


def get_device():
    port_arg = 22

    dev = Device(host=varIP, user=varUser, password=varPassword, gather_facts=True)
    dev.open()
    dev.timeout = 60
    facts = dev.facts
    print("Device has been identified as: " + dev.facts['model'])
    print("Device has the following Serialnumber: " + dev.facts['serialnumber'])
    print("Device is currently running on: " + dev.facts['version'])
    print("\n")
    print("\n")


def enable_netconf():
    devices = [
        varIP,
    ]

    for switch in devices:
        # Connect to switch and build ssh connection
        remote_conn_pre = paramiko.SSHClient()
        remote_conn_pre.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        remote_conn_pre.connect(switch, username=varUser, password=varPassword, look_for_keys=False, allow_agent=False)
        print('SSH connection established to ' + switch)
        remote_conn = remote_conn_pre.invoke_shell()
        print('Interactive SSH session established')

        # Print terminal to screen
        output = remote_conn.recv(3000)
        remote_conn.send('\n')
        time.sleep(2)
        print(output.decode())

        # Username root requires getting into the cli
        if varUser == 'root':
            remote_conn.send('cli\n')
            time.sleep(3)
            output = remote_conn.recv(3000)
            print(output.decode())
        else:
            pass

        # Enter configuration mode
        remote_conn.send('configure\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        print(output.decode())

        # SNMP Configuration
        remote_conn.send('set system services netconf ssh\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        print(output.decode())

        # Save configuration
        remote_conn.send("commit and-quit\n")
        time.sleep(6)
        output = remote_conn.recv(3000)
        print(output.decode())

        # Exit configuration mode
        remote_conn.send('exit\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        print(output.decode())

        if varUser == 'root':
            remote_conn.send('exit\n')
            time.sleep(2)
            output = remote_conn.recv(3000)
            print(output.decode())
        else:
            pass


def disable_netconf():
    devices = [
        varIP,
    ]

    for switch in devices:
        # Connect to switch and build ssh connection
        remote_conn_pre = paramiko.SSHClient()
        remote_conn_pre.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        remote_conn_pre.connect(switch, username=varUser, password=varPassword, look_for_keys=False, allow_agent=False)
        print('SSH connection established to ' + switch)
        remote_conn = remote_conn_pre.invoke_shell()
        print('Interactive SSH session established')

        # Print terminal to screen
        output = remote_conn.recv(3000)
        remote_conn.send('\n')
        time.sleep(2)
        print(output.decode())

        # Username root requires getting into the cli
        if varUser == 'root':
            remote_conn.send('cli\n')
            time.sleep(3)
            output = remote_conn.recv(3000)
            print(output.decode())
        else:
            pass

        # Enter configuration mode
        remote_conn.send('configure\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        print(output.decode())

        # SNMP Configuration
        remote_conn.send('delete system services netconf\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        print(output.decode())

        # Save configuration
        remote_conn.send("commit and-quit\n")
        time.sleep(6)
        output = remote_conn.recv(3000)
        print(output.decode())

        # Exit configuration mode
        remote_conn.send('exit\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        print(output.decode())

        if varUser == 'root':
            remote_conn.send('exit\n')
            time.sleep(2)
            output = remote_conn.recv(3000)
            print(output.decode())
        else:
            pass


def spanning_unblock():
    port_arg = 22

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(varIP, username=varUser, password=varPassword, port=port_arg)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        channel = ssh.invoke_shell()
        stdin, stdout, stderr = ssh.exec_command(
            'clear ethernet-switching bpdu-error\n')
        exit_status = stdout.channel.recv_exit_status()
        stdout = stdout.readlines()
        print('\n'.join(stdout))
        ssh.close()
        print("\n")
        print("\n")
    except paramiko.AuthenticationException as error:
        print("Error: The Credentials did not work or ssh / netconf is not enabled!")
        print("\n")
        print("\n")


def spanning_block():
    port_arg = 22

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(varIP, username=varUser, password=varPassword, port=port_arg)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        channel = ssh.invoke_shell()
        stdin, stdout, stderr = ssh.exec_command(
            'show ethernet-switching interface | match "Forwarding|Blocking|fe-|ge-|xe-|et-"\n')
        exit_status = stdout.channel.recv_exit_status()
        stdout = stdout.readlines()
        print('\n'.join(stdout))
        ssh.close()
        print("\n")
        print("\n")
    except paramiko.AuthenticationException as error:
        print("Error: The Credentials did not work or ssh / netconf is not enabled!")
        print("\n")
        print("\n")


def njsupport():
    now = datetime.now()
    dir_config = 'configuration'
    dir_rsi = 'rsi'
    dir_core = 'core-dumps'
    dir_logfiles = 'logfiles'
    dir_root = 'upload'
    date_arg = now.strftime("%Y-%m-%d_%H-%M-%S")

    # Set up logging
    log = "njs.log"
    logging.basicConfig(filename=log, level=logging.DEBUG, format='%(asctime)s %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')

    buff = ''
    resp = ''

    while True:
        try:
            varPath = str(input("Do you want the support package [R]emote (on the box) or [L]ocal (download to this PC)?: "))
        except ValueError:
            print("Please choose either R for Remote or L for Local")
        else:
            if varPath=="R" or varPath=="L":
                break
            else:
                print("Please choose either R for Remote or L for Local")

    print("\n")
    print("\n")
    print("\n")
    print("###############################################################################")
    print("#                                                                             #")
    print("#            WARNING: Please leave this Window open and running.              #")
    print("#                                                                             #")
    print("###############################################################################")
    print("\n")
    print("\n")
    print("\n")
    print("Script is starting...")
    logging.info('Script is starting...')
    time.sleep(2)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(varIP, username=varUser, password=varPassword)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    channel = ssh.invoke_shell()

    # Creating necessary folders (if they don't exist) so root folder does not get messy
    logging.info('Trying to create necessary folders')

    if not os.path.exists(dir_root + '-' + varIP + '-' + date_arg):
        os.mkdir(dir_root + '-' + varIP + '-' + date_arg)
        logging.info('Info: root directory created successfully')
    else:
        logging.info('Info: root directory already existed!')

    if not os.path.exists(dir_root + '-' + varIP + '-' + date_arg + '/' + dir_config):
        os.mkdir(dir_root + '-' + varIP + '-' + date_arg + '/' + dir_config)
        logging.info('Info: directory for configuration-files created successfully')
    else:
        logging.info('Info: directory for configuration-files already existed!')

    if not os.path.exists(dir_root + '-' + varIP + '-' + date_arg + '/' + dir_rsi):
        os.mkdir(dir_root + '-' + varIP + '-' + date_arg + '/' + dir_rsi)
        logging.info('Info: directory for rsi-files created successfully')
    else:
        logging.info('Info: directory for rsi-files already existed!')

    if not os.path.exists(dir_root + '-' + varIP + '-' + date_arg + '/' + dir_core):
        os.mkdir(dir_root + '-' + varIP + '-' + date_arg + '/' + dir_core)
        logging.info('Info: directory for core-dumps created successfully')
    else:
        logging.info('Info: directory for core-dumps already existed!')

    if not os.path.exists(dir_root + '-' + varIP + '-' + date_arg + '/' + dir_logfiles):
        os.mkdir(dir_root + '-' + varIP + '-' + date_arg + '/' + dir_logfiles)
        logging.info('Info: directory for logfiles created successfully')
    else:
        logging.info('Info: directory for logfiles already existed!')

    # Saving the config
    print("\n")
    print("Step 1/5: Saving the active configuration in set-format (including secrets)")
    logging.info('Step1/5: Saving the active configuration in set-format (including secrets)')
    stdin, stdout, stderr = ssh.exec_command(
        'show configuration | display set | no-more | save /var/tmp/active-config-' + date_arg + '.txt\n')
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        logging.info('Info: Configuration saved successfully.')
    else:
        logging.info('Error: Could not save configuration.')

    # Creating the RSI (save to file) and wait for it to complete
    # See https://www.juniper.net/documentation/en_US/junos/topics/reference/command-summary/request-support-information.html
    print("\n")
    print("Step 2/5: Creating the RSI")
    logging.info('Step 2/5: Creating the RSI')

    stdin, stdout, stderr = ssh.exec_command('request support information | save /var/tmp/rsi-' + date_arg + '.txt\n')
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        logging.info('Info: RSI created successfully.')
    else:
        logging.info('Error: Could not create RSI. Please check the device manually.')

    # Compressing the Logfiles
    # See https://www.juniper.net/documentation/en_US/junos/topics/task/troubleshooting/troubleshooting-logs-compressing.html
    print("\n")
    print("Step 3/5: Compressing the Logfiles")
    logging.info('Step 3/5: Compressing the Logfiles')
    stdin, stdout, stderr = ssh.exec_command(
        'file archive compress source /var/log/* destination /var/tmp/logfiles-' + date_arg + '.tgz\n')
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        logging.info('Info: Logfiles compressed successfully.')
    else:
        logging.info('Error: Logfiles not compresses successfully. Check Device manually.')

    if varPath == "L":
        # Now downloading all the files created on the device via scp
        print("\n")
        print("Step 4/5: Fetching the files created earlier")
        logging.info('Step 4/5: Fetching the files created earlier')
      
        logging.info('Info: Fetching RSI...')
        try:
            with SCPClient(ssh.get_transport(), sanitize=lambda x: x) as scp:
                scp.get(remote_path='/var/tmp/rsi-' + date_arg + '.txt',
                        local_path='./' + dir_root + '-' + varIP + '-' + date_arg + '/' + dir_rsi + '/')
        except:
            logging.info('Error: Could not fetch RSI - something went wrong...')
            scp.close()
        finally:
            logging.info('Info: RSI successfully fetched.')
            scp.close()
      
        logging.info('Info: Fetching Logfiles...')
        try:
            with SCPClient(ssh.get_transport(), sanitize=lambda x: x) as scp:
                scp.get(remote_path='/var/tmp/logfiles-' + date_arg + '.tgz',
                        local_path='./' + dir_root + '-' + varIP + '-' + date_arg + '/' + dir_logfiles + '/')
        except:
            logging.info('Error: Could not fetch Logfiles - something went wrong...')
            scp.close()
        finally:
            logging.info('Info: Logfiles successfully fetched.')
            scp.close()
      
        logging.info('Info: Fetching Configuration...')
        try:
            with SCPClient(ssh.get_transport(), sanitize=lambda x: x) as scp:
                scp.get(remote_path='/var/tmp/active-config-' + date_arg + '.txt',
                        local_path='./' + dir_root + '-' + varIP + '-' + date_arg + '/' + dir_config + '/')
        except:
            logging.info('Error: Could not fetch active Configuration - something went wrong...')
            scp.close()
        finally:
            logging.info('Info: Configuration successfully fetched.')
            scp.close()
      
        logging.info('Info: Now fetching the crash-dumps (core-dumps) if they exist...')
        try:
            with SCPClient(ssh.get_transport(), sanitize=lambda x: x) as scp:
                scp.get(remote_path='/var/crash/*',
                        local_path='./' + dir_root + '-' + varIP + '-' + date_arg + '/' + dir_core + '/')
        except:
            logging.info('Info: No crash-dumps (core-dumps) found - this is a good sign.')
            scp.close()
        finally:
            logging.info('Warning: crash-dumps (core-dumps) found and transferred...')
            scp.close()

        print("\n")
        print("Step 5/5: Deleting files from remote device to gain space back and finishing script")
        logging.info('Step 5/5: Deleting files from remote device to gain space back and finishing script')
        logging.info('Info: Deleting /var/tmp/rsi-' + date_arg + '.txt')
        channel.send('file delete /var/tmp/rsi-' + date_arg + '.txt\n')
        logging.info('Info: File deleted successfully.')
        time.sleep(2)
        logging.info('Info: Deleting /var/tmp/logfiles-' + date_arg + '.tgz')
        channel.send('file delete /var/tmp/logfiles-' + date_arg + '.tgz\n')
        logging.info('Info: File deleted successfully.')
        time.sleep(2)
        logging.info('Info: Deleting /var/tmp/active-config-' + date_arg + '.txt')
        channel.send('file delete /var/tmp/active-config-' + date_arg + '.txt\n')
        logging.info('Info: File deleted successfully.')
        resp = channel.recv(9999)
        output = resp.decode().split(',')
        # print(''.join(output)) #commented out so its not shown on the console (debug)
        time.sleep(1)
        ssh.close()
        time.sleep(1)
     
        shutil.make_archive('njs-package_' + varIP + '_' + date_arg, 'zip', dir_root + '-' + varIP + '-' + date_arg)
        shutil.rmtree(dir_root + '-' + varIP + '-' + date_arg, ignore_errors=True)
        print("\n")
        print("Finished!")
        pathdisplay = Path(__file__).parent.absolute()
        print("The file has been downloaded to: " + str(pathdisplay))
      
    elif varPath == "R":
        print("\n")
        print("Step 4/5 and 5/5: Skipping this steps because you selected that the file should remain on the box.")
        logging.info('Step 4/5 and 5/5: Skipping this steps because you selected that the file should remain on the box.')
        print("The package can be found at /var/tmp/")
        logging.info('The package can be found at /var/tmp/')
        print("\n")
        print("Finished!")
    else:
        print("\n")
        print("Error: Something went horribly wrong for reasons we do not know yet. Exiting...")
        logging.info('Error: Something went horribly wrong for reasons we do not know yet. Exiting...')


def main():
    loop_condition_main = True
    loop_condition_routing = True
    print(
        "  _  _     _      _                   ___       _ _        _____         _    \n | \\| |___| |_ __| |_  _ _ ___ _ _   |   \\ __ _(_) |_  _  |_   _|__  ___| |___\n | .` / -_)  _/ _| \' \\| \'_/ _ \\ \' \\  | |) / _` | | | || |   | |/ _ \\/ _ \\ (_-<\n |_|\\_\\___|\\__\\__|_||_|_| \\___/_||_| |___/\\__,_|_|_|\\_, |   |_|\\___/\\___/_/__/\n                                                    |__/                      ")
    print(
        "                                 ____\n                                / . .\\\n                                \\  ---<\n                                 \\  /\n                       __________/ /\n                    -=:___________/ developed by @chsjuniper\n")

    login_details()

    while loop_condition_main:
        print("#######################################")
        print("#             Main Menu               #")
        print("#######################################")
        print("Current Device: " + varIP)
        print("Current User: " + varUser)
        print(" ")
        print("[1] - Change Login Details / Switch Device")
        print("[2] - Collect Logs and RSI (Support-Information for JTAC) for Analysis")
        print("[3] - Routing Engine Menu")
        print("[4] - Spanning-Tree Menu")
        print("[5] - Routing Menu")
        print("[6] - Command Menu")
        print("[7] - Get Chassis Serialnumber")
        print("[9] - Exit the Tool")
        print(" ")
        loop_condition_routing = True
        loop_condition_engine = True
        loop_condition_spanning = True
        loop_condition_command = True
        main_input = int(input("Waiting for user input>> "))
        print("#######################################")
        print("\n")

        if main_input == 9:
            print("This tool was coded for you by Christian Scholz (@chsjuniper)")
            loop_condition_main = False
            break

        else:
            if main_input == 1:
                login_details()

            elif main_input == 2:
                njsupport()

            elif main_input == 3:
                while loop_condition_engine:
                    print("#######################################")
                    print("#        Routing Engine Menu          #")
                    print("#######################################")
                    print("Current Device: " + varIP)
                    print("Current User: " + varUser)
                    print(" ")
                    print("[1] - Check CPU Usage")
                    print("[2] - Get Device Infos")
                    print("[3] - Back")
                    print(" ")
                    main_input = int(input("Waiting for user input>> "))
                    print("#######################################")
                    print("\n")

                    if main_input == 3:
                        loop_condition_engine = False
                        break

                    else:
                        if main_input == 1:
                            chassis_re()
                        elif main_input == 2:
                            get_device()

            elif main_input == 4:
                while loop_condition_spanning:
                    print("#######################################")
                    print("#        Spanning Tree Menu           #")
                    print("#######################################")
                    print("Current Device: " + varIP)
                    print("Current User: " + varUser)
                    print(" ")
                    print("[1] - Check Interface Description")
                    print("[2] - Check Blocked Interfaces")
                    print("[3] - Unblock Interfaces")
                    print("[4] - Back")
                    print(" ")
                    main_input = int(input("Waiting for user input>> "))
                    print("#######################################")
                    print("\n")

                    if main_input == 4:
                        loop_condition_spanning = False
                        break

                    else:
                        if main_input == 1:
                            if_descr()
                        elif main_input == 2:
                            spanning_block()
                        elif main_input == 3:
                            spanning_unblock()

            elif main_input == 5:
                while loop_condition_routing:
                    print("#######################################")
                    print("#           Routing Menu              #")
                    print("#######################################")
                    print("Current Device: " + varIP)
                    print("Current User: " + varUser)
                    print(" ")
                    print("[1] - Check BGP Routes")
                    print("[2] - Check OSPF Neighbors")
                    print("[3] - BGP Advertisement checker")
                    print("[4] - Back")
                    print(" ")
                    main_input = int(input("Waiting for user input>> "))
                    print("#######################################")
                    print("\n")

                    if main_input == 4:
                        loop_condition_routing = False
                        break

                    else:
                        if main_input == 1:
                            bgp_summary()
                        elif main_input == 2:
                            ospf_neighbors()
                        elif main_input == 3:
                            bgp_adv()

            elif main_input == 6:
                while loop_condition_command:
                    print("#######################################")
                    print("#           Command Menu              #")
                    print("#######################################")
                    print("Current Device: " + varIP)
                    print("Current User: " + varUser)
                    print(" ")
                    print("[1] - Enable Netconf")
                    print("[2] - Disable Netconf")
                    print("[3] - Rollout vlan")
                    print("[4] - Back")
                    print(" ")
                    main_input = int(input("Waiting for user input>> "))
                    print("#######################################")
                    print("\n")

                    if main_input == 4:
                        loop_condition_command = False
                        break

                    else:
                        if main_input == 1:
                            enable_netconf()
                        elif main_input == 2:
                            disable_netconf()
                        elif main_input == 3:
                            set_vlan()

            elif main_input == 7:
                dev_script()


if __name__ == "__main__":
    main()
