import textwrap

import yaml


class BaseInfo:
    CONFIG_VSN = "0.0.1"

    @staticmethod
    def kind():
        return None

    @staticmethod
    def config_vsn():
        return BaseInfo.CONFIG_VSN


    def __init__(self, config_data):
        self.errors = []
        self.source = None
        self.details = {}
        self.vsn = None
        self.configured = None

        if config_data is not None:
            self.vsn = config_data["vsn"] if "vsn" in config_data else None


    def is_configured(self):
        """
        Checks if the OS details are configured.

        Returns:
            bool: True if the details are configured, False otherwise.
        """
        if self.configured is None:
            return True
        else:
            return self.configured

    def to_yaml(self, options = None):
        """
        Converts the OS details to a YAML-compatible dictionary.

        Returns:
            dict: The OS details in YAML format.
        """

        return {
            "vsn": self.config_vsn(),
            "kind": self.kind(),
            "source": self.source,
            "details": self.details,
        }

    def show(self, options = None):
        details = textwrap.indent(yaml.dump(self.details), " ") if self.details else None
        template = textwrap.dedent(
            """
            - kind: {kind}
            - source: {source}
            - details:            
            {details}
            """
        ).strip().format(
            type=self.kind(),
            source=self.source,
            details=details
        )
        return template

