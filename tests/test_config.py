import os
from pathlib import Path
from client.config import load_config, save_config, save_auth, CpipConfig


def test_cpip_config_paths(mock_config):
    """Test that CpipConfig computes paths correctly based on its home."""
    assert mock_config.cache_dir == os.path.join(mock_config.home, "cache")
    assert mock_config.wheels_dir == os.path.join(mock_config.cache_dir, "wheels")
    assert mock_config.layers_dir == os.path.join(mock_config.cache_dir, "layers")
    assert mock_config.metadata_dir == os.path.join(mock_config.cache_dir, "metadata")


def test_save_and_load_config(mock_config):
    """Test saving and loading configuration."""
    mock_config.cloud.api_url = "http://another-server"
    save_config(mock_config)
    
    # Reload config
    reloaded = load_config()
    assert reloaded.cloud.api_url == "http://another-server"
