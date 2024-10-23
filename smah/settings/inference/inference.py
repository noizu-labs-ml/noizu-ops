import textwrap
from typing import Optional

import yaml

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

    @staticmethod
    def provider_factory(provider, config_data):
        return Provider(provider, config_data)

    def __init__(self, config_data = None):
        config_data = config_data or {}
        self.vsn = config_data.get("vsn", self.config_vsn())
        self.instructions: Optional[str] = config_data.get("instructions")
        self.providers = {}
        providers = config_data.get("providers", {})
        for k, v in providers.items():
             provider = self.provider_factory(k,v)
             if provider:
                self.providers[k] = provider

    def is_configured(self):
        if not self.providers:
            return False
        return True

    def to_yaml(self, options = None):
        options = options or {}
        providers = {}
        for k,v in self.providers.items():
            if options.get('save') or options.get('disabled') or (v.enabled and v.is_configured()):
                providers[k] = v.to_yaml(options=options)

        o = {
            'vsn': self.config_vsn(),
            'instructions': self.instructions,
            'providers': providers
        }

        if options.get('save'):
            pass
        else:
            o.pop('vsn')
        return o

    def show(self, options = None):
        return yaml.dump(self.to_yaml(options=options), sort_keys=False)
