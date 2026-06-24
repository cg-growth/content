import os
from dotenv import load_dotenv
import yaml
from pathlib import Path

load_dotenv()
cg_api_key = os.getenv("CG_API_KEY")


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
