# written by Grok 4

from urllib.parse import urljoin
import re
import time
import os
from bs4 import BeautifulSoup
import requests

# Base configuration
BASE_URL = "https://mises.org/library/books?page={}"
TOTAL_PAGES = 40  # From page=0 to page=39
OUTPUT_DIR_HTML = "../content/html/mises-institute"
OUTPUT_DIR_EPUB = "../content/epub/mises-institute"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Create output directories if they don't exist
if not os.path.exists(OUTPUT_DIR_HTML):
    os.makedirs(OUTPUT_DIR_HTML)
if not os.path.exists(OUTPUT_DIR_EPUB):
    os.makedirs(OUTPUT_DIR_EPUB)


def get_soup(url):
    """Fetch and parse HTML content from a URL."""
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def sanitize_filename(title, extension=".html"):
    """Sanitize book title to create a valid filename with extension."""
    base = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
    return base + extension


def download_book(html_url, title):
    """Download the HTML content of a book and save it."""
    try:
        soup = get_soup(html_url)
        if not soup:
            return False

        filename = os.path.join(
            OUTPUT_DIR_HTML, sanitize_filename(title, ".html"))
        with open(filename, "w", encoding="utf-8") as f:
            f.write(str(soup))
        print(f"Downloaded HTML: {title} to {filename}")
        return True
    except Exception as e:
        print(f"Error downloading HTML {title} from {html_url}: {e}")
        return False


def get_printable_html_url(book_url):
    """Get the printable HTML version URL from the book's online page."""
    soup = get_soup(book_url)
    if not soup:
        return None

    # Find the print button link
    print_button = soup.find("a", class_="mises-btn-blue")
    if not print_button or "href" not in print_button.attrs:
        return None

    # Verify the link contains the "Print" text within a span
    span = print_button.find("span", string="Print")
    if not span:
        return None

    return urljoin(book_url, print_button["href"])


def process_book_page(book_url):
    """Process a single book page to find and download its HTML version, fallback to EPUB if HTML not available."""
    soup = get_soup(book_url)
    if not soup:
        return

    # Get book title
    title_tag = soup.find("h1", class_="page-title")
    if not title_tag:
        print(f"No title found for {book_url}")
        return
    title = title_tag.text.strip()

    # Find the downloads section
    downloads_section = soup.find("ul", class_="border")
    if not downloads_section:
        print(f"No downloads section found for {title}")
        return

    # Check if HTML already downloaded
    html_filename = os.path.join(
        OUTPUT_DIR_HTML, sanitize_filename(title, ".html"))
    if os.path.exists(html_filename):
        print(f"HTML already downloaded for {title}")
        return

    # Find HTML and EPUB links
    online_book_url = None
    epub_url = None
    epub_filename_span = None
    for a in downloads_section.find_all("a", class_="text-misesBlueDark"):
        span = a.find("span", string=re.compile(
            r"View HTML Version|.*\.epub$"))
        if span:
            if span.string == "View HTML Version":
                online_book_url = urljoin(book_url, a["href"])
            elif span.string.endswith(".epub"):
                epub_url = a["href"]
                epub_filename_span = span.string

    # Try to download HTML if available
    html_downloaded = False
    if online_book_url and online_book_url.startswith("https://mises.org/online-book/"):
        printable_url = get_printable_html_url(online_book_url)
        if printable_url:
            if download_book(printable_url, title):
                html_downloaded = True
                time.sleep(1)

    # If HTML not downloaded, fallback to EPUB
    if not html_downloaded:
        if epub_url and epub_filename_span:
            epub_filename = os.path.join(OUTPUT_DIR_EPUB, epub_filename_span)
            if os.path.exists(epub_filename):
                print(f"EPUB already downloaded for {title}")
                return
            try:
                headers = {"User-Agent": USER_AGENT}
                response = requests.get(epub_url, headers=headers, timeout=10)
                response.raise_for_status()
                with open(epub_filename, "wb") as f:
                    f.write(response.content)
                print(f"Downloaded EPUB: {title} to {epub_filename}")
                time.sleep(1)
            except Exception as e:
                print(f"Error downloading EPUB {title} from {epub_url}: {e}")
        else:
            print(f"No EPUB version found for {title}")


def main():
    """Main function to crawl all book pages."""

    print("Starting manual downloads...")
    process_book_page(
        "https://mises.org/library/book/man-economy-and-state-power-and-market")
    print("Finished manual downloads...")

    for page in range(TOTAL_PAGES):
        print(f"Processing page {page}...")
        page_url = BASE_URL.format(page)
        soup = get_soup(page_url)
        if not soup:
            continue

        # Find all book links on the page
        book_links = soup.select("h3.list-card__title a")
        for link in book_links:
            if "href" in link.attrs:
                book_url = urljoin(page_url, link["href"])
                process_book_page(book_url)

        # Delay between pages
        time.sleep(2)


if __name__ == "__main__":
    main()
