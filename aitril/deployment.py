"""
AiTril Deployment Module

Handles deployment of generated code to various targets:
- Local file system
- Docker container
- GitHub Pages
- AWS EC2
- Vercel/Netlify
"""

import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Any


class DeploymentTarget(ABC):
    """Base class for deployment targets."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def deploy(self, files: Dict[str, str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy files to target.

        Args:
            files: Dictionary of {filename: content}
            metadata: Deployment metadata (project name, description, etc.)

        Returns:
            Dictionary with deployment result (status, url, message, etc.)
        """
        pass

    @abstractmethod
    def validate_config(self) -> tuple[bool, Optional[str]]:
        """
        Validate deployment configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass


class LocalDeployment(DeploymentTarget):
    """Deploy to local file system."""

    def validate_config(self) -> tuple[bool, Optional[str]]:
        output_dir = self.config.get('output_dir')
        if not output_dir:
            return False, "output_dir is required"
        return True, None

    async def deploy(self, files: Dict[str, str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Save files to local directory."""
        output_dir = Path(self.config['output_dir']).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        deployed_files = []
        for filename, content in files.items():
            file_path = output_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            deployed_files.append(str(file_path))

        return {
            'status': 'success',
            'message': f'Deployed {len(deployed_files)} files to {output_dir}',
            'location': str(output_dir),
            'files': deployed_files
        }


class DockerDeployment(DeploymentTarget):
    """Deploy as a Docker container."""

    def validate_config(self) -> tuple[bool, Optional[str]]:
        image_name = self.config.get('image_name')
        if not image_name:
            return False, "image_name is required"
        return True, None

    async def deploy(self, files: Dict[str, str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build and optionally run a Docker container."""
        image_name = self.config['image_name']
        container_name = self.config.get('container_name', image_name.replace(':', '-'))
        port = self.config.get('port', 8080)
        auto_run = self.config.get('auto_run', True)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write files
            for filename, content in files.items():
                file_path = temp_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            # Create Dockerfile if not provided
            if 'Dockerfile' not in files:
                dockerfile_content = self._generate_dockerfile(files, metadata)
                (temp_path / 'Dockerfile').write_text(dockerfile_content)

            # Build image
            build_result = subprocess.run(
                ['docker', 'build', '-t', image_name, '.'],
                cwd=temp_path,
                capture_output=True,
                text=True
            )

            if build_result.returncode != 0:
                return {
                    'status': 'error',
                    'message': f'Docker build failed: {build_result.stderr}'
                }

            result = {
                'status': 'success',
                'message': f'Docker image built: {image_name}',
                'image': image_name
            }

            # Run container if requested
            if auto_run:
                # Stop existing container if running
                subprocess.run(
                    ['docker', 'stop', container_name],
                    capture_output=True
                )
                subprocess.run(
                    ['docker', 'rm', container_name],
                    capture_output=True
                )

                # Run new container
                run_result = subprocess.run(
                    ['docker', 'run', '-d', '--name', container_name,
                     '-p', f'{port}:{port}', image_name],
                    capture_output=True,
                    text=True
                )

                if run_result.returncode == 0:
                    result['container'] = container_name
                    result['url'] = f'http://localhost:{port}'
                    result['message'] += f'\nContainer running: {container_name} on port {port}'
                else:
                    result['message'] += f'\nWarning: Container run failed: {run_result.stderr}'

            return result

    def _generate_dockerfile(self, files: Dict[str, str], metadata: Dict[str, Any]) -> str:
        """Generate a basic Dockerfile based on detected file types."""
        has_python = any(f.endswith('.py') for f in files)
        has_node = 'package.json' in files
        has_html = any(f.endswith('.html') for f in files)

        if has_python:
            return """FROM python:3.14-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt || true
EXPOSE 8080
CMD ["python", "app.py"]
"""
        elif has_node:
            return """FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 8080
CMD ["npm", "start"]
"""
        elif has_html:
            return """FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
"""
        else:
            return """FROM alpine:latest
WORKDIR /app
COPY . .
EXPOSE 8080
CMD ["sh", "-c", "echo 'Deployed files:' && ls -la"]
"""


class GitHubPagesDeployment(DeploymentTarget):
    """Deploy to GitHub Pages."""

    def validate_config(self) -> tuple[bool, Optional[str]]:
        repo_url = self.config.get('repo_url')
        if not repo_url:
            return False, "repo_url is required"
        return True, None

    async def deploy(self, files: Dict[str, str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to GitHub Pages via gh-pages branch."""
        repo_url = self.config['repo_url']
        branch = self.config.get('branch', 'gh-pages')

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Clone repository
            clone_result = subprocess.run(
                ['git', 'clone', repo_url, '.'],
                cwd=temp_path,
                capture_output=True,
                text=True
            )

            if clone_result.returncode != 0:
                return {
                    'status': 'error',
                    'message': f'Git clone failed: {clone_result.stderr}'
                }

            # Create/checkout gh-pages branch
            subprocess.run(['git', 'checkout', '-b', branch], cwd=temp_path, capture_output=True)
            subprocess.run(['git', 'checkout', branch], cwd=temp_path, capture_output=True)

            # Clear existing files (except .git)
            for item in temp_path.iterdir():
                if item.name != '.git':
                    if item.is_dir():
                        subprocess.run(['rm', '-rf', str(item)])
                    else:
                        item.unlink()

            # Write new files
            for filename, content in files.items():
                file_path = temp_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            # Commit and push
            subprocess.run(['git', 'add', '.'], cwd=temp_path)
            subprocess.run(
                ['git', 'commit', '-m', f'Deploy: {metadata.get("description", "Update")}'],
                cwd=temp_path,
                capture_output=True
            )

            push_result = subprocess.run(
                ['git', 'push', 'origin', branch, '--force'],
                cwd=temp_path,
                capture_output=True,
                text=True
            )

            if push_result.returncode != 0:
                return {
                    'status': 'error',
                    'message': f'Git push failed: {push_result.stderr}'
                }

            # Extract GitHub Pages URL
            repo_parts = repo_url.rstrip('.git').split('/')
            username = repo_parts[-2].split(':')[-1]
            repo_name = repo_parts[-1]
            gh_pages_url = f'https://{username}.github.io/{repo_name}/'

            return {
                'status': 'success',
                'message': f'Deployed to GitHub Pages',
                'url': gh_pages_url,
                'branch': branch
            }


class EC2Deployment(DeploymentTarget):
    """Deploy to AWS EC2 instance."""

    def validate_config(self) -> tuple[bool, Optional[str]]:
        required = ['host', 'user', 'key_path']
        for field in required:
            if not self.config.get(field):
                return False, f"{field} is required"
        return True, None

    async def deploy(self, files: Dict[str, str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to EC2 via SCP and SSH."""
        host = self.config['host']
        user = self.config['user']
        key_path = self.config['key_path']
        remote_dir = self.config.get('remote_dir', '/var/www/html')

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write files locally
            for filename, content in files.items():
                file_path = temp_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            # Create remote directory
            ssh_cmd = ['ssh', '-i', key_path, f'{user}@{host}', f'mkdir -p {remote_dir}']
            subprocess.run(ssh_cmd, capture_output=True)

            # Copy files via SCP
            scp_cmd = ['scp', '-i', key_path, '-r', f'{temp_path}/*', f'{user}@{host}:{remote_dir}/']
            scp_result = subprocess.run(scp_cmd, capture_output=True, text=True)

            if scp_result.returncode != 0:
                return {
                    'status': 'error',
                    'message': f'SCP failed: {scp_result.stderr}'
                }

            # Run post-deploy commands if specified
            post_deploy = self.config.get('post_deploy_commands', [])
            for cmd in post_deploy:
                ssh_cmd = ['ssh', '-i', key_path, f'{user}@{host}', cmd]
                subprocess.run(ssh_cmd, capture_output=True)

            return {
                'status': 'success',
                'message': f'Deployed to EC2: {user}@{host}:{remote_dir}',
                'host': host,
                'location': remote_dir
            }


# Deployment factory
DEPLOYMENT_TARGETS = {
    'local': LocalDeployment,
    'docker': DockerDeployment,
    'github': GitHubPagesDeployment,
    'ec2': EC2Deployment,
}


def get_deployment_target(target_type: str, config: Dict[str, Any]) -> Optional[DeploymentTarget]:
    """Get deployment target instance by type."""
    target_class = DEPLOYMENT_TARGETS.get(target_type)
    if not target_class:
        return None
    return target_class(config)
