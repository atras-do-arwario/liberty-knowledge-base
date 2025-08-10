# written by Grok 3 and ChatGPT-5

import re
import os
from bs4 import BeautifulSoup, NavigableString
import html2text


def escape_mathjax_in_text_nodes(soup):
    """
    Escape MathJax-reserved syntax in text nodes only.
    """
    mathjax_patterns = [
        (re.compile(r'(?<!\\)\$'), r'\\$'),          # $
        (re.compile(r'(?<!\\)\\\('), r'\\\\('),      # \(
        (re.compile(r'(?<!\\)\\\)'), r'\\\\)'),      # \)
        (re.compile(r'(?<!\\)\\\['), r'\\\\['),      # \[
        (re.compile(r'(?<!\\)\\\]'), r'\\\\]'),      # \]
        (re.compile(r'(?<!\\)\\begin\{'), r'\\\\begin{'),
        (re.compile(r'(?<!\\)\\end\{'), r'\\\\end{'),
    ]

    for text_node in soup.find_all(string=True):
        if isinstance(text_node, NavigableString):
            new_text = str(text_node)
            for pattern, replacement in mathjax_patterns:
                new_text = pattern.sub(replacement, new_text)
            text_node.replace_with(new_text)


def clean_markdown(md):
    """
    Apply general Markdown formatting best practices.
    """
    # Fix footnote spacing (only for inline refs)
    md = re.sub(r'(?<!^)\s+\[\^(\d+|p\d+)\](?!:)',
                r'[^\1]', md, flags=re.MULTILINE)
    md = re.sub(r'(\[\^(?:\d+|p\d+)\])(?!:)(?=\w)', r'\1 ', md)

    # Remove trailing spaces
    md = re.sub(r'[ \t]+$', '', md, flags=re.MULTILINE)

    # Collapse multiple blank lines
    md = re.sub(r'\n{3,}', '\n\n', md)

    # Ensure blank line before and after headings
    md = re.sub(r'(?<!\n)\n(#{1,6} )', r'\n\n\1', md)  # before
    md = re.sub(r'(#{1,6} .+?)(?=\n[^#\n])', r'\1\n', md)  # after

    return md.strip() + "\n"


def process_page_markers(md):
    """
    Transform [p. 59] markers into inline footnotes like §[^p59]: Page 59.
    """
    page_footnotes = {}
    counter = 0

    def replace_marker(match):
        nonlocal counter
        page_num = match.group(1)
        counter += 1
        footnote_id = f"p{page_num}"
        page_footnotes[footnote_id] = f"Page {page_num}"
        return f" §[^{footnote_id}]"

    # Replace markers with inline footnote references
    md = re.sub(r'\s*\[p\.\s*(\d+)\]', replace_marker, md)

    # Append definitions at the end of the file
    if page_footnotes:
        md += "\n\n" + "\n".join(f"[^{fid}]: {text}" for fid,
                                 text in page_footnotes.items())

    return md


def convert_html_to_markdown(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Escape MathJax only in text nodes
    escape_mathjax_in_text_nodes(soup)

    h = html2text.HTML2Text()
    h.body_width = 0
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False

    global_footnote_counter = 0
    footnote_id_to_global = {}

    def process_article(article, level=1):
        nonlocal global_footnote_counter, footnote_id_to_global
        markdown_parts = []

        h1 = article.find('h1', recursive=False)
        if h1:
            title = h1.get_text().strip()
            markdown_parts.append(f"{'#' * level} {title}")
            next_el = h1.find_next_sibling()
            if next_el and next_el.get_text(strip=True) == title:
                next_el.decompose()

        for child in article.children:
            if child.name == 'div':
                footnote_refs = child.find_all(
                    'a', class_='footnote__citation')
                section_footnote_defs = {}

                for ref in footnote_refs:
                    footnote_id = ref.get('href').lstrip('#')
                    if footnote_id not in footnote_id_to_global:
                        global_footnote_counter += 1
                        footnote_id_to_global[footnote_id] = global_footnote_counter
                    global_num = footnote_id_to_global[footnote_id]
                    ref.replace_with(f"[^{global_num}]")

                footnotes_list = child.find('ul', class_='footnotes')
                if footnotes_list:
                    for li in footnotes_list.find_all('li', class_='footnotes__item-wrapper'):
                        footnote_id = li.find(
                            'a', class_='footnotes__item-backlink').get('id')
                        footnote_text = li.find(
                            'span', class_='footnotes__item-text').get_text().strip()
                        if footnote_id not in footnote_id_to_global:
                            global_footnote_counter += 1
                            footnote_id_to_global[footnote_id] = global_footnote_counter
                        global_num = footnote_id_to_global[footnote_id]
                        section_footnote_defs[global_num] = footnote_text
                    footnotes_list.decompose()

                div_md = h.handle(str(child)).strip()
                if div_md:
                    markdown_parts.append(div_md)

                if section_footnote_defs:
                    markdown_parts.append(
                        '\n'.join(f"[^{num}]: {text}" for num, text in sorted(
                            section_footnote_defs.items()))
                    )

            elif child.name == 'article':
                sub_md = process_article(child, level + 1)
                if sub_md:
                    markdown_parts.append(sub_md)

        return '\n\n'.join(md.strip() for md in markdown_parts if md.strip())

    main_article = soup.find('article')
    if not main_article:
        return "# No content found"

    md_output = process_article(main_article)

    # Convert [p. 59] markers to inline footnotes
    md_output = process_page_markers(md_output)

    # Apply general cleanup
    return clean_markdown(md_output)


def process_html_files(input_dir="./mises_books", output_dir="./mises_books/md"):
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.endswith('.html'):
            input_path = os.path.join(input_dir, filename)
            output_filename = os.path.splitext(filename)[0] + '.md'
            output_path = os.path.join(output_dir, output_filename)

            with open(input_path, 'r', encoding='utf-8') as file:
                html_content = file.read()

            markdown_content = convert_html_to_markdown(html_content)

            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(markdown_content)

            print(f"Converted {filename} to {output_filename}")


if __name__ == "__main__":
    process_html_files()
