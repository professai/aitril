"""
Cache and session management for AiTril.

Handles storing user preferences, conversation history, and session context
to enable continuity across interactions and coordination between agents.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


def get_cache_dir() -> Path:
    """
    Get the cache directory path.

    Returns:
        Path to cache directory (~/.aitril for unified CLI/web access)
    """
    # Unified location for both CLI and web interface
    cache_dir = Path.home() / ".aitril"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cache_file(name: str = "cache.json") -> Path:
    """
    Get path to a cache file.

    Args:
        name: Name of cache file

    Returns:
        Full path to cache file
    """
    return get_cache_dir() / name


def find_env_file() -> Optional[Path]:
    """
    Find .env file in current directory or project root.

    Returns:
        Path to .env file if found, None otherwise
    """
    # Check current working directory first
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env

    # Check for /app directory (Docker container)
    app_env = Path("/app") / ".env"
    if app_env.exists():
        return app_env

    # Check home directory
    home_env = Path.home() / ".env"
    if home_env.exists():
        return home_env

    return None


def read_env_file() -> Dict[str, str]:
    """
    Read .env file and return key-value pairs.

    Returns:
        Dictionary of environment variables from .env file
    """
    env_path = find_env_file()
    if not env_path:
        return {}

    env_vars = {}
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE format
                match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$', line)
                if match:
                    key, value = match.groups()
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    env_vars[key] = value
    except Exception as e:
        print(f"Warning: Failed to read .env file: {e}")

    return env_vars


def write_env_variable(key: str, value: str) -> bool:
    """
    Write or update a variable in the .env file.

    Args:
        key: Environment variable name (will be uppercased)
        value: Value to set

    Returns:
        True if successful, False otherwise
    """
    env_path = find_env_file()

    # If no .env file exists, create one in current directory
    if not env_path:
        env_path = Path.cwd() / ".env"
        try:
            env_path.touch()
        except Exception as e:
            print(f"Warning: Failed to create .env file: {e}")
            return False

    key = key.upper()

    try:
        # Read existing content
        lines = []
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()

        # Find and update the key, or append if not found
        key_found = False
        for i, line in enumerate(lines):
            if re.match(rf'^{key}\s*=', line):
                lines[i] = f'{key}={value}\n'
                key_found = True
                break

        if not key_found:
            # Add new variable
            if lines and not lines[-1].endswith('\n'):
                lines.append('\n')
            lines.append(f'{key}={value}\n')

        # Write back to file
        with open(env_path, 'w') as f:
            f.writelines(lines)

        return True
    except Exception as e:
        print(f"Warning: Failed to write to .env file: {e}")
        return False


class SessionCache:
    """Manages session-based caching for conversations and build sessions."""

    def __init__(self, session_name: Optional[str] = None):
        """
        Initialize session cache.

        Args:
            session_name: Name of session. Defaults to 'main' for shared CLI/web history.
                         Set to 'new' to auto-generate a unique session name.
        """
        self.cache_file = get_cache_file()
        if session_name == 'new':
            self.session_name = self._generate_session_name()
        else:
            self.session_name = session_name or "main"  # Default to unified session
        self.data = self._load_cache()

    def _generate_session_name(self) -> str:
        """Generate a unique session name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}_{uuid4().hex[:8]}"

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return {
                "preferences": {},
                "sessions": {}
            }

        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load cache: {e}")
            return {
                "preferences": {},
                "sessions": {}
            }

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def get_session_data(self) -> Dict[str, Any]:
        """
        Get data for current session.

        Returns:
            Session data dictionary
        """
        if self.session_name not in self.data["sessions"]:
            self.data["sessions"][self.session_name] = {
                "created_at": datetime.now().isoformat(),
                "history": [],
                "context": {},
                "preferences": {}
            }
            self._save_cache()

        return self.data["sessions"][self.session_name]

    def add_to_history(self, prompt: str, responses: Dict[str, str]) -> None:
        """
        Add interaction to session history.

        Args:
            prompt: User prompt
            responses: Dictionary of provider responses
        """
        session = self.get_session_data()
        session["history"].append({
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "responses": responses
        })
        self._save_cache()

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get session history.

        Args:
            limit: Maximum number of recent entries to return

        Returns:
            List of history entries
        """
        session = self.get_session_data()
        history = session["history"]

        if limit:
            return history[-limit:]
        return history

    def set_preference(self, key: str, value: Any, global_pref: bool = False) -> None:
        """
        Set a user preference.

        Args:
            key: Preference key
            value: Preference value
            global_pref: If True, set as global preference; otherwise session-specific
        """
        if global_pref:
            self.data["preferences"][key] = value
        else:
            session = self.get_session_data()
            session["preferences"][key] = value

        self._save_cache()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a user preference.

        Args:
            key: Preference key
            default: Default value if not found

        Returns:
            Preference value or default
        """
        # Check session preferences first
        session = self.get_session_data()
        if key in session["preferences"]:
            return session["preferences"][key]

        # Fall back to global preferences
        return self.data["preferences"].get(key, default)

    def set_context(self, key: str, value: Any) -> None:
        """
        Set context data for current session.

        Args:
            key: Context key
            value: Context value
        """
        session = self.get_session_data()
        session["context"][key] = value
        self._save_cache()

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get context data from current session.

        Args:
            key: Context key
            default: Default value if not found

        Returns:
            Context value or default
        """
        session = self.get_session_data()
        return session["context"].get(key, default)

    def clear_session(self, session_name: Optional[str] = None) -> None:
        """
        Clear a specific session or current session.

        Args:
            session_name: Name of session to clear. Uses current session if None.
        """
        target_session = session_name or self.session_name

        if target_session in self.data["sessions"]:
            del self.data["sessions"][target_session]
            self._save_cache()
            print(f"Cleared session: {target_session}")
        else:
            print(f"Session not found: {target_session}")

    def clear_all(self) -> None:
        """Clear all cache data."""
        self.data = {
            "preferences": {},
            "sessions": {}
        }
        self._save_cache()
        print("All cache data cleared.")

    def list_sessions(self) -> List[str]:
        """
        List all session names.

        Returns:
            List of session names
        """
        return list(self.data["sessions"].keys())

    def get_cache_summary(self) -> Dict[str, Any]:
        """
        Get summary of cache contents.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_file": str(self.cache_file),
            "current_session": self.session_name,
            "total_sessions": len(self.data["sessions"]),
            "session_names": self.list_sessions(),
            "global_preferences": self.data["preferences"],
            "current_session_data": {
                "history_count": len(self.get_history()),
                "preferences": self.get_session_data().get("preferences", {}),
                "context_keys": list(self.get_session_data().get("context", {}).keys())
            }
        }

    def set_tech_stack(self, stack_config: Dict[str, Any], global_pref: bool = True) -> None:
        """
        Set tech stack preferences in .env file.

        Args:
            stack_config: Dictionary containing tech stack configuration:
                         {
                             "language": "python",
                             "framework": "fastapi",
                             "frontend": "vanilla javascript and html",
                             "database": "postgresql",
                             "tools": "docker,pytest",
                             "style_guide": "pep8"
                         }
            global_pref: If True, set as global preference (writes to .env);
                        otherwise session-specific (cache.json)
        """
        if global_pref:
            # Write to .env file with AITRIL_TECH_ prefix
            for key, value in stack_config.items():
                env_key = f"AITRIL_TECH_{key.upper()}"
                # Convert lists to comma-separated strings
                if isinstance(value, list):
                    value = ",".join(value)
                write_env_variable(env_key, str(value))

            # Also save to cache as backup
            if "tech_stack" not in self.data["preferences"]:
                self.data["preferences"]["tech_stack"] = {}
            self.data["preferences"]["tech_stack"].update(stack_config)
        else:
            # Session-specific preferences go to cache only
            session = self.get_session_data()
            if "tech_stack" not in session["preferences"]:
                session["preferences"]["tech_stack"] = {}
            session["preferences"]["tech_stack"].update(stack_config)

        self._save_cache()

    def get_tech_stack(self) -> Dict[str, Any]:
        """
        Get tech stack preferences from .env file with defaults.

        Returns:
            Tech stack configuration dict with defaults:
            - language: python
            - framework: fastapi
            - frontend: vanilla javascript and html
        """
        # Define defaults
        defaults = {
            "language": "python",
            "framework": "fastapi",
            "frontend": "vanilla javascript and html"
        }

        # Read from .env file
        env_vars = read_env_file()
        env_stack = {}
        for key, value in env_vars.items():
            if key.startswith("AITRIL_TECH_"):
                stack_key = key.replace("AITRIL_TECH_", "").lower()
                env_stack[stack_key] = value

        # Check session preferences (highest priority)
        session = self.get_session_data()
        session_stack = session["preferences"].get("tech_stack", {})

        # Check global cache preferences (lower priority than session)
        global_stack = self.data["preferences"].get("tech_stack", {})

        # Merge: defaults < global cache < env file < session
        merged = defaults.copy()
        merged.update(global_stack)
        merged.update(env_stack)
        merged.update(session_stack)

        return merged

    def set_project_context(self, project_root: str, project_type: Optional[str] = None) -> None:
        """
        Set project context for current session.

        Args:
            project_root: Root directory of the project
            project_type: Type of project (e.g., "web_api", "cli_tool", "library")
        """
        context = {
            "project_root": project_root,
            "project_type": project_type,
            "set_at": datetime.now().isoformat()
        }
        self.set_context("project", context)

    def get_project_context(self) -> Optional[Dict[str, Any]]:
        """
        Get project context from current session.

        Returns:
            Project context dict or None if not set
        """
        return self.get_context("project")

    def add_build_artifact(self, artifact_type: str, artifact_info: Dict[str, Any]) -> None:
        """
        Record build artifact in session.

        Args:
            artifact_type: Type of artifact (e.g., "file", "directory", "deployment")
            artifact_info: Information about the artifact
        """
        session = self.get_session_data()

        if "build_artifacts" not in session:
            session["build_artifacts"] = []

        session["build_artifacts"].append({
            "type": artifact_type,
            "timestamp": datetime.now().isoformat(),
            "info": artifact_info
        })

        self._save_cache()

    def get_build_artifacts(self) -> List[Dict[str, Any]]:
        """
        Get all build artifacts from current session.

        Returns:
            List of build artifact records
        """
        session = self.get_session_data()
        return session.get("build_artifacts", [])

    def log_settings_change(self, setting_type: str, old_value: Any, new_value: Any, reason: Optional[str] = None) -> None:
        """
        Log a settings change event in the session history.

        This enables tracking how settings evolved during a session,
        allowing for richer responses and interesting build evolutions.

        Args:
            setting_type: Type of setting changed (e.g., 'model', 'provider', 'planner')
            old_value: Previous value
            new_value: New value
            reason: Optional reason for the change
        """
        session = self.get_session_data()

        if "settings_changes" not in session:
            session["settings_changes"] = []

        change_event = {
            "timestamp": datetime.now().isoformat(),
            "type": setting_type,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason
        }

        session["settings_changes"].append(change_event)
        self._save_cache()

    def get_settings_evolution(self) -> List[Dict[str, Any]]:
        """
        Get the evolution of settings changes during this session.

        Returns:
            List of settings change events
        """
        session = self.get_session_data()
        return session.get("settings_changes", [])
