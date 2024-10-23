from datetime import datetime
from typing import Optional

import yaml

def get_list(source: dict, value: str) -> Optional[list[str]]:
    v = source.get(value)
    if isinstance(v, str):
        v = [v]
    return v

def get_iso(source: dict, value: str) -> Optional[datetime]:
    v = source.get(value)
    return datetime.fromisoformat(v) if isinstance(v, str) else None

class ModelUseCase:
    def __init__(self, config_data = None):
        config_data = config_data or {}
        self.name: str = config_data.get("name")
        self.instructions: Optional[str] = config_data.get("instructions")
        self.notes: Optional[str] = config_data.get("notes")
        self.score: float = config_data.get("score", 0.3)

    def to_yaml(self, options=None):
        o = {
            'name': self.name,
        }
        if self.instructions:
            o['instructions'] = self.instructions
        if self.notes:
            o['notes'] = self.notes
        if self.score:
            o['score'] = self.score
        return o

    def show(self, options = None):
        y = self.to_yaml(options=None)
        return yaml.dump(y, sort_keys=False)

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
        self.model: str = config_data.get("model")
        self.description: str = config_data.get("description")
        self.enabled: bool = config_data.get("enabled", False)
        self.training_cutoff: Optional[datetime] = get_iso(config_data, "training_cutoff")
        self.license: Optional[str] = config_data.get("license")
        self.model_type: Optional[str] = config_data.get("model_type", "LLM")
        self.context: Optional[dict] = config_data.get("context")
        self.strengths: list[str] = get_list(config_data, "strengths") or []
        self.weaknesses: list[str] = get_list(config_data, "weaknesses") or []
        self.modalities: Optional[dict] = config_data.get("modalities") or {}
        self.settings: Optional[dict] = config_data.get("settings") or {}
        self.attributes: Optional[dict] = config_data.get("attributes") or {}
        self.cost: Optional[dict] = config_data.get("cost")
        v = config_data.get("use_cases") or []
        self.use_cases: Optional[list] = []
        for use_case in v:
            self.use_cases.append(ModelUseCase(use_case))

    def is_configured(self):
        if not self.name:
            return False
        if not self.model:
            return False
        if self.enabled is None:
            return False
        return True

    def to_yaml(self, options=None):
        options = options or {}
        if options.get("prompt"):
            return self.to_prompt_yaml(options=options)
        else:
            return self.to_standard_yaml(options=options)


    def to_prompt_yaml(self, options=None):
        options = options or {}
        min_score = options.get('min_score', 0.4)
        use_cases = [x.to_yaml(options=options) for x in self.use_cases if x.score >= min_score]
        o = {
            'id': f"{self.provider}.{self.name}",
            'description': self.description,
            'training_cutoff': self.training_cutoff,
            'context': self.context,
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'modalities': self.modalities,
            'attributes': self.attributes,
            'cost': self.cost,
            'use_cases': use_cases,
        }
        return o

    def to_standard_yaml(self, options=None):
        options = options or {}
        if options.get("save"):
            use_cases = [x.to_yaml(options=options) for x in self.use_cases]
        else:
            min_score = options.get('min_score', 0.4)
            use_cases = [x.to_yaml(options=options) for x in self.use_cases if x.score >= min_score]

        o = {
            'name': self.name,
            'model': self.model,
            'description': self.description,
            'enabled': self.enabled,
            'training_cutoff': self.training_cutoff,
            'license': self.license,
            'model_type': self.model_type,
            'context': self.context,
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'modalities': self.modalities,
            'settings': self.settings,
            'attributes': self.attributes,
            'cost': self.cost,
            'use_cases': use_cases,
            'vsn': self.config_vsn(),
        }
        if options.get("save"):
            pass
        elif options.get("disabled"):
            o.pop('vsn')
            o.pop('license')
            o.pop('settings')
        else:
            o.pop('vsn')
            o.pop('enabled')
            o.pop('license')
            o.pop('settings')
        return o

    def show(self, options = None):
        y = self.to_yaml(options=options)
        return yaml.dump(y, sort_keys=False)