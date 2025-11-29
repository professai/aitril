"""
Configuration management for AiTril.

Handles loading, saving, and initializing provider configuration
via an interactive wizard.

NOTE: This module now uses settings.json (via settings.py) instead of config.toml
for unified configuration between CLI and web interface.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from .settings import Settings


def get_config_path() -> Path:
    """
    Determine the configuration file path.

    Now returns path to ~/.aitril/settings.json for unified CLI/web configuration.
    Legacy config.toml files are automatically migrated.
    """
    # New unified location
    config_dir = Path.home() / ".aitril"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.json"


def load_config() -> Optional[dict]:
    """
    Load configuration from settings.json using Settings class.

    Returns:
        Dictionary containing configuration in legacy format for backward compatibility,
        or None if no providers are configured.
    """
    try:
        settings = Settings()
        all_settings = settings.export_settings()

        # Convert new format to legacy format for backward compatibility
        providers = all_settings.get('llm_providers', {})
        if not providers:
            return None

        # Map new format to old format
        legacy_config = {"providers": {}}
        for provider_id, provider_config in providers.items():
            legacy_config["providers"][provider_id] = {
                "enabled": provider_config.get("enabled", False),
                "api_key": None,  # API keys are read from env vars
                "model": provider_config.get("model", "")
            }

        return legacy_config
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


def save_config(cfg: dict) -> None:
    """
    Save configuration to settings.json using Settings class.

    Args:
        cfg: Configuration dictionary in legacy format to save.
    """
    try:
        settings = Settings()

        # Convert legacy format to new format
        if "providers" in cfg:
            for provider_id, provider_config in cfg["providers"].items():
                # Get existing provider config or create new one
                existing = settings.get_llm_providers().get(provider_id, {})

                # Update with legacy values
                new_config = {
                    "name": existing.get("name", provider_id.title()),
                    "enabled": provider_config.get("enabled", False),
                    "api_key_env": existing.get("api_key_env", f"{provider_id.upper()}_API_KEY"),
                    "model": provider_config.get("model", existing.get("model", "")),
                    "base_url": existing.get("base_url"),
                    "custom": existing.get("custom", False)
                }

                settings.update_provider(provider_id, new_config)

        print(f"Configuration saved to {settings.settings_file}")
    except Exception as e:
        print(f"Error saving config: {e}")
        sys.exit(1)


def load_config_from_env() -> Optional[dict]:
    """
    Load configuration from environment variables.

    Returns:
        Dictionary containing configuration from env vars, or None if no API keys found.
    """
    config = {"providers": {}}

    # Check for OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        config["providers"]["openai"] = {
            "enabled": True,
            "api_key": openai_key,
            "model": os.environ.get("OPENAI_MODEL", "gpt-4")
        }

    # Check for Anthropic
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        config["providers"]["anthropic"] = {
            "enabled": True,
            "api_key": anthropic_key,
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        }

    # Check for Gemini (uses GOOGLE_API_KEY per Google's SDK)
    gemini_key = os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        config["providers"]["gemini"] = {
            "enabled": True,
            "api_key": gemini_key,
            "model": os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
        }

    # Return None if no providers configured
    if not config["providers"]:
        return None

    return config


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
    Now uses Settings class for unified CLI/web configuration.

    Returns:
        Configuration dictionary if successful, None if user cancels.
    """
    print("\n" + "=" * 60)
    print("🧬 Welcome to AiTril - Multi-LLM Orchestration Setup")
    print("=" * 60)
    print("\nAiTril lets you query multiple LLM providers in parallel.")
    print("For the best experience (tri-lam mode), configure at least 2 providers.\n")

    settings = Settings()
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
            "model": "claude-haiku-4-5-20251001"
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
        api_key = input("Enter your Google API key (or press Enter to use GOOGLE_API_KEY env var): ").strip()
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
            # Model will be read from OPENAI_MODEL env var or use default
        }
        found_any = True

    # Check Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        config["providers"]["anthropic"] = {
            "enabled": True,
            "api_key": None,  # Will be read from env by provider
            # Model will be read from ANTHROPIC_MODEL env var or use default
        }
        found_any = True

    # Check Gemini
    if os.environ.get("GOOGLE_API_KEY"):
        config["providers"]["gemini"] = {
            "enabled": True,
            "api_key": None,  # Will be read from env by provider
            # Model will be read from GEMINI_MODEL env var or use default
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
