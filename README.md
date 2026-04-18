# Football Kit Contrast Check

A small Python web app for comparing two football kits side by side. It is designed for referees who need a quick visual check before choosing match clothing that contrasts clearly with both teams.

The app searches `zerozero.pt`, opens the first matching team pages, and displays the kit images found there.

## Running Locally

```powershell
.\.venv\Scripts\python.exe app.py
```

Open `http://127.0.0.1:8000`.

## Development

The server is a plain Python `http.server` process. Restart it after changes to `app.py`; browser refresh alone only reloads the current response.

## Notes

- Uses only Python standard library modules.
- Kit images are loaded from `zerozero.pt`.
- Search quality depends on the first team match returned by `zerozero.pt`.
