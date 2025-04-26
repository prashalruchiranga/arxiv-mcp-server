import httpx
from mcp.server.fastmcp import FastMCP
import feedparser
import re

mcp = FastMCP("arxiv-server")

USER_AGENT = "arxiv-app/1.0"
ARXIV_API_BASE = "http://export.arxiv.org/api"

async def make_api_call(url: str, params: dict[str, str]) -> str | None:
    """
    Make a request to the arXiv API.
    
    Args:
        url: URL string.
        params: Dictionary of query parameters.

    Returns:
        Response content decoded into Unicode text.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/atom+xml"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text
        except Exception:
            return None
        
async def get_pdf(url: str) -> bytes | None:
    """
    Get PDF document as bytes from arXiv.org.

    Args:
        url: URL string.

    Returns:
        PDF document in bytes.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.content
        except Exception:
            return None

def format_text(text: str) -> str:
    """
    Clean a given text string by removing escape sequences and leading and trailing whitespaces.

    Args:
        text: The input text to clean.

    Returns:
        Cleaned text.
    """
    text_without_escapes = re.sub(r'\\[ntr]', ' ', text)                # Remove common escape sequences
    text_single_spaced = re.sub(r'\s+', ' ', text_without_escapes)      # Collapse multiple spaces into one
    cleaned_text = text_single_spaced.strip()                           # Trim leading and trailing spaces
    return cleaned_text

@mcp.tool()
async def get_article_url(title: str) -> str:
    """
    Get URL of the article hosted on arXiv.org.

    Args:
        title: Article title.

    Returns:
        URL that can be used to retrieve the article.
    """
    title = format_text(title)
    url = f"{ARXIV_API_BASE}/query"
    payload = {"search_query": f'ti:"{title}"'}
    data = await make_api_call(url, params=payload)
    feed = feedparser.parse(data)
    entry = feed.entries[0]
    if not feed.entries:
        return "Unable to fetch arXiv id. This could be due to incorrect title."
    arxiv_id = entry.id.split("/abs")[-1]
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"

# @mcp.tool()
# async def download_article(title: str) -> bytes | str:
#     """
#     Get pdf document from url
#     """
#     url = await get_article_url(title)
#     pdf_document = await get_pdf(url)
#     return pdf_document


if __name__ == "__main__":
    mcp.run(transport="stdio")
