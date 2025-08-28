<#
Creates a .lnk shortcut that launches AutoSort with pythonw.exe (no console).
Optionally copies it to the user's Startup folder (auto-start at logon),
offers to remove the repo copy (i.e., "move" it), and opens Explorer highlighting it.

Usage:
- Right-click → Run with PowerShell
- or: powershell -ExecutionPolicy Bypass -NoProfile -File scripts\create_autosort_shortcut.ps1

Params:
- -NoPromptToStartup      Copy to Startup without asking.
- -NoPromptDeleteRepoCopy If copied to Startup, remove repo copy without asking.
#>

param(
    [switch]$NoPromptToStartup,
    [switch]$NoPromptDeleteRepoCopy
)

# --- Resolve repo root (script is under scripts\) ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir

# --- Ensure venv exists ---
$VenvPythonw = Join-Path $RepoRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $VenvPythonw)) {
    Write-Host "'.venv' not found or missing pythonw.exe. Running 'uv sync' to create it..." -ForegroundColor Yellow
    Push-Location $RepoRoot
    try {
        uv --version *>$null
    } catch {
        Write-Error "UV is not installed or not on PATH. Install UV first: https://docs.astral.sh/uv/install"
        exit 1
    }
    uv sync
    Pop-Location

    if (-not (Test-Path $VenvPythonw)) {
        Write-Error "Still can't find $VenvPythonw. Aborting."
        exit 1
    }
}

# --- Shortcut destinations ---
$ShortcutName   = "Run_AutoSort.lnk"
$ShortcutInRepo = Join-Path $RepoRoot $ShortcutName

# --- Create .lnk using WScript.Shell COM ---
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutInRepo)
$Shortcut.TargetPath       = $VenvPythonw            # windowless interpreter
$Shortcut.Arguments        = '"main.py"'             # quote in case of spaces
$Shortcut.WorkingDirectory = $RepoRoot

# Optional icon (use your own if present)
$IconCandidate = Join-Path $RepoRoot "exe_icon.ico"
if (Test-Path $IconCandidate) { $Shortcut.IconLocation = "$IconCandidate,0" }

$Shortcut.Save()
Write-Host "Created shortcut at: $ShortcutInRepo" -ForegroundColor Green

# --- Offer to copy to Startup ---
$Startup = [Environment]::GetFolderPath('Startup')
$ShortcutInStartup = Join-Path $Startup $ShortcutName

$copy = $true
if (-not $NoPromptToStartup) {
    $ans = Read-Host "Copy shortcut to your Startup folder for silent auto-start at logon? (Y/n)"
    if ($ans -and $ans.ToLower().StartsWith('n')) { $copy = $false }
}

if ($copy) {
    try {
        Copy-Item -Force $ShortcutInRepo $ShortcutInStartup
        Write-Host "Copied to Startup: $ShortcutInStartup" -ForegroundColor Green
        Write-Host "AutoSort will now start silently (no console) on next login." -ForegroundColor Green
    } catch {
        Write-Error "Failed to copy to Startup: $($_.Exception.Message)"
        exit 1
    }

    # --- Ask to remove the repo copy (i.e., move) ---
    $removeRepoCopy = $true
    if (-not $NoPromptDeleteRepoCopy) {
        $rm = Read-Host "Remove the shortcut from the repo now (keep only in Startup)? (Y/n)"
        if ($rm -and $rm.ToLower().StartsWith('n')) { $removeRepoCopy = $false }
    }

    if ($removeRepoCopy) {
        try {
            Remove-Item -Force $ShortcutInRepo
            Write-Host "Removed repo copy: $ShortcutInRepo" -ForegroundColor DarkGray
        } catch {
            Write-Warning "Could not remove repo copy: $($_.Exception.Message)"
        }
    } else {
        Write-Host "Keeping repo copy: $ShortcutInRepo" -ForegroundColor Yellow
    }

    # --- Inform user + wait before opening Explorer ---
    Write-Host "`nOpening Startup folder so you can view the newly added auto-run shortcut..." -ForegroundColor Cyan
    Start-Sleep -Seconds 3

    # --- Open Explorer and highlight the new shortcut ---
    try {
        Start-Process explorer.exe "/select,`"$ShortcutInStartup`""
    } catch {
        Write-Warning "Could not open Explorer: $($_.Exception.Message)"
    }
} else {
    Write-Host "You can manually copy '$ShortcutInRepo' to '$Startup' later." -ForegroundColor Yellow
}
