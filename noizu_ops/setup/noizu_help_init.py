#!/usr/bin/env python3

import os
import platform
import datetime
import psutil
import yaml
import getpass
import grp
import subprocess
import rich.console




def get_linux_distro():
    try:
        # Attempt to parse /etc/os-release first
        distro_info = {}
        with open('/etc/os-release', 'r') as f:
            lines = f.readlines()
        for line in lines:
            parts = line.strip().split('=')
            if len(parts) == 2:
                key = parts[0].strip().lower()
                value = parts[1].strip().strip('"')
                distro_info[key] = value
        return distro_info
    except (FileNotFoundError, PermissionError):
        pass

    try:
        # Fallback to uname -a
        uname_info = subprocess.check_output(['uname', '-a']).decode('utf-8').strip().split()
        distro_info = {'os_type': uname_info[0], 'os_release': uname_info[2], 'os_version': uname_info[3]}
        return distro_info
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        pass

    try:
        # Fallback to parsing /proc/version
        with open('/proc/version', 'r') as f:
            version_info = f.readline().strip().split()
        distro_info = {'os_type': version_info[0], 'os_release': version_info[2], 'os_version': version_info[4]}
        return distro_info
    except (FileNotFoundError, PermissionError, IndexError):
        pass
    return None

def get_macos_version():
    try:
        version_info = subprocess.check_output(['sw_vers']).decode('utf-8')
        version_dict = {}
        for line in version_info.split('\n'):
            parts = line.strip().split(':')
            if len(parts) == 2:
                key, value = parts
                key = key.strip().replace(' ', '_').lower()
                value = value.strip()
                version_dict[key] = value
        return version_dict
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None

def get_windows_version():
    try:
        version_info = subprocess.check_output(['systeminfo']).decode('utf-8')
        version_dict = {}
        for line in version_info.split('\n'):
            parts = line.strip().split(':')
            if len(parts) == 2:
                key, value = parts
                key = key.strip().replace(' ', '_').lower()
                value = value.strip()
                version_dict[key] = value
        return version_dict
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None

def get_bsd_version():
    try:
        version_info = subprocess.check_output(['uname', '-v']).decode('utf-8')
        version_dict = {}
        parts = version_info.strip().split(':')
        if len(parts) == 2:
            key, value = parts
            key = key.strip().replace(' ', '_').lower()
            value = value.strip()
            version_dict[key] = value
        return version_dict
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None

def cpu_info__count():
    try:
        psutil.cpu_count(logical=True)
    except:
        None
def cpu_info__freq():
    try:
        psutil.cpu_freq().current
    except:
        None

def cpu_info__percent():
    try:
        psutil.cpu_percent()
    except:
        None


def system_info():
    rich.print("""
    [bold yellow]:information_desk_person: Hello this is Noizu-OPs, lets setup your system.[/bold yellow]   
    ---------------------------------------------------
    In order to tailor my responses to your devops experience level and 
    operating system we will scan your system to determine your OS, ram, 
    and other basic details. 
    
    :see_no_evil: Currently no information is sent to our servers, all of your data remains under ~/.noizu-ops/.
    
    But first let's get some details about you!
    
    
    
    """)

    system_info = {
        "os_type": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "os_name": os.name,
    }

    if system_info["os_type"] == "Linux":
        system_info["linux_info"] = get_linux_distro()
    elif system_info["os_type"] == "Darwin":
        system_info["osx_info"] = get_macos_version()
    elif platform.system() == 'Windows':
        system_info["win_info"] = get_windows_version()
    elif platform.system() in ['FreeBSD', 'NetBSD', 'OpenBSD']:
        system_info["bsd_info"] = get_bsd_version()

    # Get CPU information
    cpu_info = {
        "cpu_count": cpu_info__count(),
        "cpu_freq": cpu_info__freq(),
        "cpu_percent": cpu_info__percent()
    }

    # Get RAM information
    try:
        ram_info = {
            "total_memory": round(psutil.virtual_memory().total / (1024.0 ** 3), 2),
            "available_memory": round(psutil.virtual_memory().available / (1024.0 ** 3), 2),
            "used_memory": round(psutil.virtual_memory().used / (1024.0 ** 3), 2),
            "memory_percent": psutil.virtual_memory().percent
        }
    except:
        ram_info = None

    # Get disk information
    try:
        disk_info = {
            "total_disk_space": round(psutil.disk_usage('/').total / (1024.0 ** 3), 2),
            "used_disk_space": round(psutil.disk_usage('/').used / (1024.0 ** 3), 2),
            "free_disk_space": round(psutil.disk_usage('/').free / (1024.0 ** 3), 2),
            "disk_percent": psutil.disk_usage('/').percent
        }
    except:
        disk_info = None

    # Get current user and groups
    current_user = getpass.getuser()
    name = input("Enter your name: ")
    if name == '':
        name = current_user
    email = input("Enter your email address: ")
    experience_level = input("Enter your experience level (0 - Novice, 1 - Beginner, *2 - Intermediate, 3 - Advanced, 4 - Expert): ")
    if experience_level == '':
        skill_level = "2 - Intermediate"
    else:
        skill_level_names = ["0 - Novice", "1 - Beginner", "2 - Intermediate", "3 - Advanced", "4- Expert"]
        skill_level = skill_level_names[int(experience_level)]

    tailor_prompt = """
    Hello Everyone, I am looking forward to working with you! Please do you best to guide and assist me in maintaining this system and finding cool and useful information and online resources!
    """

    user_info = {
        "name": name,
        "email": email,
        "tailor_prompt": tailor_prompt,
        "skill_level": skill_level,
        "current_user": current_user,
        "user_groups": [grp.getgrgid(gid).gr_name for gid in os.getgroups()]
    }

    openai_key = input("Enter your OpenAI Key: [if blank I will use $OPENAI_API_KEY]")
    if openai_key == '':
        openai_key = None
    openai_model = input("Enter your OpenAI Model: [if blank I will use NOIZU_OPS_MODEL or 'gpt3.5-turbo']")
    if openai_model == '':
        openai_model = None

    # Combine all information
    system_config = {
        "config": {
            "required": False,
            "version": "0.1.0",
            "last-update": datetime.datetime.now(),
            "editor": "vim"
        },
        "system_info": system_info,
        "cpu_info": cpu_info,
        "ram_info": ram_info,
        "disk_info": disk_info,
        "user_info": user_info,
        "credentials": {
            "openai_key": openai_key,
            "model": openai_model
        }
    }

    rich.print(
    """
    [bold yellow]:information_desk_person: Fantastic, here's what we got. [/bold yellow]    
    -------------------------
    """)

    console = rich.console.Console()
    md = f"""
```yaml
{yaml.dump(system_config, sort_keys=False)}
```
    """
    console.print(rich.markdown.Markdown(md, justify="left"))

    rich.print(
    """
    you can edit your saved settings by opening `~/.noizu-ops/user-settings.yml` or running `noizu-ops init`.\n\n\n\n
    """)
    return system_config

def update_config(si):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    noizu_dir = os.path.dirname(script_dir)

    os.makedirs(os.path.join(os.path.expanduser('~'), ".noizu-ops"), exist_ok=True)
    config_dir = os.path.join(os.path.expanduser('~'), ".noizu-ops")
    config_file = os.path.join(config_dir, "user-settings.yml")

    # Create the directory if it doesn't exist
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # Write the information to a YAML file
    with open(config_file, 'w') as file:
        yaml.dump(si, file)
    return si

def main():
    si = system_info()
    update_config(si)

if __name__ == "__main__":
    system_config = main()