
class BaseInfo:
    @staticmethod
    def kind():
        return None

    @staticmethod
    def yaml_version():
        return "0.0.1"


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
            "vsn": self.vsn if self.vsn is not None else self.yaml_version(),
            "kind": self.kind(),
            "source": self.source,
            "details": self.details,
        }
