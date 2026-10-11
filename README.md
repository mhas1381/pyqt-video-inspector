# Video Inspector

Desktop app for opening a video, browsing frames, selecting a rectangular ROI, and viewing an RGB histogram of the selected region.

Built with **PyQt6**, **OpenCV**, and **NumPy**.

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)

Dependencies are CPU-only (`numpy`, `opencv-python`, `PyQt6`). No NVIDIA/CUDA drivers or GPU packages are needed.

## Setup

### 1. Install uv

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen the terminal afterwards so `uv` is on your `PATH`. If it is still not found,
add `%USERPROFILE%\.local\bin` to your user `PATH`.

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify the installation:

```powershell
uv --version
```

### 2. Install Python 3.12 and the dependencies

`uv` downloads the Python version pinned in `.python-version` automatically, so no separate
Python install is needed:

```powershell
uv sync
```

This creates a virtual environment in `.venv\` and installs `PyQt6`, `opencv-python`, and `numpy`.

### 3. Run the app

```powershell
uv run pyqt-video-inspector
```

The command launches the GUI window. You do not need to activate the environment first —
`uv run` does that for you.

### Troubleshooting

**`uv` is not recognized** — reopen the terminal, or add `%USERPROFILE%\.local\bin` to your
user `PATH` environment variable.

**Missing DLL / application fails to start on Windows** — `opencv-python` needs the
[Microsoft Visual C++ Redistributable](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist).
Install the x64 build if the app crashes immediately on launch.

**Qt platform plugin errors** (`could not load or find the Qt platform plugin "windows"`) —
the environment inherited from the shell is interfering. Try launching from a fresh
PowerShell window, or reset the variable:

```powershell
$env:QT_QPA_PLATFORM = ""
```

**Rebuilding the environment from scratch:**

```powershell
Remove-Item -Recurse -Force .venv
uv sync
```

## Features

- Open common video formats (mp4, avi, mkv, mov, …)
- Show resolution, FPS, and frame count
- Seek with a slider and numeric frame input
- Play / Pause with `QTimer`
- Drag a rectangular ROI on the frame
- RGB histogram in a separate window (updates live while open)
