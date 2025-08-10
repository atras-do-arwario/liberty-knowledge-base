import requests
from bs4 import BeautifulSoup
import os
import time
import re
from urllib.parse import urljoin

# Base configuration
BASE_URL = "https://mises.org/library/books?page={}"
TOTAL_PAGES = 40  # From page=0 to page=39
OUTPUT_DIR = "mises_books"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


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


def sanitize_filename(title):
    """Sanitize book title to create a valid filename."""
    # Remove invalid characters and replace spaces
    return re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_') + ".html"


def download_book(html_url, title):
    """Download the HTML content of a book and save it."""
    try:
        soup = get_soup(html_url)
        if not soup:
            return False

        filename = os.path.join(OUTPUT_DIR, sanitize_filename(title))
        with open(filename, "w", encoding="utf-8") as f:
            f.write(str(soup))
        print(f"Downloaded: {title} to {filename}")
        return True
    except Exception as e:
        print(f"Error downloading {title} from {html_url}: {e}")
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
    """Process a single book page to find and download its HTML version."""
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

    # Check for HTML version link within the downloads section
    html_link = downloads_section.find("a", class_="text-misesBlueDark")
    if not html_link or "href" not in html_link.attrs:
        print(f"No HTML version link found for {title}")
        return

    # Verify the link contains the "View HTML Version" text within a span
    span = html_link.find("span", string="View HTML Version")
    if not span:
        print(f"No HTML version found for {title}")
        return

    online_book_url = urljoin(book_url, html_link["href"])
    if not online_book_url.startswith("https://mises.org/online-book/"):
        print(f"Invalid online book URL for {title}: {online_book_url}")
        return

    # Get the printable HTML URL
    printable_url = get_printable_html_url(online_book_url)
    if not printable_url:
        print(f"No printable HTML version found for {title}")
        return

    # Download the book
    download_book(printable_url, title)
    # Respectful delay
    time.sleep(1)


def main():
    """Main function to crawl all book pages."""
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
