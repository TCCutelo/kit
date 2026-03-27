from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.request import Request, urlopen
import re


BASE_URL = "https://www.zerozero.pt"
TEMPLATE_PATH = Path(__file__).with_name("templates").joinpath("index.html")
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


def render_result_block(result: dict[str, str] | None = None, error: str = "") -> str:
    if error:
        return f"""
        <div class="message error">{escape(error)}</div>
        """

    if result:
        return f"""
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

    return ""


def render_page(club_query: str = "", result: dict[str, str] | None = None, error: str = "") -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("{{club_query}}", escape(club_query))
        .replace("{{result_block}}", render_result_block(result=result, error=error))
    )


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
