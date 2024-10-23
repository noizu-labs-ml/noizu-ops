import textwrap
from typing import Optional, Tuple

import yaml


class BaseInfo:
    CONFIG_VSN = "0.0.1"

    @staticmethod
    def info()  -> Optional[Tuple]:
        return None

    @staticmethod
    def config_vsn():
        return BaseInfo.CONFIG_VSN


    def __init__(self, kind: str, config_data = None, fetch=False):
        config_data = config_data or {}
        self.kind = kind
        self.source = None
        self.details = None
        self.vsn = None

        if fetch:
            self.vsn = self.config_vsn()
            details = self.info()
            if details:
                self.source, self.details = details
            else:
                self.source = "Unsupported"
        elif config_data is not None:
            self.vsn = config_data.get("vsn", self.config_vsn())
            self.source = config_data.get("source")
            self.details = config_data.get("details")

    def is_configured(self):
        """
        Checks if the OS details are configured.

        Returns:
            bool: True if the details are configured, False otherwise.
        """
        if not self.kind:
            return False
        return True

    def to_yaml(self, options = None):
        """
        Converts the OS details to a YAML-compatible dictionary.

        Returns:
            dict: The OS details in YAML format.
        """

        return {
            "vsn": self.config_vsn(),
            "kind": self.kind,
            "source": self.source,
            "details": self.details,
        }

    def show(self, options = None):
        if self.details:
            details = textwrap.indent("\n".join([f"- {k}: {v}" for k,v in self.details.items()]), "  ")
        else:
            details = None

        template = textwrap.dedent(
            """
            - kind: {kind}
            - source: {source}
            - details:            
            {details}
            """
        ).strip().format(
            kind=self.kind,
            source=self.source,
            details=details
        )
        return template

