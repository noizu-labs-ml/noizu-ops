from .model import Model

class Provider:
    CONFIG_VSN: str = "0.0.1"

    @staticmethod
    def config_vsn() -> str:
        """
        Returns the version of the configuration.

        Returns:
            str: The version of the configuration.
        """
        return Provider.CONFIG_VSN


    def __init__(self, identifier, config_data):
        self.identifier = identifier
        self.vsn = config_data.get("vsn")
        self.name = config_data.get("name")
        self.enabled = config_data.get("enabled")
        self.details = config_data.get("details", {})
        self.models: list[Model] = []
        for model in config_data.get("models", []):
            self.models.append(Model(self.identifier, model))

    def to_yaml(self, options = None):
        options = options or {}
        models: list[dict] = []
        for model in self.models:
            if options.get("disabled") or options.get("save"):
                models.append(model.to_yaml(options=options))
            elif model.enabled:
                models.append(model.to_yaml(options=options))

        o = {
            'name': self.name,
            'enabled': self.enabled,
            'details': self.details,
            'models': models,
            'vsn': self.config_vsn(),
        }

        if options.get("save"):
            pass
        if options.get("disabled"):
            o.pop('vsn')
        else:
            o.pop('vsn')
            o.pop('enabled')
        return o