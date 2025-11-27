"""
Configuration management for AiTril.

Handles loading, saving, and initializing provider configuration
via an interactive wizard.
"""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

import tomli_w


def get_config_path() -> Path:
    """
    Determine the configuration file path.

    Returns the path to ~/.config/aitril/config.toml on Linux/macOS,
    or appropriate location on Windows.
    """
    if sys.platform == "win32":
        config_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "aitril"
    else:
        config_dir = Path.home() / ".config" / "aitril"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.toml"


def load_config() -> Optional[dict]:
    """
    Load configuration from TOML file.

    Returns:
        Dictionary containing configuration, or None if file doesn't exist.
    """
    config_path = get_config_path()

    if not config_path.exists():
        return None

    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return None


def save_config(cfg: dict) -> None:
    """
    Save configuration to TOML file.

    Args:
        cfg: Configuration dictionary to save.
    """
    config_path = get_config_path()

    try:
        with open(config_path, "wb") as f:
            tomli_w.dump(cfg, f)
        print(f"Configuration saved to {config_path}")
    except Exception as e:
        print(f"Error saving config to {config_path}: {e}")
        sys.exit(1)


def count_enabled_providers(cfg: dict) -> int:
    """
    Count the number of enabled providers in configuration.

    Args:
        cfg: Configuration dictionary.

    Returns:
        Number of enabled providers.
    """
    if "providers" not in cfg:
        return 0

    count = 0
    for provider_name, provider_config in cfg["providers"].items():
        if isinstance(provider_config, dict) and provider_config.get("enabled", False):
            count += 1

    return count


def init_wizard() -> Optional[dict]:
    """
    Interactive setup wizard for configuring AiTril providers.

    Guides the user through configuring OpenAI, Anthropic, and Gemini providers.
    Warns if fewer than 2 providers are enabled.

    Returns:
        Configuration dictionary if successful, None if user cancels.
    """
    print("\n" + "=" * 60)
    print("🧬 Welcome to AiTril - Multi-LLM Orchestration Setup")
    print("=" * 60)
    print("\nAiTril lets you query multiple LLM providers in parallel.")
    print("For the best experience (tri-lam mode), configure at least 2 providers.\n")

    config = {"providers": {}}

    # OpenAI Configuration
    print("-" * 60)
    print("OpenAI (GPT) Configuration")
    print("-" * 60)
    configure_openai = input("Configure OpenAI? [y/N]: ").strip().lower()

    if configure_openai in ["y", "yes"]:
        api_key = input("Enter your OpenAI API key (or press Enter to use OPENAI_API_KEY env var): ").strip()
        config["providers"]["openai"] = {
            "enabled": True,
            "api_key": api_key if api_key else None,
            "model": "gpt-4"
        }
        print("✓ OpenAI configured")
    else:
        config["providers"]["openai"] = {"enabled": False}
        print("✗ OpenAI skipped")

    # Anthropic Configuration
    print("\n" + "-" * 60)
    print("Anthropic (Claude) Configuration")
    print("-" * 60)
    configure_anthropic = input("Configure Anthropic Claude? [y/N]: ").strip().lower()

    if configure_anthropic in ["y", "yes"]:
        api_key = input("Enter your Anthropic API key (or press Enter to use ANTHROPIC_API_KEY env var): ").strip()
        config["providers"]["anthropic"] = {
            "enabled": True,
            "api_key": api_key if api_key else None,
            "model": "claude-3-5-sonnet-20240620"
        }
        print("✓ Anthropic configured")
    else:
        config["providers"]["anthropic"] = {"enabled": False}
        print("✗ Anthropic skipped")

    # Gemini Configuration
    print("\n" + "-" * 60)
    print("Google Gemini Configuration")
    print("-" * 60)
    configure_gemini = input("Configure Google Gemini? [y/N]: ").strip().lower()

    if configure_gemini in ["y", "yes"]:
        api_key = input("Enter your Google API key (or press Enter to use GEMINI_API_KEY env var): ").strip()
        config["providers"]["gemini"] = {
            "enabled": True,
            "api_key": api_key if api_key else None,
            "model": "gemini-pro"
        }
        print("✓ Gemini configured")
    else:
        config["providers"]["gemini"] = {"enabled": False}
        print("✗ Gemini skipped")

    # Validate configuration
    print("\n" + "=" * 60)
    enabled_count = count_enabled_providers(config)
    print(f"Enabled providers: {enabled_count}")

    if enabled_count < 2:
        print("\n⚠️  WARNING: You have configured fewer than 2 providers.")
        print("AiTril works best with at least 2 providers for tri-lam mode.")
        print("You can run 'aitril init' again later to add more providers.")

        proceed = input("\nProceed with current configuration? [y/N]: ").strip().lower()
        if proceed not in ["y", "yes"]:
            print("Setup cancelled.")
            return None

    # Save configuration
    save_config(config)

    print("\n✓ Setup complete! You can now use AiTril.")
    print("\nTry:")
    print("  aitril ask --provider gpt 'Hello, world!'")
    if enabled_count >= 2:
        print("  aitril tri 'Compare your strengths'")
    print()

    return config


def create_config_from_env() -> Optional[dict]:
    """
    Create configuration from environment variables if they exist.

    Checks for OPENAI_API_KEY, ANTHROPIC_API_KEY, and GEMINI_API_KEY
    environment variables and creates a config dict.

    Returns:
        Configuration dictionary if at least one API key is found, None otherwise.
    """
    config = {"providers": {}}
    found_any = False

    # Check OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        config["providers"]["openai"] = {
            "enabled": True,
            "api_key": None,  # Will be read from env by provider
            "model": "gpt-4"
        }
        found_any = True

    # Check Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        config["providers"]["anthropic"] = {
            "enabled": True,
            "api_key": None,  # Will be read from env by provider
            "model": "claude-3-5-sonnet-20240620"
        }
        found_any = True

    # Check Gemini
    if os.environ.get("GEMINI_API_KEY"):
        config["providers"]["gemini"] = {
            "enabled": True,
            "api_key": None,  # Will be read from env by provider
            "model": "gemini-pro"
        }
        found_any = True

    return config if found_any else None


def ensure_config(min_providers: int = 2) -> dict:
    """
    Ensure configuration exists and meets minimum provider requirements.

    If configuration doesn't exist, tries to create config from environment variables.
    If env vars are insufficient, runs the init wizard.

    Args:
        min_providers: Minimum number of enabled providers required.

    Returns:
        Valid configuration dictionary.

    Raises:
        SystemExit: If user cancels wizard or requirements aren't met.
    """
    config = load_config()

    if config is None:
        # Try to auto-create config from environment variables
        config = create_config_from_env()

        if config is None or count_enabled_providers(config) < min_providers:
            print("No configuration found. Running setup wizard...\n")
            config = init_wizard()
            if config is None:
                sys.exit(1)

    enabled_count = count_enabled_providers(config)

    if enabled_count < min_providers:
        print(f"\n⚠️  ERROR: At least {min_providers} providers must be enabled.")
        print(f"Current enabled providers: {enabled_count}")
        print("\nPlease run 'aitril init' to configure more providers.")
        sys.exit(1)

    return config
