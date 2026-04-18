# Football Kit Contrast Check

Simple Python website for comparing two football kits side by side. The user types two team names, the app searches `zerozero.pt`, opens the first matching club pages, and shows the kit images used there.

This is useful for referees who want to choose clothing that contrasts clearly with both teams.

## Run

Use Python 3 directly:

```bash
python app.py
```

Then open `http://127.0.0.1:8000`.

## Activate The Virtual Environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

After activation, run:

```bash
python app.py
```

If you prefer not to activate the environment, you can run the app directly with:

```powershell
.\.venv\Scripts\python.exe app.py
```

## Restart After Code Changes

Refreshing the browser is not enough after changing `app.py`, because the Python server keeps the old code in memory.

To restart the server:

1. Go to the terminal where the server is running.
2. Press `Ctrl+C`.
3. Start it again:

```powershell
.\.venv\Scripts\python.exe app.py
```

Then refresh `http://127.0.0.1:8000` in the browser.

## Notes

- The app uses only Python standard library modules.
- The displayed image is the kit/equipment image from `zerozero.pt`, not the badge.
- Search results depend on the first club match returned by `zerozero.pt`.
