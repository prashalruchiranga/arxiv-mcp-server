import os
import re
import httpx
from mcp.server.fastmcp import FastMCP
import feedparser
import fitz

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
        
async def get_url_and_arxiv_id(title: str) -> tuple[str, str] | str:
    """Get URL of the article hosted on arXiv.org."""
    url = f"{ARXIV_API_BASE}/query"
    payload = {"search_query": f'ti:"{title}"'}
    data = await make_api_call(url, params=payload)
    if data is None:
        return "Unable to retrieve data from arXiv.org."
    feed = feedparser.parse(data)
    if not feed.entries:
        return "Unable to extract arXiv ID for the provided title. " \
        "This issue may stem from an incorrect or incomplete title, " \
        "or because the work has not been published on arXiv."
    entry = feed.entries[0]
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
    Retrieve the URL of an article hosted on arXiv.org based on its title. Use this tool only for retrieving \
        the URL. This tool searches for the article based on its title, and then fetches the corresponding URL from arXiv.org.

    Args:
        title: Article title.

    Returns:
        URL that can be used to retrieve the article.
    """
    formatted_title = format_text(title)
    result = await get_url_and_arxiv_id(formatted_title)
    if isinstance(result, str):
        return result
    article_url, _ = result
    return article_url

@mcp.tool()
async def download_article(title: str) -> str:
    """
    Download the article hosted on arXiv.org as a PDF file. This tool searches for the article based on its title, retrieves \
        the article's PDF, and saves it to a specified download location using the arXiv ID as the filename.

    Args:
        title: Article title.

    Returns:
        Success or error message.
    """
    formatted_title = format_text(title)
    result = await get_url_and_arxiv_id(formatted_title)
    if isinstance(result, str):
        return result
    article_url, arxiv_id = result
    pdf_doc = await get_pdf(article_url)
    if pdf_doc is None:
        return "Unable to retrieve the article from arXiv.org."
    file_path = os.path.join(DOWNLOAD_PATH, f"{arxiv_id}.pdf")
    try:
        with open(file_path, "wb") as file:
            file.write(pdf_doc)
        return f"Download successful. Find the PDF at {DOWNLOAD_PATH}."
    except Exception:
        return f"Unable to save the article to local directory."

@mcp.tool()
async def load_article_to_context(title: str) -> str:
    """
    Load the article hosted on arXiv.org into context. This tool searches for the article based on its title, retrieves \
        the article content, and loads text content into LLM context.

    Args:
        title: Article title.

    Returns:
        Article as a text string or error message.
    """
    formatted_title = format_text(title)
    result = await get_url_and_arxiv_id(formatted_title)
    if isinstance(result, str):
        return result
    article_url, _ = result
    pdf_doc = await get_pdf(article_url)
    if pdf_doc is None:
        return "Unable to retrieve the article from arXiv.org."
    pymupdf_doc = fitz.open(stream=pdf_doc, filetype="pdf")
    content = ""
    for page in pymupdf_doc:
        content += page.get_text()
    return content


if __name__ == "__main__":
    mcp.run(transport="stdio")
