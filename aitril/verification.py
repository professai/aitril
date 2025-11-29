"""
Verification - File and content verification for multi-agent workflows.

Ensures files are actually created with valid content before reporting success.
"""
import os
import json
from typing import Dict, List, Optional
from pathlib import Path


class VerificationError(Exception):
    """Raised when verification fails."""
    pass


class FileVerifier:
    """Verify files are created correctly with valid content."""

    @staticmethod
    def verify_file_exists(file_path: str) -> bool:
        """
        Verify file exists.

        Args:
            file_path: Path to file

        Returns:
            bool: True if file exists

        Raises:
            VerificationError: If file doesn't exist
        """
        if not os.path.exists(file_path):
            raise VerificationError(f"File not found: {file_path}")
        return True

    @staticmethod
    def verify_file_size(file_path: str, min_size: int = 100) -> bool:
        """
        Verify file has minimum size.

        Args:
            file_path: Path to file
            min_size: Minimum file size in bytes

        Returns:
            bool: True if file meets minimum size

        Raises:
            VerificationError: If file is too small
        """
        FileVerifier.verify_file_exists(file_path)

        size = os.path.getsize(file_path)
        if size < min_size:
            raise VerificationError(
                f"File too small: {file_path} ({size} bytes, minimum {min_size})"
            )
        return True

    @staticmethod
    def verify_json_file(file_path: str) -> bool:
        """
        Verify file contains valid JSON.

        Args:
            file_path: Path to JSON file

        Returns:
            bool: True if valid JSON

        Raises:
            VerificationError: If JSON is invalid
        """
        FileVerifier.verify_file_size(file_path, min_size=10)

        try:
            with open(file_path, 'r') as f:
                json.load(f)
            return True
        except json.JSONDecodeError as e:
            raise VerificationError(
                f"Invalid JSON in {file_path}: {e}"
            )

    @staticmethod
    def verify_notebook(file_path: str) -> bool:
        """
        Verify Jupyter notebook has valid structure.

        Args:
            file_path: Path to .ipynb file

        Returns:
            bool: True if valid notebook

        Raises:
            VerificationError: If notebook is invalid
        """
        FileVerifier.verify_json_file(file_path)

        with open(file_path, 'r') as f:
            nb = json.load(f)

        # Check required fields
        if "cells" not in nb:
            raise VerificationError(
                f"Notebook missing 'cells' field: {file_path}"
            )

        if not isinstance(nb["cells"], list):
            raise VerificationError(
                f"Notebook 'cells' must be a list: {file_path}"
            )

        if len(nb["cells"]) == 0:
            raise VerificationError(
                f"Notebook has no cells: {file_path}"
            )

        # Check first cell has content
        first_cell = nb["cells"][0]
        if "source" not in first_cell or not first_cell["source"]:
            raise VerificationError(
                f"First cell has no content: {file_path}"
            )

        return True

    @staticmethod
    def verify_python_file(file_path: str) -> bool:
        """
        Verify Python file has valid syntax.

        Args:
            file_path: Path to .py file

        Returns:
            bool: True if valid Python

        Raises:
            VerificationError: If Python syntax is invalid
        """
        FileVerifier.verify_file_size(file_path, min_size=10)

        try:
            with open(file_path, 'r') as f:
                compile(f.read(), file_path, 'exec')
            return True
        except SyntaxError as e:
            raise VerificationError(
                f"Python syntax error in {file_path}: {e}"
            )

    @staticmethod
    def verify_directory_structure(
        base_path: str,
        expected_files: List[str]
    ) -> Dict[str, bool]:
        """
        Verify directory contains expected files.

        Args:
            base_path: Base directory path
            expected_files: List of expected file paths (relative to base)

        Returns:
            Dict mapping file paths to verification status

        Raises:
            VerificationError: If any expected file is missing
        """
        results = {}
        missing_files = []

        for file_path in expected_files:
            full_path = os.path.join(base_path, file_path)
            try:
                FileVerifier.verify_file_exists(full_path)
                results[file_path] = True
            except VerificationError:
                results[file_path] = False
                missing_files.append(file_path)

        if missing_files:
            raise VerificationError(
                f"Missing files: {', '.join(missing_files)}"
            )

        return results


class ContentVerifier:
    """Verify content meets requirements."""

    @staticmethod
    def verify_not_empty(content: str, name: str = "Content") -> bool:
        """
        Verify content is not empty.

        Args:
            content: Content to verify
            name: Name for error messages

        Returns:
            bool: True if content is not empty

        Raises:
            VerificationError: If content is empty
        """
        if not content or not content.strip():
            raise VerificationError(f"{name} is empty")
        return True

    @staticmethod
    def verify_min_length(
        content: str,
        min_length: int,
        name: str = "Content"
    ) -> bool:
        """
        Verify content meets minimum length.

        Args:
            content: Content to verify
            min_length: Minimum length
            name: Name for error messages

        Returns:
            bool: True if content meets minimum length

        Raises:
            VerificationError: If content is too short
        """
        ContentVerifier.verify_not_empty(content, name)

        if len(content) < min_length:
            raise VerificationError(
                f"{name} too short: {len(content)} chars (minimum {min_length})"
            )
        return True

    @staticmethod
    def verify_contains(
        content: str,
        required_strings: List[str],
        name: str = "Content"
    ) -> bool:
        """
        Verify content contains required strings.

        Args:
            content: Content to verify
            required_strings: List of required strings
            name: Name for error messages

        Returns:
            bool: True if all required strings are present

        Raises:
            VerificationError: If any required string is missing
        """
        missing = [s for s in required_strings if s not in content]

        if missing:
            raise VerificationError(
                f"{name} missing required strings: {', '.join(missing)}"
            )
        return True


def verify_project_files(
    project_dir: str,
    expected_structure: Dict[str, Dict]
) -> Dict[str, bool]:
    """
    Verify entire project structure and file contents.

    Args:
        project_dir: Base project directory
        expected_structure: Dict mapping file paths to verification config
            Example:
            {
                "notebooks/file.ipynb": {"type": "notebook"},
                "data/data.json": {"type": "json", "min_size": 100},
                "scripts/script.py": {"type": "python"}
            }

    Returns:
        Dict mapping file paths to verification results

    Raises:
        VerificationError: If any verification fails
    """
    results = {}

    for file_path, config in expected_structure.items():
        full_path = os.path.join(project_dir, file_path)

        try:
            file_type = config.get("type", "file")
            min_size = config.get("min_size", 100)

            if file_type == "notebook":
                FileVerifier.verify_notebook(full_path)
            elif file_type == "json":
                FileVerifier.verify_json_file(full_path)
            elif file_type == "python":
                FileVerifier.verify_python_file(full_path)
            else:
                FileVerifier.verify_file_size(full_path, min_size)

            results[file_path] = True

        except VerificationError as e:
            results[file_path] = False
            raise VerificationError(f"Verification failed for {file_path}: {e}")

    return results
