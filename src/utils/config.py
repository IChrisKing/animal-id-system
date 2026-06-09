"""配置加载模块"""

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class Config:
    """加载并管理 YAML 配置文件 + 环境变量"""

    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()
        self._raw = self._load_yaml(config_path)
        self._resolve_env_vars()

    def _load_yaml(self, path: str) -> dict:
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def _resolve_env_vars(self):
        """递归替换配置中的 ${ENV_VAR} 占位符"""
        import os
        import re

        def resolve(obj: Any) -> Any:
            if isinstance(obj, str):
                pattern = r'\$\{([^}]+)\}'
                matches = re.findall(pattern, obj)
                for var in matches:
                    obj = obj.replace(f"${{{var}}}", os.getenv(var, ""))
                return obj
            elif isinstance(obj, dict):
                return {k: resolve(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve(v) for v in obj]
            return obj

        self._raw = resolve(self._raw)

    def __getattr__(self, name: str) -> Any:
        if name in self._raw:
            value = self._raw[name]
            if isinstance(value, dict):
                return ConfigDict(value)
            return value
        raise AttributeError(f"Config has no key: {name}")


class ConfigDict:
    """支持点号访问的字典包装器"""
    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            value = self._data[name]
            if isinstance(value, dict):
                return ConfigDict(value)
            return value
        raise AttributeError(f"Config key not found: {name}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
