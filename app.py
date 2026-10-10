from socket import timeout as SocketTimeout
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import re

import streamlit as st


BASE_URL = "https://www.zerozero.pt"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 25
MAX_RETRIES = 2
KIT_IMAGE_WIDTH = 320


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

    raise ValueError("Could not fetch the page.")


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


@st.cache_data(show_spinner=False, ttl=900)
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


def render_result(team_name: str, label: str) -> None:
    if not team_name:
        st.info("Enter a team name to load this kit.")
        return

    try:
        with st.spinner(f"Searching {team_name}..."):
            result = search_club(team_name)
    except Exception as exc:
        st.error(str(exc))
        return

    st.caption(label)
    st.subheader(result["club_name"])
    st.image(result["kit_image_url"], width=KIT_IMAGE_WIDTH)
    st.link_button("Open team page", result["team_url"])


def main() -> None:
    st.set_page_config(
        page_title="Football Kit Contrast Check",
        page_icon="",
        layout="wide",
    )

    st.title("Football Kit Contrast Check")
    st.write(
        "Compare two football kits side by side before choosing referee clothing."
    )

    with st.form("kit-search"):
        team_a = st.text_input("Team 1", value="", placeholder="Benfica")
        team_b = st.text_input("Team 2", value="", placeholder="Belenenses")
        submitted = st.form_submit_button("Compare kits")

    if submitted:
        col_a, col_b = st.columns(2)
        with col_a:
            render_result(team_a.strip(), "Team 1 kit")
        with col_b:
            render_result(team_b.strip(), "Team 2 kit")


if __name__ == "__main__":
    main()
