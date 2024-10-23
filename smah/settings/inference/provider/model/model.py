
class Model:
    CONFIG_VSN: str = "0.0.1"

    @staticmethod
    def config_vsn() -> str:
        """
        Returns the version of the configuration.

        Returns:
            str: The version of the configuration.
        """
        return Model.CONFIG_VSN

    def __init__(self, provider, config_data):
        self.provider: str = provider
        self.vsn: str = config_data.get("vsn")

        self.name: str = config_data.get("name")
        self.description: str = config_data.get("description")
        self.enabled: bool = config_data.get("enabled")
        self.model: str = config_data.get("model", self.name)

    def to_yaml(self, options=None):
        options = options or {}
        o = {
                'vsn': self.config_vsn(),
                'name': self.name,
                'model': self.model,
                'description': self.description,
                'enabled': self.enabled,
            }
        if options.get("save"):
            pass
        elif options.get("disabled"):
            o.pop('vsn')
        else:
            o.pop('vsn')
            o.pop('enabled')
        return o

