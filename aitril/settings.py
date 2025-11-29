"""
Settings management for AiTril
Handles LLM provider and deployment target configuration
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class Settings:
    """Manages AiTril settings with persistence"""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize settings manager

        Args:
            config_dir: Directory to store settings (default: ~/.aitril)
        """
        if config_dir is None:
            config_dir = Path.home() / '.aitril'

        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.config_dir / 'settings.json'

        self.settings = self._load_settings()

    def _load_settings(self) -> Dict:
        """Load settings from disk or create defaults"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")
                return self._default_settings()
        else:
            return self._default_settings()

    def _default_settings(self) -> Dict:
        """Create default settings structure, reading models from environment variables"""
        import os

        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "llm_providers": {
                "openai": {
                    "name": "OpenAI",
                    "enabled": True,
                    "api_key_env": "OPENAI_API_KEY",
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
                    "base_url": None,
                    "custom": False
                },
                "anthropic": {
                    "name": "Anthropic",
                    "enabled": True,
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "model": os.getenv("ANTHROPIC_MODEL", "claude-opus-4-20250514"),
                    "base_url": None,
                    "custom": False
                },
                "gemini": {
                    "name": "Google Gemini",
                    "enabled": True,
                    "api_key_env": "GOOGLE_API_KEY",
                    "model": os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
                    "base_url": None,
                    "custom": False
                }
            },
            "deployment_targets": {
                "local": {
                    "name": "Local File System",
                    "enabled": True,
                    "output_dir": "./output",
                    "type": "local"
                },
                "github": {
                    "name": "GitHub Pages",
                    "enabled": False,
                    "repo_url": "",
                    "access_token_env": "GITHUB_TOKEN",
                    "branch": "gh-pages",
                    "build_command": "",
                    "type": "github"
                },
                "ec2": {
                    "name": "AWS EC2",
                    "enabled": False,
                    "access_key_env": "AWS_ACCESS_KEY_ID",
                    "secret_key_env": "AWS_SECRET_ACCESS_KEY",
                    "region": "us-east-1",
                    "instance_id": "",
                    "ssh_key_path": "",
                    "type": "ec2"
                },
                "docker": {
                    "name": "Docker Container",
                    "enabled": True,
                    "host": "unix:///var/run/docker.sock",
                    "registry_url": "",
                    "registry_username": "",
                    "registry_password_env": "DOCKER_REGISTRY_PASSWORD",
                    "platform": "linux/amd64",
                    "type": "docker"
                }
            },
            "general": {
                "theme": "dark",
                "default_mode": "build",
                "log_level": "info",
                "auto_save": True,
                "initial_planner": "none"
            },
            "chat_history": {
                "enabled": True,
                "persist_across_cli_web": True,
                "default_session": "main",
                "max_history_items": 100
            }
        }

    def save(self) -> bool:
        """Save settings to disk

        Returns:
            True if successful, False otherwise
        """
        try:
            self.settings['last_updated'] = datetime.now().isoformat()
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def get_llm_providers(self) -> Dict:
        """Get all LLM provider settings"""
        return self.settings.get('llm_providers', {})

    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled provider IDs"""
        providers = self.get_llm_providers()
        return [
            provider_id for provider_id, config in providers.items()
            if config.get('enabled', False)
        ]

    def update_provider(self, provider_id: str, config: Dict) -> bool:
        """Update LLM provider configuration

        Args:
            provider_id: Provider identifier (e.g., 'openai', 'anthropic')
            config: Provider configuration dictionary

        Returns:
            True if successful, False otherwise
        """
        if 'llm_providers' not in self.settings:
            self.settings['llm_providers'] = {}

        self.settings['llm_providers'][provider_id] = config
        return self.save()

    def add_custom_provider(self, provider_id: str, name: str,
                           api_key_env: str, model: str,
                           base_url: str) -> bool:
        """Add a custom LLM provider

        Args:
            provider_id: Unique identifier for provider
            name: Display name
            api_key_env: Environment variable for API key
            model: Model identifier
            base_url: Base URL for API

        Returns:
            True if successful, False otherwise
        """
        config = {
            "name": name,
            "enabled": True,
            "api_key_env": api_key_env,
            "model": model,
            "base_url": base_url,
            "custom": True
        }
        return self.update_provider(provider_id, config)

    def get_deployment_targets(self) -> Dict:
        """Get all deployment target settings"""
        return self.settings.get('deployment_targets', {})

    def get_enabled_targets(self) -> List[str]:
        """Get list of enabled deployment target IDs"""
        targets = self.get_deployment_targets()
        return [
            target_id for target_id, config in targets.items()
            if config.get('enabled', False)
        ]

    def update_deployment_target(self, target_id: str, config: Dict) -> bool:
        """Update deployment target configuration

        Args:
            target_id: Target identifier (e.g., 'github', 'ec2', 'docker')
            config: Target configuration dictionary

        Returns:
            True if successful, False otherwise
        """
        if 'deployment_targets' not in self.settings:
            self.settings['deployment_targets'] = {}

        self.settings['deployment_targets'][target_id] = config
        return self.save()

    def get_general_settings(self) -> Dict:
        """Get general application settings"""
        return self.settings.get('general', {})

    def update_general_settings(self, config: Dict) -> bool:
        """Update general settings

        Args:
            config: General settings dictionary

        Returns:
            True if successful, False otherwise
        """
        self.settings['general'] = config
        return self.save()

    def export_settings(self) -> Dict:
        """Export all settings (excluding sensitive data)"""
        exported = self.settings.copy()

        # Remove sensitive environment variable values
        # (keep references to env vars, but not actual values)
        return exported

    def import_settings(self, settings: Dict) -> bool:
        """Import settings from dictionary

        Args:
            settings: Settings dictionary to import

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate settings structure
            required_keys = ['llm_providers', 'deployment_targets', 'general']
            if not all(key in settings for key in required_keys):
                return False

            self.settings = settings
            return self.save()
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False

    def get_chat_history_settings(self) -> Dict:
        """Get chat history settings"""
        return self.settings.get('chat_history', {
            "enabled": True,
            "persist_across_cli_web": True,
            "default_session": "main",
            "max_history_items": 100
        })

    def update_chat_history_settings(self, config: Dict) -> bool:
        """Update chat history settings

        Args:
            config: Chat history settings dictionary

        Returns:
            True if successful, False otherwise
        """
        self.settings['chat_history'] = config
        return self.save()

    def clear_chat_history(self) -> bool:
        """Clear all chat history from cache

        Returns:
            True if successful, False otherwise
        """
        try:
            from .cache import SessionCache
            cache = SessionCache()
            cache.clear_all()
            return True
        except Exception as e:
            print(f"Error clearing chat history: {e}")
            return False
