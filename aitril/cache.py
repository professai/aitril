"""
Cache and session management for AiTril.

Handles storing user preferences, conversation history, and session context
to enable continuity across interactions and coordination between agents.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


def get_cache_dir() -> Path:
    """
    Get the cache directory path.

    Returns:
        Path to cache directory (~/.cache/aitril or platform equivalent)
    """
    if sys.platform == "win32":
        cache_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "aitril" / "cache"
    elif sys.platform == "darwin":
        cache_dir = Path.home() / "Library" / "Caches" / "aitril"
    else:
        cache_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "aitril"

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


class SessionCache:
    """Manages session-based caching for conversations and build sessions."""

    def __init__(self, session_name: Optional[str] = None):
        """
        Initialize session cache.

        Args:
            session_name: Name of session (e.g., 'chat', 'build'). Auto-generated if None.
        """
        self.cache_file = get_cache_file()
        self.session_name = session_name or self._generate_session_name()
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
