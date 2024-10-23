
class Model:

    def __init__(self, provider, config_data):
        self.provider: str = provider
        self.vsn: str = config_data.get("vsn")

        self.name: str = config_data.get("name")
        self.description: str = config_data.get("description")
        self.enabled: bool = config_data.get("enabled")
        self.model: str = config_data.get("model", self.name)


