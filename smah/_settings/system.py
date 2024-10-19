import os
import platform
import textwrap
import yaml
import datetime
import subprocess
import psutil
from attr.converters import optional
from prompt_toolkit.layout import is_container

from rich.prompt import Prompt, Confirm
from rich.console import Console

class System:
    YAML_VERSION = "0.0.1"

    @staticmethod
    def version_supported(version):
        if version is None:
            return False
        else:
            return version <= System.YAML_VERSION

    def __init__(self, config_data):
        self.errors = []
        self.disk = System.DiskStats()
        self.cpu = System.CpuStats()
        self.memory = System.MemoryStats()

        if config_data is not None:
            config_data = config_data["os"] if "os" in config_data else None

        if config_data is None:
            self.errors = ["System data is missing"]
            self.type = None
            self.name = None
            self.version = None
            self.release = None
            self.info = None
            self.vsn = None
        else:
            self.type = config_data["type"] if "type" in config_data else None
            self.name = config_data["name"] if "name" in config_data else None
            self.version = config_data["version"] if "version" in config_data else None
            self.release = config_data["release"] if "release" in config_data else None
            self.info = self.load_info(config_data["info"] if "info" in config_data else None)
            self.vsn = config_data["vsn"] if "vsn" in config_data else None

        if not self.errors:
            self.errors = None

        self.configured = None
        self.configured = self.is_configured()

    def status(self):
        info = self.info.status() if self.info is not None else None

        cpu = self.cpu.status() if self.status is not None else None
        memory = self.memory.status() if self.memory is not None else None
        disk = self.disk.status() if self.disk is not None else None

        status = textwrap.dedent(f"""
           ### OS
           - type: {self.type}
           - name: {self.name}
           - version: {self.version}
           - release: {self.release}
           - info:
           """)
        status += textwrap.indent(info or "N/A", "  ")
        status += "\n\n### CPU\n"
        status += cpu or "N/A"
        status += "\n\n### Memory\n"
        status += memory or "N/A"
        status += "\n\n### Disk\n"
        status += disk or "N/A"

        return textwrap.dedent(status).strip()



    def is_configured(self):
        if (self.configured is None):
            return not(self.type is None or self.release is None or self.version is None or self.name is None or self.vsn is None)
        else:
            return self.configured

    def os_details(self):
        type = None
        release = None
        version = None
        name = None
        try:
            type = platform.system()
            release = platform.release()
            version = platform.version()
            name = os.name
        except Exception as e:
            print("error")
            pass

        return {
            "type": type,
            "release": release,
            "version": version,
            "name": name,
        }

    def terminal_configure(self, console):
        self.errors = []
        auto = Confirm.ask("Would you like me to automatically setup your system details", default=True)
        os_details = self.os_details()
        if auto:
            self.type = os_details["type"] if "type" in os_details else None
            self.name = os_details["name"] if "name" in os_details else None
            self.version = os_details["version"] if "version" in os_details else None
            self.release = os_details["release"] if "release" in os_details else None
            self.info = self.prompt_info(self.type)
        else:
            self.type = self.prompt_type(console, os_details["type"] if "type" in os_details else None)
            self.name = self.prompt_name(console, os_details["name"] if "name" in os_details else None)
            self.version = self.prompt_version(console, os_details["version"] if "version" in os_details else None)
            self.release = self.prompt_release(console, os_details["release"] if "release" in os_details else None)
            auto = Confirm.ask("Would you like me to automatically load your OS specific details", default=True)
            if auto:
                self.info = self.prompt_info(self.type)
            else:
                self.info = None

            console.print("...")

        if not self.errors:
            self.errors = None

        self.configured = None
        self.configured = self.is_configured()

    def to_yaml(self, options = {}):
        system = {
            "vsn": self.vsn if self.vsn is not None else System.YAML_VERSION,
            "type": self.type,
            "name": self.name,
            "version": self.version,
            "release": self.release,
            "info": self.info.to_yaml(options = options) if self.info is not None else None,
        }




        if "stats" in options and options["stats"]:
            return {
                "vsn": System.YAML_VERSION,
                "os": system,
                "cpu": self.cpu.readings(),
                "memory": self.memory.readings(),
                "disk": self.disk.readings(),
            }
        else:
            return {
                "vsn": System.YAML_VERSION,
                "os": system,
            }

    def prompt_type(self, console, type):
        default_type = None
        default_bsd_type = None
        if type is not None:
            if type == "Linux":
                default_type = "1"
            elif type == "Darwin":
                default_type = "2"
            elif type == "Windows":
                default_type = "3"
            elif type in ["FreeBSD", "OpenBSD", "NetBSD"]:
                default_type = "4"
                if type == "FreeBSD":
                    default_bsd_type = "1"
                elif type == "OpenBSD":
                    default_bsd_type = "2"
                elif type == "NetBSD":
                    default_bsd_type = "3"


        os_type_message = textwrap.dedent(
            """
            [bold green]What is your os type?[/bold green]
            1 - Linux
            2 - MacOS (Darwin)
            3 - Windows
            4 - BSD
            """
        )
        types = {
            "1": "Linux",
            "2": "Darwin",
            "3": "Windows",
            "4": "BSD",
        }
        bsd_type_message = textwrap.dedent(
            """
            [bold green]What is your BSD flavor?[/bold green]
            1 - FreeBSD
            2 - OpenBSD
            3 - NetBSD
            """
        )
        bsd_types = {
            "1": "FreeBSD",
            "2": "OpenBSD",
            "3": "NetBSD",
        }


        if self.type is None:
            type = Prompt.ask(os_type_message, choices=["1", "2", "3", "4"], default = default_type)
            v = types[type]
            if v == "BSD":
                bsd_type = Prompt.ask(bsd_type_message, choices=["1", "2", "3"], default=default_bsd_type)
                return bsd_types[bsd_type]
            else:
                return v
        else:
            type_name = "MacOs (Darwin)" if self.type == "Darwin" else self.type

            console.print(f"OS Type: {type_name}")
            if Confirm.ask("correct?", default=False):
                return self.type
            else:
                type = Prompt.ask(os_type_message, choices=["1", "2", "3", "4"], default = default_type)
                v = types[type]
                if v == "BSD":
                    bsd_type = Prompt.ask(bsd_type_message, choices=["1", "2", "3"], default=default_bsd_type)
                    return bsd_types[bsd_type]
                else:
                    return v

    def prompt_release(self, console, release):
        message = "[bold green]What is your Os Release?[/bold green]"
        if self.release is None:
            return Prompt.ask(message, default=release)
        else:
            console.print(f"Release: {self.release}")
            if Confirm.ask("correct?", default=False):
                return self.release
            else:
                return Prompt.ask(message, default=release)

    def prompt_version(self, console, version):
        message = "[bold green]What is your OS Version[/bold green]"
        if self.version is None:
            return Prompt.ask(message, default=version)
        else:
            console.print(f"OS Version: {self.version}")
            if Confirm.ask("correct?", default=False):
                return self.version
            else:
                return Prompt.ask(message, default=version)

    def prompt_name(self, console, name):
        message = "[bold green]What is your OS Name[/bold green]"
        if self.name is None:
            return Prompt.ask(message, default=name)
        else:
            console.print(f"OS Name: {self.name}")
            if Confirm.ask("correct?", default=False):
                return self.name
            else:
                return Prompt.ask(message, default=name)

    def prompt_info(self, type):
        if type == "Linux":
            return System.LinuxDetails(None, fetch=True)
        elif type == "Darwin":
            return System.DarwinDetails(None, fetch=True)
        elif type == "Windows":
            return System.WindowsDetails(None, fetch=True)
        elif type in ["FreeBSD", "OpenBSD", "NetBSD"]:
            return System.BSDDetails(None, fetch=True)
        else:
            return None

    def load_info(self, config_data):
        if config_data is None:
            return None
        else:
            kind = config_data["kind"] if "kind" in config_data else None
            if kind is None:
                return None
            elif kind == "Linux":
                return System.LinuxDetails(config_data)
            elif kind == "Darwin":
                return System.DarwinDetails(config_data)
            elif kind == "Windows":
                return System.WindowsDetails(config_data)
            elif kind == "BSD":
                return System.BSDDetails(config_data)
            else:
                return None

    class CpuStats:

        @staticmethod
        def cpu_info(reading):
            try:
                if reading == "count":
                    return psutil.cpu_count(logical=True)
                elif reading == "freq.current":
                    return round(psutil.cpu_freq().current, 2)
                elif reading == "percent":
                    return round(psutil.cpu_percent(), 2)
            except:
                return None


        def __init__(self):
            self.time_stamp = None
            self.last_cpu_count = None
            self.last_cpu_freq = None
            self.last_cpu_percent = None

        def status(self):
            reading = self.readings()
            r = f"""
            - time: {reading["time"]}
            - count: {reading["cpu_count"]}
            - freq: {reading["cpu_freq"]}
            - percent: {reading["cpu_percent"]}
            """
            return textwrap.dedent(r).strip()

        def update(self):
            self.time_stamp = datetime.datetime.now()
            self.last_cpu_count = System.CpuStats.cpu_info("count")
            self.last_cpu_freq = System.CpuStats.cpu_info("freq.current")
            self.last_cpu_percent = System.CpuStats.cpu_info("percent")

        def stale(self, threshold):
            if self.time_stamp is None:
                return True
            else:
                return (datetime.datetime.now().microsecond - self.time_stamp.microsecond) > threshold

        def readings(self, threshold = 100):
            if self.stale(threshold):
                self.update()
            return {
                "time": self.time_stamp,
                "cpu_count": self.last_cpu_count,
                "cpu_freq": self.last_cpu_freq,
                "cpu_percent": self.last_cpu_percent
            }


    class DiskStats:

        @staticmethod
        def disk_info(reading):
            try:
                if reading == "total":
                    return round(psutil.disk_usage('/').total / (1024.0 ** 3), 2)
                elif reading == "available":
                    return round(psutil.disk_usage('/').free / (1024.0 ** 3), 2)
                elif reading == "used":
                    return round(psutil.disk_usage('/').used / (1024.0 ** 3), 2)
                elif reading == "percent":
                    return round(psutil.disk_usage('/').percent, 2)
            except Exception as e:
                return None

        def __init__(self):
            self.time_stamp = None
            self.last_total = None
            self.last_available = None
            self.last_used = None
            self.last_percent = None

        def status(self):
            reading = self.readings()
            r = f"""
            - time: {reading["time"]}
            - total: {reading["total"]}
            - free: {reading["available"]}
            - used: {reading["used"]}
            - percent: {reading["percent"]}
            """
            return textwrap.dedent(r).strip()

        def update(self):
            self.time_stamp = datetime.datetime.now()
            self.last_total = System.DiskStats.disk_info("total")
            self.last_available = System.DiskStats.disk_info("available")
            self.last_used = System.DiskStats.disk_info("used")
            self.last_percent = System.DiskStats.disk_info("percent")

        def stale(self, threshold):
            if self.time_stamp is None:
                return True
            else:
                return (datetime.datetime.now().microsecond - self.time_stamp.microsecond) > threshold

        def readings(self, threshold=100):
            if self.stale(threshold):
                self.update()
            return {
                "time": self.time_stamp,
                "total": self.last_total,
                "available": self.last_available,
                "used": self.last_used,
                "percent": self.last_percent
            }

    class MemoryStats:

        @staticmethod
        def memory_info(reading):
            try:
                if reading == "total":
                    return round(psutil.virtual_memory().total / (1024.0 ** 3), 2)
                elif reading == "available":
                    return round(psutil.virtual_memory().available / (1024.0 ** 3), 2)
                elif reading == "used":
                    return round(psutil.virtual_memory().used / (1024.0 ** 3), 2)
                elif reading == "percent":
                    return psutil.virtual_memory().percent
            except:
                return None

        def __init__(self):
            self.time_stamp = None
            self.last_total = None
            self.last_available = None
            self.last_used = None
            self.last_percent = None

        def status(self):
            reading = self.readings()
            r = f"""
            - time: {reading["time"]}
            - total: {reading["total"]}
            - free: {reading["available"]}
            - used: {reading["used"]}
            - percent: {reading["percent"]}
            """
            return textwrap.dedent(r).strip()

        def update(self):
            self.time_stamp = datetime.datetime.now()
            self.last_total = System.MemoryStats.memory_info("total")
            self.last_available = System.MemoryStats.memory_info("available")
            self.last_used = System.MemoryStats.memory_info("used")
            self.last_percent = System.MemoryStats.memory_info("percent")

        def stale(self, threshold):
            if self.time_stamp is None:
                return True
            else:
                return (datetime.datetime.now().microsecond - self.time_stamp.microsecond) > threshold

        def readings(self, threshold=100):
            if self.stale(threshold):
                self.update()
            return {
                "time": self.time_stamp,
                "total": self.last_total,
                "available": self.last_available,
                "used": self.last_used,
                "percent": self.last_percent
            }

    class LinuxDetails:
        YAML_VERSION = "0.0.1"

        @staticmethod
        def os_release_details():
            try:
                # Attempt to parse /etc/os-release first
                distro_info = {}
                with open('/etc/os-release', 'r') as f:
                    lines = f.readlines()
                for line in lines:
                    parts = line.strip().split('=')
                    if len(parts) == 2:
                        key = parts[0].strip().lower().replace('_','-')
                        value = parts[1].strip().strip('"')
                        distro_info[key] = value
                return "os_release", distro_info
            except (FileNotFoundError, PermissionError):
                return None

        @staticmethod
        def uname_details():
            try:
                uname_info = subprocess.check_output(['uname', '-a']).decode('utf-8').strip().split()
                distro_info = {'os_type': uname_info[0], 'os_release': uname_info[2], 'os_version': uname_info[3]}
                return "uname", distro_info
            except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
                return None

        @staticmethod
        def proc_details():
            try:
                # Fallback to parsing /proc/version
                with open('/proc/version', 'r') as f:
                    version_info = f.readline().strip().split()
                distro_info = {'os_type': version_info[0], 'os_release': version_info[2], 'os_version': version_info[4]}
                return "proc", distro_info
            except (FileNotFoundError, PermissionError, IndexError):
                return None

        def __init__(self, config_data, fetch=False):
            self.errors = []
            self.source = None
            self.details = {}
            self.vsn = None

            if fetch:
                details = System.LinuxDetails.os_release_details() or System.LinuxDetails.uname_details() or System.LinuxDetails.proc_details()
                if details is not None:
                    self.vsn = System.LinuxDetails.YAML_VERSION
                    self.source, self.details = details
            elif config_data is not None:
                    self.vsn = config_data["vsn"] if "vsn" in config_data else None
                    self.source = config_data["source"] if "source" in config_data else None
                    self.details = config_data["details"] if "details" in config_data else None

            if not self.errors:
                self.errors = None

            self.configured = None
            self.configured = self.is_configured()


        def status(self):
            details = "\n".join(f"- {key}: {value}" for key, value in (self.details or {}).items())
            details = textwrap.indent(details, "  ")
            r = textwrap.dedent(f"""
            - source: {self.source}            
            - details:
            """).strip()
            r += "\n" + details
            return textwrap.dedent(r).strip()

        def is_configured(self):
            if (self.configured is None):
                return True
            else:
                return self.configured

        def to_yaml(self, options = {}):
            return {
                "vsn": self.vsn if self.vsn is not None else System.LinuxDetails.YAML_VERSION,
                "kind": "Linux",
                "source": self.source,
                "details": self.details,
            }

    class DarwinDetails:
        YAML_VERSION = "0.0.1"

        @staticmethod
        def darwin_details():
            try:
                version_info = subprocess.check_output(['sw_vers']).decode('utf-8')
                version_dict = {}
                for line in version_info.split('\n'):
                    parts = line.strip().split(':')
                    if len(parts) == 2:
                        key, value = parts
                        key = key.strip().replace(' ', '-').lower()
                        value = value.strip()
                        version_dict[key] = value
                return "sw_vers", version_dict
            except (subprocess.CalledProcessError, FileNotFoundError):
                return None

        def __init__(self, config_data, fetch=False):
            self.errors = []
            self.source = None
            self.details = {}
            self.vsn = None

            if fetch:
                details = System.DarwinDetails.darwin_details()
                if details is not None:
                    self.vsn = System.DarwinDetails.YAML_VERSION
                    self.source, self.details = details
            elif config_data is not None:
                self.vsn = config_data["vsn"] if "vsn" in config_data else None
                self.source = config_data["source"] if "source" in config_data else None
                self.details = config_data["details"] if "details" in config_data else None

            if not self.errors:
                self.errors = None

            self.configured = None
            self.configured = self.is_configured()


        def status(self):
            details = "\n".join(f"{key}: {value}" for key, value in (self.details or {}).items())
            details = textwrap.indent(details, "  ")
            r = f"""
            - source: {self.source}
            - details:
            {details}
            """
            return textwrap.dedent(r).strip()

        def is_configured(self):
            if (self.configured is None):
                return True
            else:
                return self.configured

        def to_yaml(self):
            return {
                "vsn": self.vsn if self.vsn is not None else System.DarwinDetails.YAML_VERSION,
                "kind": "Darwin",
                "source": self.source,
                "details": self.details,
            }


    class BSDDetails:
        YAML_VERSION = "0.0.1"

        @staticmethod
        def uname_details():
            try:
                version_info = subprocess.check_output(['uname', '-v']).decode('utf-8')
                version_dict = {}
                parts = version_info.strip().split(':')
                if len(parts) == 2:
                    key, value = parts
                    key = key.strip().replace(' ', '-').lower()
                    value = value.strip()
                    version_dict[key] = value
                return "uname", version_dict
            except (subprocess.CalledProcessError, FileNotFoundError):
                return None

        def __init__(self, config_data, fetch=False):
            self.errors = []
            self.source = None
            self.details = {}
            self.vsn = None
            if config_data is not None:
                self.vsn = config_data["vsn"] if "vsn" in config_data else None

            if fetch:
                details = System.BSDDetails.uname_details()
                if details is not None:
                    self.vsn = System.BSDDetails.YAML_VERSION
                    self.source, self.details = details
            elif config_data is not None:
                self.vsn = config_data["vsn"] if "vsn" in config_data else None
                self.source = config_data["source"] if "source" in config_data else None
                self.details = config_data["details"] if "details" in config_data else None


            if not self.errors:
                self.errors = None

            self.configured = None
            self.configured = self.is_configured()

        def status(self):
            details = "\n".join(f"{key}: {value}" for key, value in (self.details or {}).items())
            details = textwrap.indent(details, "  ")
            r = f"""
            - source: {self.source}
            - details:
            {details}
            """
            return textwrap.dedent(r).strip()

        def is_configured(self):
            if (self.configured is None):
                return True
            else:
                return self.configured

        def to_yaml(self):
            return {
                "vsn": self.vsn if self.vsn is not None else System.BSDDetails.YAML_VERSION,
                "kind": "BSD",
                "source": self.source,
                "details": self.details,
            }


    class WindowsDetails:
        YAML_VERSION = "0.0.1"

        @staticmethod
        def system_info_details():
            try:
                version_info = subprocess.check_output(['systeminfo']).decode('utf-8')
                version_dict = {}
                for line in version_info.split('\n'):
                    parts = line.strip().split(':')
                    if len(parts) == 2:
                        key, value = parts
                        key = key.strip().replace(' ', '-').lower()
                        value = value.strip()
                        version_dict[key] = value
                return "systeminfo", version_dict
            except (subprocess.CalledProcessError, FileNotFoundError):
                return None

        def __init__(self, config_data, fetch=False):
            self.errors = []
            self.source = None
            self.details = {}
            self.vsn = None

            if fetch:
                details = System.WindowsDetails.system_info_details()
                if details is not None:
                    self.vsn = System.WindowsDetails.YAML_VERSION
                    self.source, self.details = details
            elif config_data is not None:
                self.vsn = config_data["vsn"] if "vsn" in config_data else None
                self.source = config_data["source"] if "source" in config_data else None
                self.details = config_data["details"] if "details" in config_data else None


            if config_data is not None:
                self.vsn = config_data["vsn"] if "vsn" in config_data else None

            if not self.errors:
                self.errors = None

            self.configured = None
            self.configured = self.is_configured()

        def status(self):
            details = "\n".join(f"{key}: {value}" for key, value in (self.details or {}).items())
            details = textwrap.indent(details, "  ")
            r = f"""
            - source: {self.source}
            - details:
            {details}
            """
            return textwrap.dedent(r).strip()

        def is_configured(self):
            if (self.configured is None):
                return True
            else:
                return self.configured

        def to_yaml(self):
            return {
                "vsn": self.vsn if self.vsn is not None else System.WindowsDetails.YAML_VERSION,
                "kind": "Windows",
                "source": self.source,
                "details": self.details,
            }