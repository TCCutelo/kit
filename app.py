from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from socket import timeout as SocketTimeout
from time import sleep
import re


BASE_URL = "https://www.zerozero.pt"
TEMPLATE_PATH = Path(__file__).with_name("templates").joinpath("index.html")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 25
MAX_RETRIES = 2


def fetch_page(url: str) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(MAX_RETRIES + 1):
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                return response.read().decode("utf-8", errors="ignore"), response.geturl()
        except HTTPError as exc:
            if exc.code in (502, 504):
                if attempt < MAX_RETRIES:
                    sleep(1 + attempt)
                    continue
                raise ValueError(
                    "zerozero.pt did not respond correctly. Please try again in a moment."
                ) from exc
            raise
        except (URLError, SocketTimeout) as exc:
            if attempt < MAX_RETRIES:
                sleep(1 + attempt)
                continue
            raise ValueError(
                "Could not reach zerozero.pt right now. Please try again in a moment."
            ) from exc


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


def render_kit_card(result: dict[str, str], label: str) -> str:
    club_name = escape(result["club_name"])
    return f"""
          <article class="kit-card">
            <p class="eyebrow">{escape(label)}</p>
            <h2>{club_name}</h2>
            <a class="source" href="{escape(result["team_url"])}" target="_blank" rel="noreferrer">
              Open team page on zerozero.pt
            </a>
            <div class="image-wrap">
              <img src="{escape(result["kit_image_url"])}" alt="Kit of {club_name}" />
            </div>
          </article>
    """


def render_kit_error_card(team_name: str, error: str, label: str) -> str:
    return f"""
          <article class="kit-card">
            <p class="eyebrow">{escape(label)}</p>
            <h2>{escape(team_name)}</h2>
            <div class="message error kit-error">{escape(error)}</div>
          </article>
    """


def render_result_block(results: list[dict[str, str]] | None = None) -> str:
    if results:
        labels = ["Team 1 kit", "Team 2 kit"]
        cards = []
        for index, result in enumerate(results):
            label = labels[index] if index < len(labels) else "Team kit"
            if result["status"] == "ok":
                cards.append(render_kit_card(result, label))
            else:
                cards.append(render_kit_error_card(result["query"], result["error"], label))

        return f"""
        <section class="card">
          <div class="comparison-head">
            <p class="eyebrow">Referee kit contrast check</p>
            <h2>Compare both teams</h2>
            <p>
              Use the two kits below to choose referee clothing that stands apart from both teams.
            </p>
          </div>
          <div class="comparison-grid">
            {"".join(cards)}
          </div>
        </section>
        """

    return ""


def render_clear_link(team_a_query: str = "", team_b_query: str = "") -> str:
    if not team_a_query and not team_b_query:
        return ""

    return '<a class="clear-link" href="/" aria-label="Clear search">Clear</a>'


def render_page(
    team_a_query: str = "",
    team_b_query: str = "",
    results: list[dict[str, str]] | None = None,
) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("{{team_a_query}}", escape(team_a_query))
        .replace("{{team_b_query}}", escape(team_b_query))
        .replace("{{clear_link}}", render_clear_link(team_a_query, team_b_query))
        .replace("{{result_block}}", render_result_block(results=results))
    )


class ClubKitHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        if parsed_url.path != "/":
            self.send_error(404, "Page not found")
            return

        params = parse_qs(parsed_url.query)
        team_a_name = params.get("team_a", params.get("club", [""]))[0].strip()
        team_b_name = params.get("team_b", [""])[0].strip()
        team_names = [name for name in (team_a_name, team_b_name) if name]
        results = None

        if team_names:
            results = []
            for team_name in team_names:
                try:
                    result = search_club(team_name)
                    result["status"] = "ok"
                    result["query"] = team_name
                    results.append(result)
                except Exception as exc:  # pragma: no cover - basic fallback for runtime errors
                    results.append(
                        {
                            "status": "error",
                            "query": team_name,
                            "error": str(exc),
                        }
                    )

        page = render_page(
            team_a_query=team_a_name,
            team_b_query=team_b_name,
            results=results,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8000), ClubKitHandler)
    print("Server running at http://127.0.0.1:8000")
    server.serve_forever()
