"""
File operations module for AiTril code building.

Provides safe file operations with backup, diff tracking, and validation.
"""

import os
import shutil
import difflib
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime


class FileOperations:
    """Manages file operations for code building and deployment."""

    def __init__(self, project_root: Optional[str] = None, backup_enabled: bool = True):
        """
        Initialize file operations manager.

        Args:
            project_root: Root directory for file operations. Defaults to current directory.
            backup_enabled: Whether to create backups before modifying files.
        """
        self.project_root = Path(project_root or os.getcwd())
        self.backup_enabled = backup_enabled
        self.backup_dir = self.project_root / ".aitril_backups"

        if self.backup_enabled:
            self.backup_dir.mkdir(exist_ok=True)

    def read_file(self, file_path: str) -> str:
        """
        Read file contents.

        Args:
            file_path: Path to file (relative to project_root or absolute).

        Returns:
            File contents as string.

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        full_path = self._resolve_path(file_path)

        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_file(self, file_path: str, content: str, create_dirs: bool = True) -> None:
        """
        Write content to file with optional backup.

        Args:
            file_path: Path to file (relative to project_root or absolute).
            content: Content to write.
            create_dirs: Whether to create parent directories if they don't exist.

        Raises:
            IOError: If write fails.
        """
        full_path = self._resolve_path(file_path)

        # Create backup if file exists
        if full_path.exists() and self.backup_enabled:
            self._create_backup(full_path)

        # Create parent directories if needed
        if create_dirs:
            full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def append_to_file(self, file_path: str, content: str) -> None:
        """
        Append content to existing file.

        Args:
            file_path: Path to file (relative to project_root or absolute).
            content: Content to append.

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        full_path = self._resolve_path(file_path)

        if self.backup_enabled:
            self._create_backup(full_path)

        with open(full_path, 'a', encoding='utf-8') as f:
            f.write(content)

    def create_directory(self, dir_path: str, parents: bool = True) -> None:
        """
        Create directory.

        Args:
            dir_path: Path to directory (relative to project_root or absolute).
            parents: Whether to create parent directories.
        """
        full_path = self._resolve_path(dir_path)
        full_path.mkdir(parents=parents, exist_ok=True)

    def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists.

        Args:
            file_path: Path to file (relative to project_root or absolute).

        Returns:
            True if file exists, False otherwise.
        """
        full_path = self._resolve_path(file_path)
        return full_path.exists() and full_path.is_file()

    def directory_exists(self, dir_path: str) -> bool:
        """
        Check if directory exists.

        Args:
            dir_path: Path to directory (relative to project_root or absolute).

        Returns:
            True if directory exists, False otherwise.
        """
        full_path = self._resolve_path(dir_path)
        return full_path.exists() and full_path.is_dir()

    def list_files(self, dir_path: str = ".", pattern: str = "*") -> List[str]:
        """
        List files in directory matching pattern.

        Args:
            dir_path: Directory to list (relative to project_root or absolute).
            pattern: Glob pattern for matching files (default: all files).

        Returns:
            List of file paths relative to project_root.
        """
        full_path = self._resolve_path(dir_path)

        files = []
        for file in full_path.glob(pattern):
            if file.is_file():
                relative_path = file.relative_to(self.project_root)
                files.append(str(relative_path))

        return sorted(files)

    def get_diff(self, file_path: str, new_content: str) -> str:
        """
        Generate diff between current file and new content.

        Args:
            file_path: Path to file (relative to project_root or absolute).
            new_content: New content to compare against.

        Returns:
            Unified diff as string.
        """
        full_path = self._resolve_path(file_path)

        if not full_path.exists():
            return f"New file: {file_path}\n{new_content}"

        old_content = self.read_file(file_path)
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{file_path} (original)",
            tofile=f"{file_path} (modified)",
            lineterm='\n'
        )

        return ''.join(diff)

    def create_project_structure(self, structure: Dict[str, any]) -> List[str]:
        """
        Create project directory structure.

        Args:
            structure: Nested dict defining structure.
                      Keys are dir/file names, values are:
                      - dict for directories (containing nested structure)
                      - str for files (containing file content)
                      - None for empty directories

        Returns:
            List of created paths.

        Example:
            {
                "src": {
                    "__init__.py": "",
                    "main.py": "print('hello')"
                },
                "tests": None
            }
        """
        created = []

        def _create_recursive(current_path: Path, struct: Dict):
            for name, content in struct.items():
                path = current_path / name

                if isinstance(content, dict):
                    # Directory with nested structure
                    path.mkdir(parents=True, exist_ok=True)
                    created.append(str(path.relative_to(self.project_root)))
                    _create_recursive(path, content)
                elif content is None:
                    # Empty directory
                    path.mkdir(parents=True, exist_ok=True)
                    created.append(str(path.relative_to(self.project_root)))
                else:
                    # File with content
                    path.parent.mkdir(parents=True, exist_ok=True)
                    self.write_file(str(path), str(content))
                    created.append(str(path.relative_to(self.project_root)))

        _create_recursive(self.project_root, structure)
        return created

    def delete_file(self, file_path: str) -> None:
        """
        Delete file with backup.

        Args:
            file_path: Path to file (relative to project_root or absolute).

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        full_path = self._resolve_path(file_path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if self.backup_enabled:
            self._create_backup(full_path)

        full_path.unlink()

    def _resolve_path(self, path: str) -> Path:
        """
        Resolve path relative to project_root or as absolute.

        Args:
            path: Path to resolve.

        Returns:
            Resolved Path object.
        """
        path_obj = Path(path)

        if path_obj.is_absolute():
            return path_obj

        return self.project_root / path_obj

    def _create_backup(self, file_path: Path) -> None:
        """
        Create backup of file with timestamp.

        Args:
            file_path: Path to file to backup.
        """
        if not file_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(file_path, backup_path)

    def get_backup_dir(self) -> str:
        """
        Get path to backup directory.

        Returns:
            Absolute path to backup directory.
        """
        return str(self.backup_dir)

    def restore_from_backup(self, backup_file: str, destination: Optional[str] = None) -> None:
        """
        Restore file from backup.

        Args:
            backup_file: Name of backup file in backup directory.
            destination: Destination path. If None, extracts from backup filename.

        Raises:
            FileNotFoundError: If backup doesn't exist.
        """
        backup_path = self.backup_dir / backup_file

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_file}")

        if destination is None:
            # Extract original filename from backup name (remove timestamp)
            original_name = backup_file.rsplit('.', 2)[0]
            destination = original_name

        dest_path = self._resolve_path(destination)
        shutil.copy2(backup_path, dest_path)
