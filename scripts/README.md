# Scripts

## Mises Institute

### Download

To search and download all html books from the Mises Institute, run the script `mises-institute-html-books.py`.
It's configured to be slow and to download them into `./mises_books/`.

```bash
pip install requests beautifulsoup4
python mises-institute-html-books.py
```

### Markdown

To convert all downloaded books into markdown, run the script `mises-institute-html-to-markdown.py`.
It's configured to read from `./mises_books/`, convert and save them into `./mises_books/md/`

```bash
pip install beautifulsoup4 html2text
python mises-institute-html-to-markdown.py
```
