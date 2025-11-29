# AiTril Installation Script for Windows
# Usage:
#   PowerShell: iwr -useb https://raw.githubusercontent.com/professai/aitril/main/install.ps1 | iex
#   Or: Invoke-WebRequest -Uri https://raw.githubusercontent.com/professai/aitril/main/install.ps1 -UseBasicParsing | Invoke-Expression

# Requires -Version 5.1

$ErrorActionPreference = "Stop"

# Colors for output
function Print-Info {
    param($Message)
    Write-Host "ℹ " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

function Print-Success {
    param($Message)
    Write-Host "✓ " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Print-Warning {
    param($Message)
    Write-Host "⚠ " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Print-Error {
    param($Message)
    Write-Host "✗ " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Print-Header {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║            AiTril Installer v0.0.37                        ║" -ForegroundColor Cyan
    Write-Host "║     Multi-LLM Orchestration CLI Tool                       ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# Check if running as Administrator (optional, for system-wide install)
function Check-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check for Python 3.8+
function Check-Python {
    Print-Info "Checking Python installation..."

    # Try different Python commands
    $pythonCommands = @("python", "python3", "py")
    $pythonCmd = $null
    $pythonVersion = $null

    foreach ($cmd in $pythonCommands) {
        try {
            $version = & $cmd --version 2>&1
            if ($version -match "Python (\d+)\.(\d+)\.(\d+)") {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]

                if ($major -ge 3 -and $minor -ge 8) {
                    $pythonCmd = $cmd
                    $pythonVersion = $version
                    $pythonPath = (Get-Command $cmd).Source
                    Print-Success "Found $pythonVersion at $pythonPath"
                    return $pythonCmd
                }
            }
        } catch {
            continue
        }
    }

    Print-Error "Python 3.8 or higher is required but not found."
    Write-Host ""
    Write-Host "Please install Python from:"
    Write-Host "  - Official installer: https://www.python.org/downloads/"
    Write-Host "  - Microsoft Store: search for 'Python 3.14'"
    Write-Host "  - Chocolatey: choco install python"
    Write-Host "  - Winget: winget install Python.Python.3.14"
    Write-Host ""
    Write-Host "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

# Check for pip
function Check-Pip {
    param($PythonCmd)

    Print-Info "Checking pip installation..."

    try {
        $pipVersion = & $PythonCmd -m pip --version 2>&1
        Print-Success "Found pip: $pipVersion"
        return "$PythonCmd -m pip"
    } catch {
        Print-Warning "pip not found, attempting to install..."

        try {
            & $PythonCmd -m ensurepip --default-pip
            Print-Success "pip installed successfully"
            return "$PythonCmd -m pip"
        } catch {
            Print-Error "Failed to install pip"
            exit 1
        }
    }
}

# Install AiTril
function Install-AiTril {
    param($PipCmd)

    Print-Info "Installing AiTril from PyPI..."

    try {
        # Split the command string and execute
        $cmdParts = $PipCmd -split ' '
        $pythonExe = $cmdParts[0]
        $pipArgs = $cmdParts[1..($cmdParts.Length - 1)]

        & $pythonExe @pipArgs install aitril --user

        Print-Success "AiTril installed successfully!"
    } catch {
        Print-Error "Failed to install AiTril: $_"
        exit 1
    }
}

# Install with web extras (optional)
function Install-WebExtras {
    param($PipCmd)

    Write-Host ""
    $response = Read-Host "Install web interface? (y/N)"

    if ($response -match "^[Yy]") {
        Print-Info "Installing AiTril with web interface..."

        try {
            $cmdParts = $PipCmd -split ' '
            $pythonExe = $cmdParts[0]
            $pipArgs = $cmdParts[1..($cmdParts.Length - 1)]

            & $pythonExe @pipArgs install "aitril[web]" --user

            Print-Success "Web interface installed!"
        } catch {
            Print-Error "Failed to install web extras: $_"
        }
    }
}

# Setup .env file
function Setup-Env {
    Write-Host ""
    $response = Read-Host "Download .env.example template? (y/N)"

    if ($response -match "^[Yy]") {
        Print-Info "Downloading .env.example..."

        try {
            Invoke-WebRequest -Uri "https://raw.githubusercontent.com/professai/aitril/main/.env.example" `
                -OutFile ".env.example" -UseBasicParsing

            Print-Success "Downloaded .env.example to current directory"
            Print-Info "Copy it to .env and add your API keys:"
            Write-Host "  Copy-Item .env.example .env"
        } catch {
            Print-Warning "Failed to download .env.example: $_"
        }
    }
}

# Check if aitril command is in PATH
function Check-Path {
    param($PythonCmd)

    Print-Info "Checking if aitril is in PATH..."

    $aitrilPath = Get-Command aitril -ErrorAction SilentlyContinue

    if ($aitrilPath) {
        Print-Success "aitril command is available!"

        try {
            $version = & aitril --version 2>&1
            Print-Info "Version: $version"
        } catch {
            Print-Info "Version: unknown"
        }
    } else {
        Print-Warning "aitril command not found in PATH"

        # Check user Scripts directory
        $pythonPath = (Get-Command $PythonCmd).Source
        $pythonDir = Split-Path $pythonPath
        $scriptsDir = Join-Path $pythonDir "Scripts"
        $userScriptsDir = Join-Path $env:APPDATA "Python\Python*\Scripts"

        $possiblePaths = @($scriptsDir) + (Get-ChildItem $userScriptsDir -ErrorAction SilentlyContinue)

        foreach ($path in $possiblePaths) {
            $aitrilExe = Join-Path $path "aitril.exe"
            if (Test-Path $aitrilExe) {
                Print-Info "Found aitril at $aitrilExe"

                # Check if this path is in PATH
                if ($env:PATH -notlike "*$path*") {
                    Print-Warning "$path is not in your PATH"
                    Write-Host ""
                    Write-Host "Add this directory to your PATH:"
                    Write-Host "  1. Open System Properties > Environment Variables"
                    Write-Host "  2. Edit 'Path' under User variables"
                    Write-Host "  3. Add: $path"
                    Write-Host ""
                    Write-Host "Or run this PowerShell command (current session only):"
                    Write-Host "  `$env:PATH += `";$path`""
                }
                break
            }
        }
    }
}

# Print next steps
function Print-NextSteps {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                Installation Complete!                      ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Print-Success "AiTril has been installed successfully!"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host ""
    Write-Host "1. Set up your API keys:"
    Write-Host "   - Copy .env.example to .env"
    Write-Host "   - Add your OpenAI, Anthropic, and/or Google API keys"
    Write-Host ""
    Write-Host "2. Initialize AiTril:"
    Write-Host "   PS> aitril init"
    Write-Host ""
    Write-Host "3. Try a query with Tri-lam mode (3 LLMs):"
    Write-Host "   PS> aitril tri `"Explain quantum computing in simple terms`""
    Write-Host ""
    Write-Host "4. Or use the web interface:"
    Write-Host "   PS> aitril web"
    Write-Host "   Then open: http://localhost:37142"
    Write-Host ""
    Write-Host "Documentation: https://github.com/professai/aitril"
    Write-Host "Issues: https://github.com/professai/aitril/issues"
    Write-Host ""
}

# Main installation flow
function Main {
    Print-Header

    if (Check-Admin) {
        Print-Info "Running as Administrator"
    } else {
        Print-Info "Running as regular user (recommended)"
    }

    $pythonCmd = Check-Python
    $pipCmd = Check-Pip -PythonCmd $pythonCmd
    Install-AiTril -PipCmd $pipCmd
    Install-WebExtras -PipCmd $pipCmd
    Setup-Env
    Check-Path -PythonCmd $pythonCmd
    Print-NextSteps
}

# Run main function
try {
    Main
} catch {
    Print-Error "Installation failed: $_"
    Write-Host $_.ScriptStackTrace
    exit 1
}
