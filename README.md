# Football Kit Contrast Check

A small Python web app for comparing two football kits side by side. It is designed for referees who need a quick visual check before choosing match clothing that contrasts clearly with both teams.

The app searches `zerozero.pt`, opens the first matching team pages, and displays the kit images found there.

## Running Locally

Open the Windows Command Prompt (`cmd.exe`) and go to the project folder:

```cmd
cd C:\Users\Utilizador\TesteSoPython\kit
```

Then activate the virtual environment:

```cmd
.venv\Scripts\activate.bat
```

Then run the Streamlit app:

```cmd
python -m streamlit run app.py
```

Open `http://localhost:8501`.

## Stopping the App

To stop the app, go back to the Command Prompt window where Streamlit is running and press:

```cmd
Ctrl+C
```

You can also run it without activating the virtual environment:

```cmd
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Development

Streamlit reloads the app when `app.py` changes. If the browser does not update, stop the server with `Ctrl+C` and start it again.

## Notes

- Uses Streamlit for the web interface.
- This app does not perform OCR or extract text from kit images. It finds kit image URLs in the team page HTML.
- Kit images are loaded from `zerozero.pt`.
- Search quality depends on the first team match returned by `zerozero.pt`.
