import os
import re
import httpx
from mcp.server.fastmcp import FastMCP
import feedparser

mcp = FastMCP("arxiv-server")

USER_AGENT = "arxiv-app/1.0"
ARXIV_API_BASE = "http://export.arxiv.org/api"
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH")

async def make_api_call(url: str, params: dict[str, str]) -> str | None:
    """Make a request to the arXiv API."""
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
    """Get PDF document as bytes from arXiv.org."""
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
        
async def get_url_and_arxiv_id(title: str) -> str:
    """Get URL of the article hosted on arXiv.org."""
    url = f"{ARXIV_API_BASE}/query"
    payload = {"search_query": f'ti:"{title}"'}
    data = await make_api_call(url, params=payload)
    feed = feedparser.parse(data)
    entry = feed.entries[0]
    if not feed.entries:
        return "Unable to fetch arXiv id. This could be due to incorrect title being provided."
    arxiv_id = entry.id.split("/abs/")[-1]
    direct_pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    return (direct_pdf_url, arxiv_id)

def format_text(text: str) -> str:
    """Clean a given text string by removing escape sequences and leading and trailing whitespaces."""
    # Remove common escape sequences
    text_without_escapes = re.sub(r'\\[ntr]', ' ', text)  
    # Collapse multiple spaces into one              
    text_single_spaced = re.sub(r'\s+', ' ', text_without_escapes)  
     # Trim leading and trailing spaces    
    cleaned_text = text_single_spaced.strip()                          
    return cleaned_text

@mcp.tool()
async def get_article_url(title: str) -> str:
    """
    Retrieve the URL of an article hosted on arXiv.org based on its title.
    
    This function formats the given title and then fetches the corresponding 
    article URL from arXiv.org using an internal helper function.

    Args:
        title: Article title.

    Returns:
        URL that can be used to retrieve the article.
    """
    formatted_title = format_text(title)
    article_url, _ = await get_url_and_arxiv_id(formatted_title)
    return article_url

@mcp.tool()
async def download_article(title: str) -> bytes | str:
    """
    Download the article hosted on arXiv.org as a PDF file.

    This tool searches for the article based on its title, retrieves the article's PDF, 
    and saves it to a specified download location using the arXiv ID as the filename.

    Args:
        title: Article title.

    Returns:
        Succesful message.
    """
    formatted_title = format_text(title)
    article_url, arxiv_id = await get_url_and_arxiv_id(formatted_title)
    pdf_document = await get_pdf(article_url)
    file_path = os.path.join(DOWNLOAD_PATH, f"{arxiv_id}.pdf")
    with open(file_path, "wb") as file:
        file.write(pdf_document)
    return "Success"


if __name__ == "__main__":
    mcp.run(transport="stdio")
