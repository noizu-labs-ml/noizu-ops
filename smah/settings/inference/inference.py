from typing import Optional

from .provider import Provider

class Inference:
    CONFIG_VSN: str = "0.0.1"

    @staticmethod
    def config_vsn() -> str:
        """
        Returns the version of the configuration.

        Returns:
            str: The version of the configuration.
        """
        return Inference.CONFIG_VSN

    def __init__(self, config_data):
        config_data = config_data or {}
        self.vsn = config_data.get("vsn", self.config_vsn())
        self.instructions: Optional[str] = config_data.get("instructions")
        self.providers = {}
    #     providers = config_data.get("providers", {})
    #     for provider, config in providers.items():
    #         self.providers.append(Provider(provider, config))
    #
    # @staticmethod
    # def load_provider(provider, config_data):
    #     return Provider(provider, config_data)

    def is_configured(self):
        if not self.providers:
            return False
        return True

    def to_yaml(self, options = None):
        providers = {k:v.to_yaml(options=options) for k,v in self.providers.items()}
        return {
            'vsn': self.config_vsn(),
            'instructions': self.instructions,
            'providers': providers
        }