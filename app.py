from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.request import Request, urlopen
import re


BASE_URL = "https://www.zerozero.pt"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def fetch_page(url: str) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore"), response.geturl()


def normalize_zerozero_url(path_or_url: str) -> str:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return f"{BASE_URL}{path_or_url}"


def is_team_page(url: str) -> bool:
    return bool(re.search(r"/equipa/[^/?#]+(?:/\d+)?", url, re.IGNORECASE))


def find_team_page(search_html: str, club_name: str) -> str | None:
    matches = re.findall(r'href="(/equipa/[^"#?]+(?:/\d+)?)', search_html, re.IGNORECASE)
    normalized_query = re.sub(r"[^a-z0-9]+", "", club_name.lower())

    candidates = []
    seen = set()
    for match in matches:
        team_url = normalize_zerozero_url(match)
        if team_url in seen:
            continue
        seen.add(team_url)
        candidates.append(team_url)

    if not candidates:
        return None

    for team_url in candidates:
        slug = team_url.rstrip("/").split("/")[-1].lower()
        if slug.isdigit() and len(team_url.rstrip("/").split("/")) >= 2:
            slug = team_url.rstrip("/").split("/")[-2].lower()
        normalized_slug = re.sub(r"[^a-z0-9]+", "", slug)
        if normalized_query and normalized_query in normalized_slug:
            return team_url

    return candidates[0]


def find_kit_image(team_html: str) -> str | None:
    match = re.search(
        r'((?:https?:)?//[^"\']+_shirt_[^"\']+\.(?:png|jpg|jpeg|webp|svg)|'
        r'/img/logos/equipas/[^"\']+_shirt_[^"\']+\.(?:png|jpg|jpeg|webp|svg))',
        team_html,
        re.IGNORECASE,
    )
    if not match:
        return None

    image_url = match.group(1)
    if image_url.startswith("//"):
        return f"https:{image_url}"
    return normalize_zerozero_url(image_url)


def find_team_name(team_html: str, fallback: str) -> str:
    match = re.search(r"<title>\s*([^<]+?)\s*-\s*", team_html, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return fallback


def search_club(club_name: str) -> dict[str, str]:
    search_url = f"{BASE_URL}/search.php?inputString={quote_plus(club_name)}"
    search_html, final_search_url = fetch_page(search_url)
    team_url = final_search_url if is_team_page(final_search_url) else find_team_page(search_html, club_name)

    if not team_url:
        raise ValueError("No club was found on zerozero.pt.")

    team_html, _ = fetch_page(team_url)
    kit_image_url = find_kit_image(team_html)

    if not kit_image_url:
        raise ValueError("The kit image was not found on the zerozero.pt team page.")

    return {
        "club_name": find_team_name(team_html, club_name),
        "team_url": team_url,
        "kit_image_url": kit_image_url,
    }


def render_page(club_query: str = "", result: dict[str, str] | None = None, error: str = "") -> str:
    safe_query = escape(club_query)
    result_block = ""

    if error:
        result_block = f"""
        <div class="message error">{escape(error)}</div>
        """
    elif result:
        result_block = f"""
        <section class="card">
          <p class="eyebrow">Kit found on zerozero.pt</p>
          <h2>{escape(result["club_name"])}</h2>
          <a class="source" href="{escape(result["team_url"])}" target="_blank" rel="noreferrer">
            Open team page on zerozero.pt
          </a>
          <div class="image-wrap">
            <img src="{escape(result["kit_image_url"])}" alt="Kit of {escape(result["club_name"])}" />
          </div>
        </section>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Football Club Kit Search</title>
    <style>
      :root {{
        --bg: #eef3ea;
        --panel: #fffdf8;
        --ink: #122020;
        --muted: #546060;
        --accent: #1f7a53;
        --accent-dark: #125239;
        --line: #d5dfd1;
        --error-bg: #fff1ef;
        --error-text: #9f2f1d;
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        min-height: 100vh;
        font-family: Georgia, "Times New Roman", serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(31, 122, 83, 0.18), transparent 28%),
          linear-gradient(145deg, #f7fbf5 0%, var(--bg) 55%, #dde9dd 100%);
      }}

      .shell {{
        width: min(920px, calc(100% - 32px));
        margin: 48px auto;
        background: rgba(255, 253, 248, 0.92);
        border: 1px solid rgba(213, 223, 209, 0.9);
        border-radius: 28px;
        padding: 28px;
        box-shadow: 0 20px 50px rgba(18, 32, 32, 0.08);
        backdrop-filter: blur(10px);
      }}

      h1 {{
        margin: 0;
        font-size: clamp(2.2rem, 4vw, 3.8rem);
        line-height: 0.98;
      }}

      .intro {{
        margin: 14px 0 28px;
        max-width: 640px;
        color: var(--muted);
        font-size: 1.05rem;
      }}

      form {{
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 12px;
        margin-bottom: 26px;
      }}

      input {{
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 999px;
        padding: 16px 20px;
        font-size: 1rem;
        background: white;
      }}

      button {{
        border: 0;
        border-radius: 999px;
        padding: 16px 22px;
        font-size: 1rem;
        font-weight: 700;
        color: white;
        background: linear-gradient(135deg, var(--accent), var(--accent-dark));
        cursor: pointer;
      }}

      .card,
      .message {{
        border-radius: 24px;
        border: 1px solid var(--line);
        background: var(--panel);
        padding: 22px;
      }}

      .message.error {{
        background: var(--error-bg);
        color: var(--error-text);
        border-color: #f3c7bf;
      }}

      .eyebrow {{
        margin: 0 0 10px;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-size: 0.72rem;
        color: var(--muted);
      }}

      h2 {{
        margin: 0;
        font-size: clamp(1.8rem, 3vw, 2.7rem);
      }}

      .source {{
        display: inline-block;
        margin-top: 10px;
        color: var(--accent-dark);
        text-decoration: none;
      }}

      .image-wrap {{
        margin-top: 20px;
        padding: 32px;
        border-radius: 20px;
        background:
          linear-gradient(180deg, rgba(31, 122, 83, 0.08), rgba(31, 122, 83, 0.02)),
          white;
        display: grid;
        place-items: center;
        min-height: 560px;
      }}

      img {{
        width: auto;
        max-width: min(100%, 520px);
        max-height: 680px;
        object-fit: contain;
        display: block;
      }}

      .footnote {{
        margin-top: 18px;
        color: var(--muted);
        font-size: 0.92rem;
      }}

      @media (max-width: 720px) {{
        .shell {{
          margin: 20px auto;
          padding: 20px;
          border-radius: 20px;
        }}

        form {{
          grid-template-columns: 1fr;
        }}

        button {{
          width: 100%;
        }}

        .image-wrap {{
          min-height: 420px;
          padding: 20px;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <h1>Search a football club and see its kit</h1>
      <p class="intro">
        Type a club name, and this Python site searches zerozero.pt, opens the first matching team page,
        and shows the equipment image used there.
      </p>

      <form method="GET" action="/">
        <input
          type="text"
          name="club"
          placeholder="Example: Benfica, Porto, Sporting"
          value="{safe_query}"
          required
        />
        <button type="submit">Search</button>
      </form>

      {result_block}

      <p class="footnote">
        Source: zerozero.pt. Results depend on the first club match returned by zerozero search.
      </p>
    </main>
    <script>
      const kitImage = document.querySelector(".image-wrap img");

      if (kitImage) {{
        const sizeImage = () => {{
          const containerWidth = Math.min(window.innerWidth - 120, 520);
          const naturalWidth = kitImage.naturalWidth || 0;
          const naturalHeight = kitImage.naturalHeight || 0;

          if (!naturalWidth || !naturalHeight) {{
            return;
          }}

          const width = Math.min(naturalWidth, containerWidth);
          const height = Math.min(naturalHeight, 680);

          kitImage.style.width = `${{width}}px`;
          kitImage.style.maxWidth = "100%";
          kitImage.style.height = "auto";
          kitImage.style.maxHeight = `${{height}}px`;
        }};

        if (kitImage.complete) {{
          sizeImage();
        }} else {{
          kitImage.addEventListener("load", sizeImage, {{ once: true }});
        }}

        window.addEventListener("resize", sizeImage);
      }}
    </script>
  </body>
</html>
"""


class ClubKitHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        if parsed_url.path != "/":
            self.send_error(404, "Page not found")
            return

        params = parse_qs(parsed_url.query)
        club_name = params.get("club", [""])[0].strip()
        result = None
        error = ""

        if club_name:
            try:
                result = search_club(club_name)
            except Exception as exc:  # pragma: no cover - basic fallback for runtime errors
                error = str(exc)

        page = render_page(club_query=club_name, result=result, error=error).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8000), ClubKitHandler)
    print("Server running at http://127.0.0.1:8000")
    server.serve_forever()
