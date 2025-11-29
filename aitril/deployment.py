"""
Deployment - Flexible deployment system supporting multiple targets.

Strategy pattern implementation that adapts to user requirements:
- Google Colab (notebooks)
- GitHub Pages (static sites)
- AWS (various services)
- Heroku (web apps)
- Vercel (web apps)
- Docker Hub (containers)
- PyPI (Python packages)
- Local file system
"""
import os
import json
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from pathlib import Path


class DeploymentError(Exception):
    """Raised when deployment fails."""
    pass


class DeploymentStrategy(ABC):
    """Base class for deployment strategies."""

    @abstractmethod
    def deploy(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """
        Deploy files/project to target.

        Args:
            source_path: Path to file or directory to deploy
            **kwargs: Strategy-specific configuration

        Returns:
            Dict with deployment results (urls, status, etc.)
        """
        pass

    @abstractmethod
    def supports(self, project_type: str) -> bool:
        """Check if this strategy supports the project type."""
        pass

    @abstractmethod
    def get_requirements(self) -> List[str]:
        """Get list of requirements/prerequisites for this deployment."""
        pass


class GoogleColabStrategy(DeploymentStrategy):
    """Deploy Jupyter notebooks to Google Colab via Drive."""

    def supports(self, project_type: str) -> bool:
        return project_type in ["jupyter_notebook", "notebook", "ipynb"]

    def get_requirements(self) -> List[str]:
        return [
            "Google Cloud credentials (OAuth)",
            "google-api-python-client",
            "google-auth-httplib2",
            "google-auth-oauthlib"
        ]

    def deploy(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """Deploy notebook to Google Drive for Colab access."""
        # For now, return instructions (full implementation requires OAuth)
        return {
            "status": "manual_upload_required",
            "colab_url": "https://colab.research.google.com/",
            "instructions": [
                "1. Go to https://colab.research.google.com/",
                f"2. Upload file: {source_path}",
                "3. Or set up Google Drive API for automatic upload"
            ],
            "notebook_path": source_path
        }


class GitHubPagesStrategy(DeploymentStrategy):
    """Deploy static sites to GitHub Pages."""

    def supports(self, project_type: str) -> bool:
        return project_type in ["static_site", "html", "web", "docs"]

    def get_requirements(self) -> List[str]:
        return ["git", "GitHub repository", "gh CLI (optional)"]

    def deploy(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """Deploy to GitHub Pages."""
        repo_url = kwargs.get("repo_url")
        branch = kwargs.get("branch", "gh-pages")

        if not repo_url:
            raise DeploymentError("repo_url required for GitHub Pages deployment")

        try:
            # Initialize git if needed
            if not os.path.exists(os.path.join(source_path, ".git")):
                subprocess.run(["git", "init"], cwd=source_path, check=True)

            # Add remote
            subprocess.run(
                ["git", "remote", "add", "origin", repo_url],
                cwd=source_path,
                capture_output=True
            )

            # Commit and push
            subprocess.run(["git", "add", "."], cwd=source_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Deploy to GitHub Pages"],
                cwd=source_path,
                check=True
            )
            subprocess.run(
                ["git", "push", "-u", "origin", branch],
                cwd=source_path,
                check=True
            )

            # Extract GitHub Pages URL
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            username = repo_url.split("/")[-2]
            pages_url = f"https://{username}.github.io/{repo_name}/"

            return {
                "status": "deployed",
                "url": pages_url,
                "repo_url": repo_url,
                "branch": branch
            }

        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"GitHub Pages deployment failed: {e}")


class HerokuStrategy(DeploymentStrategy):
    """Deploy web apps to Heroku."""

    def supports(self, project_type: str) -> bool:
        return project_type in ["web_app", "api", "backend", "python_app"]

    def get_requirements(self) -> List[str]:
        return ["Heroku CLI", "Heroku account", "Procfile", "requirements.txt"]

    def deploy(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """Deploy to Heroku."""
        app_name = kwargs.get("app_name")

        try:
            # Create Heroku app if needed
            if app_name:
                subprocess.run(
                    ["heroku", "create", app_name],
                    cwd=source_path,
                    capture_output=True
                )

            # Deploy
            subprocess.run(["git", "push", "heroku", "main"], cwd=source_path, check=True)

            # Get app URL
            result = subprocess.run(
                ["heroku", "apps:info", "--json"],
                cwd=source_path,
                capture_output=True,
                text=True,
                check=True
            )

            app_info = json.loads(result.stdout)
            app_url = app_info["app"]["web_url"]

            return {
                "status": "deployed",
                "url": app_url,
                "app_name": app_info["app"]["name"]
            }

        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Heroku deployment failed: {e}")


class VercelStrategy(DeploymentStrategy):
    """Deploy web apps to Vercel."""

    def supports(self, project_type: str) -> bool:
        return project_type in ["web_app", "nextjs", "react", "static_site"]

    def get_requirements(self) -> List[str]:
        return ["Vercel CLI", "Vercel account"]

    def deploy(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """Deploy to Vercel."""
        try:
            production = kwargs.get("production", True)
            cmd = ["vercel", "--yes"]
            if production:
                cmd.append("--prod")

            result = subprocess.run(
                cmd,
                cwd=source_path,
                capture_output=True,
                text=True,
                check=True
            )

            # Extract URL from output
            url = result.stdout.strip().split("\n")[-1]

            return {
                "status": "deployed",
                "url": url,
                "production": production
            }

        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Vercel deployment failed: {e}")


class DockerHubStrategy(DeploymentStrategy):
    """Deploy containers to Docker Hub."""

    def supports(self, project_type: str) -> bool:
        return project_type in ["container", "docker", "dockerfile"]

    def get_requirements(self) -> List[str]:
        return ["Docker", "Docker Hub account"]

    def deploy(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """Build and push to Docker Hub."""
        image_name = kwargs.get("image_name")
        tag = kwargs.get("tag", "latest")

        if not image_name:
            raise DeploymentError("image_name required for Docker Hub deployment")

        try:
            # Build image
            subprocess.run(
                ["docker", "build", "-t", f"{image_name}:{tag}", "."],
                cwd=source_path,
                check=True
            )

            # Push to Docker Hub
            subprocess.run(
                ["docker", "push", f"{image_name}:{tag}"],
                check=True
            )

            return {
                "status": "deployed",
                "image": f"{image_name}:{tag}",
                "registry": "hub.docker.com",
                "pull_command": f"docker pull {image_name}:{tag}"
            }

        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Docker Hub deployment failed: {e}")


class LocalStrategy(DeploymentStrategy):
    """Copy files locally (for testing/backup)."""

    def supports(self, project_type: str) -> bool:
        return True  # Supports all project types

    def get_requirements(self) -> List[str]:
        return []  # No external requirements

    def deploy(self, source_path: str, **kwargs) -> Dict[str, Any]:
        """Copy to local destination."""
        import shutil
        from pathlib import Path

        # Try to get output_dir from env var, then settings, then fallback
        default_path = os.environ.get(
            "AITRIL_OUTPUTS_DIR",
            str(Path.home() / "Documents" / "projects" / "aitril_outputs")
        )
        dest_path = kwargs.get("dest_path", default_path)

        if os.path.isfile(source_path):
            os.makedirs(dest_path, exist_ok=True)
            target = os.path.join(dest_path, os.path.basename(source_path))
            shutil.copy2(source_path, target)
        else:
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.copytree(source_path, dest_path)
            target = dest_path

        return {
            "status": "deployed",
            "local_path": target,
            "type": "file" if os.path.isfile(target) else "directory"
        }


class DeploymentManager:
    """Manages deployment strategies and selects appropriate target."""

    def __init__(self):
        self.strategies: Dict[str, DeploymentStrategy] = {
            "google_colab": GoogleColabStrategy(),
            "github_pages": GitHubPagesStrategy(),
            "heroku": HerokuStrategy(),
            "vercel": VercelStrategy(),
            "docker_hub": DockerHubStrategy(),
            "local": LocalStrategy()
        }

    def register_strategy(self, name: str, strategy: DeploymentStrategy):
        """Register a custom deployment strategy."""
        self.strategies[name] = strategy

    def get_compatible_strategies(self, project_type: str) -> List[str]:
        """Get list of strategies that support the project type."""
        return [
            name for name, strategy in self.strategies.items()
            if strategy.supports(project_type)
        ]

    def deploy(
        self,
        source_path: str,
        target: Optional[str] = None,
        project_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Deploy to specified target or auto-select based on project type.

        Args:
            source_path: Path to deploy
            target: Specific deployment target name (optional)
            project_type: Type of project (optional, for auto-selection)
            **kwargs: Strategy-specific parameters

        Returns:
            Dict with deployment results
        """
        # Auto-detect project type if not specified
        if not project_type:
            project_type = self._detect_project_type(source_path)

        # Use specified target or auto-select
        if target:
            if target not in self.strategies:
                raise DeploymentError(f"Unknown deployment target: {target}")
            strategy = self.strategies[target]
        else:
            # Auto-select first compatible strategy
            compatible = self.get_compatible_strategies(project_type)
            if not compatible:
                raise DeploymentError(
                    f"No deployment strategy supports project type: {project_type}"
                )
            strategy = self.strategies[compatible[0]]
            target = compatible[0]

        # Check if strategy supports this project type
        if not strategy.supports(project_type):
            raise DeploymentError(
                f"{target} does not support project type: {project_type}"
            )

        # Execute deployment
        result = strategy.deploy(source_path, **kwargs)
        result["deployment_target"] = target
        result["project_type"] = project_type

        return result

    def _detect_project_type(self, path: str) -> str:
        """Auto-detect project type from path."""
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1]
            if ext == ".ipynb":
                return "jupyter_notebook"
            elif ext == ".html":
                return "static_site"
            elif ext in [".py", ".pyw"]:
                return "python_app"

        # Check directory contents
        if os.path.isdir(path):
            files = os.listdir(path)
            if "Dockerfile" in files:
                return "container"
            elif "package.json" in files:
                return "web_app"
            elif "requirements.txt" in files or "setup.py" in files:
                return "python_app"
            elif "index.html" in files:
                return "static_site"

        return "unknown"
