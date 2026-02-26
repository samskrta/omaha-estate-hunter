"""Tests for configuration loading."""

import os
import tempfile
from pathlib import Path

import yaml

from estate_pricer.config import load_config


class TestLoadConfig:
    def test_default_config(self):
        config = load_config(config_path="/nonexistent/config.yaml", env_path="/nonexistent/.env")
        assert config.anthropic_api_key == ""
        assert config.scraper.download_dir == "./data/sales"
        assert config.analyzer.model == "claude-sonnet-4-5-20250929"
        assert config.pricer.cache_ttl_days == 7
        assert config.output.default_format == "terminal"

    def test_env_loading(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("ANTHROPIC_API_KEY=test-key-123\n")
            f.write("EBAY_CLIENT_ID=ebay-id\n")
            f.write("EBAY_CLIENT_SECRET=ebay-secret\n")
            env_path = f.name

        try:
            config = load_config(config_path="/nonexistent/config.yaml", env_path=env_path)
            assert config.anthropic_api_key == "test-key-123"
            assert config.ebay_client_id == "ebay-id"
            assert config.ebay_client_secret == "ebay-secret"
        finally:
            os.unlink(env_path)

    def test_yaml_loading(self):
        yaml_data = {
            "scraper": {"download_dir": "/tmp/test_sales", "max_retries": 5},
            "analyzer": {"model": "claude-opus-4-6", "max_concurrency": 5},
            "pricer": {"cache_ttl_days": 14},
            "output": {"default_format": "json"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_data, f)
            yaml_path = f.name

        try:
            config = load_config(config_path=yaml_path, env_path="/nonexistent/.env")
            assert config.scraper.download_dir == "/tmp/test_sales"
            assert config.scraper.max_retries == 5
            assert config.analyzer.model == "claude-opus-4-6"
            assert config.analyzer.max_concurrency == 5
            assert config.pricer.cache_ttl_days == 14
            assert config.output.default_format == "json"
        finally:
            os.unlink(yaml_path)
