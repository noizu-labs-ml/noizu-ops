import textwrap
from typing import Optional

from rich.prompt import Prompt, Confirm
from smah.console import std_console
class User:
    CONFIG_VSN = "0.0.1"

    @staticmethod
    def config_vsn():
        return User.CONFIG_VSN

    @staticmethod
    def vsn_supported(vsn):
        if vsn is None:
            return False
        else:
            return vsn <= User.config_vsn()

    def __init__(self, config_data = None):
        config_data = config_data or {}
        self.name: Optional[str] = config_data.get("name")
        self.system_admin_experience: Optional[str] = config_data.get("system_admin_experience")
        self.role: Optional[str] = config_data.get("role")
        self.about: Optional[str] = config_data.get("about")
        self.vsn: Optional[str] = config_data.get("vsn")

    def is_configured(self) -> bool:
        if not self.name:
            return False
        if not self.system_admin_experience:
            return False
        if not self.role:
            return False
        if not self.about:
            return False
        return True

    def to_yaml(self, options=None) -> dict:
        return {
            "vsn": self.config_vsn(),
            "name": self.name,
            "system_admin_experience": self.system_admin_experience,
            "role": self.role,
            "about": self.about,
        }

    def show(self, options=None):
        about = self.about or ""
        about = textwrap.indent(about, "   ")
        template = textwrap.dedent(
            """
            - name: {name}
            - role: {role}
            - system_admin_experience: {experience}
            - about:
            {about}
            """
        ).strip().format(
            name=self.name,
            role=self.role,
            experience=self.system_admin_experience,
            about=about,
        )
        return template