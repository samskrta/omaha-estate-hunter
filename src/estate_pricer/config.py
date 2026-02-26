"""Configuration loading from .env and config.yaml."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class ScraperConfig:
    download_dir: str = "./data/sales"
    request_delay_min: float = 1.0
    request_delay_max: float = 3.0
    page_timeout: int = 30
    photo_timeout: int = 10
    max_retries: int = 3


@dataclass
class AnalyzerConfig:
    model: str = "claude-sonnet-4-5-20250929"
    max_concurrency: int = 3
    min_value_threshold: int = 5
    context_template: str = "Estate sale in {location}"


@dataclass
class PricerConfig:
    cache_ttl_days: int = 7
    max_comps: int = 20
    outlier_std_devs: float = 2.0
    broadening_threshold: int = 3


@dataclass
class OutputConfig:
    default_format: str = "terminal"
    default_sort: str = "value"
    currency: str = "USD"


@dataclass
class Config:
    anthropic_api_key: str = ""
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    analyzer: AnalyzerConfig = field(default_factory=AnalyzerConfig)
    pricer: PricerConfig = field(default_factory=PricerConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    db_path: str = "./data/estate_pricer.db"


def _apply_yaml_section(target, section_dict: dict):
    """Apply a dictionary of values to a dataclass instance."""
    for key, value in section_dict.items():
        if hasattr(target, key):
            setattr(target, key, value)


def load_config(config_path: str | None = None, env_path: str | None = None) -> Config:
    """Load configuration from .env and config.yaml files.

    Args:
        config_path: Path to config.yaml. If None, looks in current directory.
        env_path: Path to .env file. If None, looks in current directory.

    Returns:
        Populated Config dataclass.
    """
    # Load environment variables
    env_file = Path(env_path) if env_path else Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    config = Config(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        ebay_client_id=os.getenv("EBAY_CLIENT_ID", ""),
        ebay_client_secret=os.getenv("EBAY_CLIENT_SECRET", ""),
    )

    # Load YAML config
    yaml_file = Path(config_path) if config_path else Path("config.yaml")
    if yaml_file.exists():
        with open(yaml_file) as f:
            yaml_data = yaml.safe_load(f) or {}

        if "scraper" in yaml_data:
            _apply_yaml_section(config.scraper, yaml_data["scraper"])
        if "analyzer" in yaml_data:
            _apply_yaml_section(config.analyzer, yaml_data["analyzer"])
        if "pricer" in yaml_data:
            _apply_yaml_section(config.pricer, yaml_data["pricer"])
        if "output" in yaml_data:
            _apply_yaml_section(config.output, yaml_data["output"])
        if "db_path" in yaml_data:
            config.db_path = yaml_data["db_path"]

    return config
