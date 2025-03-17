from dialog import Dialog
import locale, os, time

locale.setlocale(locale.LC_ALL, '')
d = Dialog(dialog="dialog")
d.set_background_title("EIT STREAM SERVICE MANAGEMENT")

try:
    os.mkdir(f"{os.getcwd()}/scan-scripts")
    os.mkdir(f"{os.getcwd()}/scan-files")
except:
    pass


###
### EIT STREAM SERVICE MANAGEMENT TOOL
###

# FILE CONNECTION
class File():
    def __init__(self, name):
        self.name = name

    def read(self):
        with open(self.name, "r") as f:
            return f.read()

    def write(self, content):
        with open(self.name, "w") as f:
            return f.write(content)

# ROOT/SUDO CHECKER
def prompt_sudo():
    if os.getuid() != 0:
        print("No root permission detected. Stop.")
        exit()


#
# SYSTEMCTL FILES
#

# SCAN SERVICE
def create_sys(name, source, scan_d, sleep_d):

    if "http://" in source:
        command = f"curl {source} --output - | {os.getcwd()}/libdvbtee/dvbtee/dvbtee -t{scan_d} -e -E -d3 2> {os.getcwd()}/scan-files/{name.lower()}"
    else:
        command = f"{os.getcwd()}/libdvbtee/dvbtee/dvbtee -i{source} -t{scan_d} -e -E -d3 2> {os.getcwd()}/scan-files/{name.lower()}"

    File(f"{os.getcwd()}/scan-scripts/{name.lower()}.sh").write("#!/bin/bash\nwhile true; do if [ ! -f "+os.getcwd()+"/scan-files/"+name.lower()+"_final ]; then "+command+f"; mv "+f"{os.getcwd()}/scan-files/{name.lower()}"+" "+f"{os.getcwd()}/scan-files/{name.lower()}_final"+f"; else sleep 60; fi; sleep {sleep_d}; done")

    content = \
        f"""[Unit]
Description=EIT scanner for {name}
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory={os.getcwd()}

User=root
Group=root

Restart=always
RestartSec=10

ExecStart=bash {f'{os.getcwd()}/scan-scripts/{name.lower()}.sh'}"""

    File(f"/lib/systemd/system/eitscan-{name.lower()}.service").write(content)
    os.system("systemctl daemon-reload")
    os.system(f"systemctl start eitscan-{name.lower()}")


# GRABBER SERVICE
def create_xmlsys(ext_days):

    content = \
        f"""[Unit]
Description=XMLTV Grabber for EIT files
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory={os.getcwd()}

User=root
Group=root

Restart=always
RestartSec=10

ExecStart=python3 {f'{os.getcwd()}/create.py'} 'days={str(ext_days)}'"""

    File(f"/lib/systemd/system/eit-xmltv-grabber.service").write(content)
    os.system("systemctl daemon-reload")
    os.system(f"systemctl restart eit-xmltv-grabber.service")


#
# DVBTEE INSTALLER
#

def install_dvbtee():
    os.system("clear")
    if os.path.exists("libdvbtee"):
        os.system("rm -rf libdvbtee")
    os.system("apt install git autoconf libtool pkg-config")
    os.system("git clone https://github.com/mkrufky/libdvbtee")
    os.system("cd libdvbtee && ./build-auto.sh && cd -")
    if os.path.exists("libdvbtee/dvbtee/dvbtee"):
        d.msgbox("dvbtee has been installed!")
    else:
        input("Failed to install dvbtee. Press enter to continue...")

# DVBTEE SCAN SERVICE CREATOR
def add_dvbtee_scan():
    d.set_background_title("EIT STREAM SERVICE MANAGEMENT > DVBTEE > ADD")
    
    # NAME 
    while True:
        code, name = d.inputbox("Please enter a name for your EIT mux source.\n\nOnly letters and numbers are allowed.", width=60)
        f = os.listdir(f"{os.getcwd()}/scan-scripts")
        if not name:
            return
        if name+".sh" in f:
            d.msgbox("ERROR: The name already exists\n\nPlease try again.")
            continue
        if not name.isalnum():
            d.msgbox("ERROR: Invalid name\n\nPlease try again.")
            continue
        break    

    # SOURCE
    while True:
        code, source = d.inputbox("Please enter your EIT mux source.\n\nAllowed sources:\nhttp://, udp://, rdp://", width=60)
        if not source:
            return
        if not any(["http://" in source, "udp://" in source, "tcp://" in source]):
            d.msgbox("ERROR: Invalid address\n\nPlease try again.")
            continue
        break
    
    # SCAN DURATION
    while True:
        code, scan_duration = d.inputbox("Please enter the scan duration (in seconds).\n\nAllowed input:\nmin. 10", width=60)
        if not scan_duration:
            return
        try:
            if int(scan_duration) < 10:
                d.msgbox("ERROR: Invalid number\n\nPlease try again.")
                continue
        except:
            d.msgbox("ERROR: Invalid input\n\nPlease try again.")
            continue
        break

    # SLEEP DURATION
    while True:
        code, sleep_duration = d.inputbox("Please enter the sleep duration (in seconds).\n\nAllowed input:\nmin. 10", width=60)
        if not sleep_duration:
            return
        try:
            if int(sleep_duration) < 10:
                d.msgbox("ERROR: Invalid number\n\nPlease try again.")
                continue
        except:
            d.msgbox("ERROR: Invalid input\n\nPlease try again.")
            continue
        break

    # INIT COMMAND
    try:
        os.remove(f"{os.getcwd()}/scan-files/--test--")
    except:
        pass

    if "http://" in source:
        command = f"curl {source} --output - | {os.getcwd()}/libdvbtee/dvbtee/dvbtee -t10 -e -E -d3 2> {os.getcwd()}/scan-files/--test--"
    else:
        command = f"{os.getcwd()}/libdvbtee/dvbtee/dvbtee -i{source} -t10 -e -E -d3 2> {os.getcwd()}/scan-files/--test--"
    
    os.system("clear")
    os.system("echo 'Testing your source, please wait...\n' && sleep 3")
    os.system(command)
    
    if os.path.exists(f"{os.getcwd()}/scan-files/--test--") and "[EIT]::store" in str(File(f"{os.getcwd()}/scan-files/--test--").read()):
        os.system("echo '\nThe test was successful. Creating systemctl service...\n' && sleep 3")
    else:
        os.system("echo '\nFailed to validate the source. Stop.\n' && sleep 3")

    create_sys(name, source, scan_duration, sleep_duration)
    d.msgbox("The service has been established.")
    os.remove(f"{os.getcwd()}/scan-files/--test--")


# DVBTEE SCAN SERVICE MANAGER
def manage_dvbtee_scan():
    d.set_background_title("EIT STREAM SERVICE MANAGEMENT > DVBTEE > MANAGE")
    f = os.listdir(f"{os.getcwd()}/scan-scripts")
    
    if not f:
        d.msgbox("There are no services to be managed!")
        return


    service_removed = False

    while True:

        if service_removed:
            break

        choices = []
        status_values = []
        for n, i in enumerate(f):
            name = i.replace(".sh", "")
            status = os.system(f'systemctl is-active --quiet eitscan-{name}')
            name = "[STOPPED] " + name if status == 768 else "[RUNNING] " + name if status == 0 else name
            status_values.append(status)
            choices.append((f'({str(n+1)})', name.upper()))
        
        d.set_background_title("EIT STREAM SERVICE MANAGEMENT > DVBTEE > MANAGE")

        code, tag = d.menu("Please select an instance to be managed:",
                        choices=choices)
    
        if not tag:
            break
        
        tag = int(tag.replace("(", "").replace(")", ""))-1
            
        while True:
        
            d.set_background_title(f"EIT STREAM SERVICE MANAGEMENT > DVBTEE > MANAGE > {f[tag].replace(".sh", "").upper()}")
        
            code, tag_2 = d.menu("Please select an option:",
                                choices=[("(1)", "Stop service" if status_values[tag] == 0 else "Start service"),
                                         ("(2)", "Check systemctl status output"),
                                         ("(3)", "Change scan/sleep durations"),
                                         ("(4)", "Remove service")])

            if tag_2 == "(1)":
                if status_values[tag] == 0:
                    os.system(f'systemctl stop eitscan-{f[tag].replace(".sh", "")}')
                    status_values[tag] = 768
                else:
                    os.system(f'systemctl start eitscan-{f[tag].replace(".sh", "")}')
                    status_values[tag] = 0

            elif tag_2 == "(2)":
                os.system("clear")
                os.system(f'systemctl status eitscan-{f[tag].replace(".sh", "")}')
                input("Press any key to continue...")

            elif tag_2 == "(3)":
                d.set_background_title(f"EIT STREAM SERVICE MANAGEMENT > DVBTEE > MANAGE > {f[tag].replace(".sh", "").upper()} > EDIT")
                
                # SCAN DURATION
                while True:
                    code, scan_duration = d.inputbox("Please enter the scan duration (in seconds).\n\nAllowed input:\nmin. 10", width=60)
                    if not scan_duration:
                        return
                    try:
                        if int(scan_duration) < 10:
                            d.msgbox("ERROR: Invalid number\n\nPlease try again.")
                            continue
                    except:
                        d.msgbox("ERROR: Invalid input\n\nPlease try again.")
                        continue
                    break

                if not scan_duration:
                    break

                # SLEEP DURATION
                while True:
                    code, sleep_duration = d.inputbox("Please enter the sleep duration (in seconds).\n\nAllowed input:\nmin. 10", width=60)
                    if not sleep_duration:
                        return
                    try:
                        if int(sleep_duration) < 10:
                            d.msgbox("ERROR: Invalid number\n\nPlease try again.")
                            continue
                    except:
                        d.msgbox("ERROR: Invalid input\n\nPlease try again.")
                        continue
                    break

                if not sleep_duration:
                    break
                
                if status_values[tag] == 0:
                    os.system(f'systemctl stop eitscan-{f[tag].replace(".sh", "")}')
                os.system(f"sed -i 's/-t.* -e -E/-t{str(scan_duration)} -e -E/g' {os.getcwd()}/scan-scripts/{f[tag]}")
                os.system(f"sed -i 's/sleep .*; done/sleep {str(sleep_duration)}; done/g' {os.getcwd()}/scan-scripts/{f[tag]}")
                if status_values[tag] == 0:
                    os.system(f'systemctl start eitscan-{f[tag].replace(".sh", "")}')
                d.msgbox("The service has been updated.")
                break

            elif tag_2 == "(4)":
                d.set_background_title(f"EIT STREAM SERVICE MANAGEMENT > DVBTEE > MANAGE > {f[tag].replace(".sh", "").upper()} > REMOVE")
                os.system(f'systemctl stop eitscan-{f[tag].replace(".sh", "")}')
                os.system(f"rm /lib/systemd/system/eitscan-{f[tag].replace(".sh", "")}.service")
                os.system(f"rm {os.getcwd()}/scan-scripts/{f[tag]}")
                os.system("systemctl daemon-reload")
                service_removed = True
                d.msgbox("The service has been removed.")
                break

            else:
                break


#
# XMLTV SERVICE CREATOR
#

def install_grabber():
    d.set_background_title("EIT STREAM SERVICE MANAGEMENT > XMLTV GRABBER > ADD")
    
    # EXTENDED GUIDE DATA
    while True:
        code, ext_days = d.inputbox("Please enter the time period for extended guide data\n(in days).\n", width=60)
        if not ext_days:
            return
        try:
            if int(ext_days) <= 0:
                d.msgbox("ERROR: Invalid number\n\nPlease try again.")
                continue
        except:
            d.msgbox("ERROR: Invalid input\n\nPlease try again.")
            continue
        break

    create_xmlsys(ext_days)
    d.msgbox("The service has been established.")

# XMLTV GRABBER SERVICE MANAGER
def manage_grabber():
    d.set_background_title("EIT STREAM SERVICE MANAGEMENT > XMLTV GRABBER > MANAGE")

    while True:

        status = os.system(f'systemctl is-active --quiet eit-xmltv-grabber')
    
        code, tag_1 = d.menu("Please select an option:",
                            choices=[("(1)", "Stop service" if status == 0 else "Start service"),
                                     ("(2)", "Check systemctl status output"),
                                     ("(3)", "Remove service")])
        
        if tag_1 == "(1)":
            if status == 0:
                os.system(f'systemctl stop eit-xmltv-grabber')
                status = 768
            else:
                os.system(f'systemctl start eit-xmltv-grabber')
                status = 0

        elif tag_1 == "(2)":
            os.system("clear")
            os.system(f'systemctl status eit-xmltv-grabber')
            input("Press any key to continue...")

        elif tag_1 == "(3)":
            d.set_background_title(f"EIT STREAM SERVICE MANAGEMENT > XMLTV GRABBER > MANAGE > REMOVE")
            os.system(f'systemctl stop eit-xmltv-grabber')
            os.system(f"rm /lib/systemd/system/eit-xmltv-grabber.service")
            os.system("systemctl daemon-reload")
            d.msgbox("The service has been removed.")
            break

        else:
            break


# #######################
# RUN SCRIPT
# #######################

# CHECK FOR ROOT
if prompt_sudo() != 0:
    pass

# DIALOG
while True:
    d.set_background_title("EIT STREAM SERVICE MANAGEMENT")

    code, tag = d.menu("Please select a tool to manage:",
                        choices=[("(1)", "Dvbtee service instances"),
                                 ("(2)", "XMLTV Grabber instance")])

    if tag == "(1)":
        while True:
            d.set_background_title("EIT STREAM SERVICE MANAGEMENT > DVBTEE")

            if os.path.exists("libdvbtee/dvbtee/dvbtee"):
                code, tag = d.menu("Please select an option:",
                                    choices=[("(1)", "Re-install dvbtee"),
                                             ("(2)", "Add new scan service"),
                                             ("(3)", "Manage existing scan services")])
            else:
                code, tag = d.menu("Please select an option:",
                                    choices=[("(1)", "Install dvbtee")])

            if tag == "(1)":
                install_dvbtee()

            elif tag == "(2)":
                add_dvbtee_scan()

            elif tag == "(3)":
                manage_dvbtee_scan()
        
            else:
                break

    elif tag == "(2)":
        while True:
            d.set_background_title("EIT STREAM SERVICE MANAGEMENT > XMLTV GRABBER")

            if os.path.exists("/lib/systemd/system/eit-xmltv-grabber.service"):
                code, tag = d.menu("Please select an option:",
                                    choices=[("(1)", "Re-install grabber"),
                                             ("(2)", "Manage grabber service")])
            else:
                code, tag = d.menu("Please select an option:",
                                    choices=[("(1)", "Install grabber")])

            if tag == "(1)":
                install_grabber()

            elif tag == "(2)":
                manage_grabber()
        
            else:
                break
    
    else:
        break

os.system("clear")