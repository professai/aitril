# AiTril Deployment Checkpoint - v0.0.36

**Date**: 2025-11-29
**Version**: 0.0.36
**Critical**: Read this EVERY time before deploying

## ⚠️ CRITICAL: Repository Naming Convention

### The Canonical Repositories

**GitHub Organization**: `professai`
- Main repository: `git@github.com:professai/aitril.git`
- Landing page: `git@github.com:professai/aitril-landing.git`

**PyPI Package**: `aitril`
- URL: https://pypi.org/project/aitril/
- Install: `pip install aitril`

**Docker Hub**: `collinparan/aitril` (CURRENT)
- URL: https://hub.docker.com/r/collinparan/aitril
- Pull: `docker pull collinparan/aitril:0.0.36`
- Pull: `docker pull collinparan/aitril:latest`
- **Note**: Using personal account until project gains popularity
- **Future**: Will migrate to `professai/aitril` when worth paying for organization account

### ❌ Common Mistakes to Avoid

1. **DO NOT change Docker Hub repository without asking first**
   - Current canonical Docker repository: `collinparan/aitril`
   - Will migrate to `professai/aitril` in the future when project grows
   - All documentation must reference `collinparan/aitril` for now

2. **DO NOT update documentation without verifying all references**
   - Check README.md for Docker Hub references
   - Check .env.example for Docker Hub references
   - Check landing page for Docker Hub references
   - Ensure ALL references use `collinparan/aitril` (current standard)

3. **DO NOT assume authorization will work**
   - Docker Hub uses `collinparan` account (logged in via Docker Desktop)
   - GitHub uses `professai` organization (SSH keys configured)
   - PyPI uses token authentication (stored in .env)

## 📋 Pre-Deployment Checklist

Before deploying any version:

- [ ] Verify version number is consistent across:
  - [ ] `pyproject.toml` (version field)
  - [ ] `aitril/__init__.py` (__version__)
  - [ ] `README.md` (header, install instructions)
  - [ ] `.env.example` (header comment)
  - [ ] Landing page `index.html` (meta description, title, install section)

- [ ] Verify repository references are consistent:
  - [ ] README.md Docker pull commands use `professai/aitril`
  - [ ] .env.example Docker Hub URL uses `professai/aitril`
  - [ ] Landing page (if applicable) uses `professai/aitril`

- [ ] Test the build locally:
  - [ ] `docker-compose build` succeeds
  - [ ] Image is tagged correctly: `professai/aitril:X.X.X` and `professai/aitril:latest`
  - [ ] Test container runs: `docker run professai/aitril:latest aitril --version`

## 🚀 Deployment Sequence (v0.0.36)

### 1. Code Changes & Documentation
```bash
# Make code changes
# Update version in pyproject.toml, __init__.py
# Update README.md, .env.example with new features
# Update landing page if needed
```

### 2. Git Commit & Push
```bash
cd /Users/collinparan/Documents/projects/aitril
git add [files]
git commit -m "vX.X.X: [description]"
git push origin main

# If landing page updated:
cd /Users/collinparan/Documents/projects/aitril-landing
git add index.html
git commit -m "Update landing page for vX.X.X: [features]"
git push origin main
```

### 3. PyPI Deployment
```bash
cd /Users/collinparan/Documents/projects/aitril
rm -rf dist/ build/ aitril.egg-info/
python3 -m build

# Use credentials from .env or environment
TWINE_USERNAME=__token__ \
TWINE_PASSWORD=$PYPI_TOKEN \
twine upload dist/*

# Verify upload
for i in {1..10}; do
  echo "Checking availability (attempt $i/10)..."
  if curl -s https://pypi.org/pypi/aitril/X.X.X/json | grep -q "X.X.X"; then
    echo "✓ vX.X.X is now available on PyPI!"
    break
  fi
  sleep 10
done
```

### 4. Docker Hub Deployment

**IMPORTANT**: Currently using `collinparan/aitril` until project gains popularity.

```bash
cd /Users/collinparan/Documents/projects/aitril

# Verify Docker Desktop is running
docker info

# Build image with correct tags
docker build -t collinparan/aitril:X.X.X -t collinparan/aitril:latest .

# Verify image built
docker images | grep aitril

# Push version tag (Docker Desktop already logged in to collinparan)
docker push collinparan/aitril:X.X.X

# Push latest tag
docker push collinparan/aitril:latest

# Verify push succeeded
docker pull collinparan/aitril:X.X.X
```

**Future Migration to `professai/aitril`**:
When the project gains popularity and it's worth paying for organization account:
1. Create `professai/aitril` repository on Docker Hub
2. Update ALL documentation (README.md, .env.example, landing page)
3. Build and push to both repositories during transition period
4. Announce deprecation of `collinparan/aitril`

### 5. Verification

```bash
# Verify all deployments
echo "=== Verification ==="

# Check Git
echo "Git commits:"
cd /Users/collinparan/Documents/projects/aitril
git log --oneline -1

# Check PyPI
echo "PyPI package:"
pip3 index versions aitril 2>&1 | head -5

# Check Docker Hub
echo "Docker Hub image:"
docker pull professai/aitril:latest
docker run --rm professai/aitril:latest aitril --version
```

## 📝 Current State (v0.0.36)

**Completed**:
- ✅ Code committed to `professai/aitril` (commit: b8e487d)
- ✅ Landing page committed to `professai/aitril-landing` (commit: e5a10b1)
- ✅ Both repositories pushed to GitHub
- ✅ Docker image built locally
- ✅ Docker image pushed to `collinparan/aitril:0.0.36` and `:latest`
- ✅ Documentation updated to use `collinparan/aitril` consistently

**Pending**:
- ❌ PyPI deployment for v0.0.36 (if not already done)
- ❌ Commit documentation updates (.env.example, DEPLOYMENT_CHECKPOINT.md)

**Action Required**:
1. Commit and push the updated documentation files
2. Verify PyPI has v0.0.36 or deploy if needed

**Decision Made** (2025-11-29):
- Using `collinparan/aitril` on Docker Hub for now
- Will migrate to `professai/aitril` when project gains popularity
- All documentation now consistently references `collinparan/aitril`

## 🔐 Credentials Reference

**PyPI**:
- Username: `__token__`
- Token: Stored in environment or .env file
- Scope: Upload permissions for `aitril` package

**Docker Hub**:
- Primary account: `professai` (requires login)
- Fallback account: `collinparan` (currently logged in via Docker Desktop)
- Token: Not yet configured in .env

**GitHub**:
- SSH keys configured for `professai` organization access
- Repositories: `professai/aitril`, `professai/aitril-landing`

## 📚 Documentation Files to Keep Consistent

When updating version or features, check ALL of these files:

1. **Version Number**:
   - `/Users/collinparan/Documents/projects/aitril/pyproject.toml` (line ~4: `version = "X.X.X"`)
   - `/Users/collinparan/Documents/projects/aitril/aitril/__init__.py` (line ~1: `__version__ = "X.X.X"`)
   - `/Users/collinparan/Documents/projects/aitril/README.md` (line 3: `**Latest: vX.X.X**`)
   - `/Users/collinparan/Documents/projects/aitril/.env.example` (line 13: `# Version: X.X.X`)
   - `/Users/collinparan/Documents/projects/aitril-landing/index.html` (line 6-7: meta & title)

2. **Docker Hub References** (currently `collinparan/aitril`):
   - `/Users/collinparan/Documents/projects/aitril/README.md` (search for "docker pull")
   - `/Users/collinparan/Documents/projects/aitril/.env.example` (line 266: Docker Hub URL)
   - Any deployment scripts or documentation
   - All should reference `collinparan/aitril` until migration to `professai/aitril`

3. **GitHub Repository References**:
   - All should use `professai/aitril` or `professai/aitril-landing`
   - No references to personal accounts in public docs

## 🎯 Key Lessons

1. **Consistency is Critical**: All platform references (GitHub, PyPI, Docker Hub) should use the same organization/account name for a professional project.

2. **Verify Before Acting**: When authorization fails, STOP and ask rather than pushing to an alternative repository.

3. **Document Everything**: This checkpoint exists to prevent repeated mistakes across session boundaries.

4. **Check All References**: A version update or repository change affects multiple files across multiple repositories.

---

**Last Updated**: 2025-11-29
**By**: Claude Code (checkpoint creation for v0.0.36 deployment)
