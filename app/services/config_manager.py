import json
import configparser
from pathlib import Path


def load_ini_config(path: str) -> dict:
    config = configparser.ConfigParser()
    config.read(path, encoding="utf-8")
    return {section: dict(config[section]) for section in config.sections()}


def save_ini_config(path: str, data: dict):
    config = configparser.ConfigParser()
    for section, values in data.items():
        config[section] = values
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        config.write(f)


def load_json_config(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_json_config(path: str, data: dict):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
