from .model import Model

class Provider:
    def __init__(self, identifier, config_data):
        self.identifier = identifier
        self.vsn = config_data.get("vsn")
        self.name = config_data.get("name")
        self.enabled = config_data.get("enabled")
        self.details = config_data.get("details", {})
        self.models = []
        for model in config_data.get("models", []):
            self.models.append(Model(self.identifier, model))

