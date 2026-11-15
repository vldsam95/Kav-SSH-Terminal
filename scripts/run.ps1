$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Remove-ProjectItem {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $Resolved = (Resolve-Path -LiteralPath $Path).Path
    $RootPrefix = (Resolve-Path -LiteralPath $Root).Path.TrimEnd("\") + "\"
    if (-not $Resolved.StartsWith($RootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to delete outside project: $Resolved"
    }

    Remove-Item -LiteralPath $Resolved -Recurse -Force
}

function Optimize-SourceRuntime {
    $PySide = Join-Path $Root ".venv\Lib\site-packages\PySide6"
    if (-not (Test-Path -LiteralPath $PySide)) {
        return
    }

    foreach ($Name in @(
        "doc", "glue", "include", "lib", "metatypes", "qml",
        "resources", "scripts", "translations", "typesystems"
    )) {
        Remove-ProjectItem (Join-Path $PySide $Name)
    }

    foreach ($Pattern in @(
        "assistant.exe", "designer.exe", "linguist.exe", "lrelease.exe", "lupdate.exe",
        "qml*.exe", "opengl32sw.dll", "Qt6Designer*.dll", "Qt6Help.dll",
        "Qt6Qml*.dll", "Qt6Quick*.dll", "Qt6Labs*.dll", "Qt6Lottie*.dll",
        "Qt6OpenGL*.dll", "Qt6Pdf*.dll", "Qt6VirtualKeyboard.dll",
        "QtOpenGL*.pyd", "QtQml*.pyd", "QtQuick*.pyd", "QtDesigner*.pyd",
        "QtHelp.pyd", "QtPdf*.pyd"
    )) {
        Get-ChildItem -Force -File -LiteralPath $PySide -Filter $Pattern -ErrorAction SilentlyContinue |
            ForEach-Object { Remove-ProjectItem $_.FullName }
    }

    $PluginRoot = Join-Path $PySide "plugins"
    if (Test-Path -LiteralPath $PluginRoot) {
        Get-ChildItem -Force -Directory -LiteralPath $PluginRoot |
            Where-Object { $_.Name -notin @("platforms", "styles") } |
            ForEach-Object { Remove-ProjectItem $_.FullName }

        $Platforms = Join-Path $PluginRoot "platforms"
        if (Test-Path -LiteralPath $Platforms) {
            Get-ChildItem -Force -File -LiteralPath $Platforms |
                Where-Object { $_.Name -ne "qwindows.dll" } |
                ForEach-Object { Remove-ProjectItem $_.FullName }
        }
    }

    Get-ChildItem -Recurse -Force -Directory -LiteralPath $Root |
        Where-Object { $_.Name -eq "__pycache__" } |
        ForEach-Object { Remove-ProjectItem $_.FullName }
    Get-ChildItem -Recurse -Force -File -LiteralPath $Root |
        Where-Object { $_.Extension -in ".pyc", ".pyo" } |
        ForEach-Object { Remove-ProjectItem $_.FullName }
}

function Find-SystemPython {
    $Candidates = @(
        @("py", "-3.12"),
        @("py", "-3"),
        @("python")
    )

    foreach ($Candidate in $Candidates) {
        $Command = $Candidate[0]
        $Arguments = @($Candidate | Select-Object -Skip 1)
        try {
            & $Command @Arguments -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return @{ Command = $Command; Arguments = $Arguments }
            }
        } catch {
            continue
        }
    }

    return $null
}

function Test-RuntimeReady {
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $Python)) {
        return $false
    }

    & $Python -B -c "import main; from PySide6.QtCore import Qt; import asyncssh, keyring, pydantic, pyte, bidi, wcwidth" 2>$null
    return $LASTEXITCODE -eq 0
}

function New-AppVenv {
    $SystemPython = Find-SystemPython
    if ($null -eq $SystemPython) {
        throw "Python 3.12+ is required. Install Python from https://www.python.org/downloads/ and run this file again."
    }

    if (Test-Path -LiteralPath ".venv") {
        Remove-ProjectItem (Join-Path $Root ".venv")
    }

    & $SystemPython.Command @($SystemPython.Arguments) -m venv .venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not (Test-RuntimeReady)) {
    if (-not (Test-Path ".venv")) {
        New-AppVenv
    }

    .\.venv\Scripts\python -B -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        New-AppVenv
        .\.venv\Scripts\python -B -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    .\.venv\Scripts\python -B -m pip install -e "."
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Optimize-SourceRuntime
}

if (-not (Test-RuntimeReady)) {
    throw "Runtime setup completed, but the app still cannot import its required packages."
}

.\.venv\Scripts\pythonw -B -m main
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
