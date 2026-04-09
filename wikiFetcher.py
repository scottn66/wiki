import time
start_time = time.time()
import wikipediaapi
import requests
from bs4 import BeautifulSoup
import os
import json
from urllib.parse import urljoin

"""
Using the API, it fetches and stores wikipedia entries in a json database that houses the structural data.
Currently just searches for a given list of articles which are all stored from a previous runtime. 

"""


class WebScraper:
    def __init__(self, url, user_agent=None):
        self.url = url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent or "WikiPageBot/1.0 (https://github.com/scottn66/wiki; snelso43@lion.lmu.edu)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Referer": "https://en.wikipedia.org/",
        })

    def scrape(self, timeout=15):
        response = self.session.get(self.url, timeout=timeout)
        soup = BeautifulSoup(response.text, 'html.parser')
        return response, soup

    def validate_wikipedia_soup(self, response, soup):
        """
        Validate that the fetched page looks like a real Wikipedia article
        with parseable content.
        """
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"

        if soup.select_one("table.noarticletext") or soup.select_one("#noarticletext"):
            return False, "Missing article page"

        title_element = soup.select_one("h1#firstHeading") or soup.find("h1")
        if title_element is None:
            return False, "Missing article title heading"

        content_root = soup.select_one("div.mw-parser-output")
        if content_root is None:
            return False, "Missing article content container"

        paragraphs = [
            paragraph.get_text(strip=True)
            for paragraph in content_root.find_all("p")
        ]
        substantive_paragraphs = [text for text in paragraphs if len(text) > 40]
        if not substantive_paragraphs:
            return False, "No substantive paragraph content"

        categories_element = soup.select_one("#mw-normal-catlinks")
        if categories_element:
            categories_text = categories_element.get_text(" ", strip=True).lower()
            if "disambiguation" in categories_text:
                return False, "Disambiguation page"

        return True, "ok"

    def get_headings(self, soup):
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        return [heading.text.strip() for heading in headings]

    def get_content_under_headings(self, soup):
        content = {}
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            content[heading.text.strip()] = heading.find_next_sibling().text.strip() if heading.find_next_sibling() else ''
        return content

    def get_wikipedia_hyperlinks(self, soup):
        base_url = "https://en.wikipedia.org"
        hyperlinks = []

        # Get all links within the content of the Wikipedia page
        for link in soup.select('div.mw-parser-output a[href^="/wiki/"]'):
            if link['href']:
                full_url = urljoin(base_url, link['href'])
                hyperlinks.append(full_url)

        return hyperlinks


class Node:
    def __init__(self, name):
        self.name = name
        self.children = {}

    def print(self, indent=0):
        print('  ' * indent + self.name)
        for child in self.children.values():
            child.print(indent + 1)


def create_tree(lst):
    if not lst:  # check for empty list
        return None

    root = Node(lst[0])
    nodes = {0: root}

    for item in lst[1:]:
        name = item.split('. ', 1)[-1]
        level = item.count('.')
        if level == 0:
            continue
        node = Node(name)
        nodes[level] = node

        # Ensure the parent level exists before trying to access it
        if level - 1 in nodes:
            parent = nodes[level-1]
            parent.children[name] = node

    return root

class WikipediaFetcher:
    def __init__(self):
        self.user_agent = "WikiPageBot/1.0 (https://github.com/scottn66/wiki; snelso43@lion.lmu.edu) wikipediaapi/0.1"
        self.wiki_wiki = wikipediaapi.Wikipedia(language='en', user_agent=self.user_agent)
        self.directory = "wikipedia_articles"
        if not os.path.exists(self.directory):
            os.mkdir(self.directory)
        self.downloaded_articles = self._load_downloaded_articles()

    def _load_downloaded_articles(self):
        metadata_file = os.path.join(self.directory, "metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return set(article['wiki_url'] for article in data)
        return set()

    def _save_metadata(self, articles):
        metadata_file = os.path.join(self.directory, "metadata.json")
        existing_data = []
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as file:
                existing_data = json.load(file)

        with open(metadata_file, 'w', encoding='utf-8') as file:
            combined_data = existing_data + articles
            json.dump(combined_data, file, ensure_ascii=False, indent=4)

    def fetch_wikipedia_articles(self, titles_list):
        base_url = "https://en.wikipedia.org/wiki/"
        new_articles = []

        for title in titles_list:
            # Format the title to fit the URL format (replace spaces with underscores)
            formatted_title = title.replace(" ", "_")
            url = base_url + formatted_title
            
            if url in self.downloaded_articles:
                print(f"Article: {title} Already downloaded.")
                continue

            scraper = WebScraper(url, user_agent=self.user_agent)
            try:
                response, article_soup = scraper.scrape()
            except requests.RequestException as exc:
                print(f"Skipping {url}; request failed: {exc}")
                continue

            is_valid, reason = scraper.validate_wikipedia_soup(response, article_soup)
            if not is_valid:
                print(f"Skipping {url}; validation failed: {reason}")
                continue

            title_element = article_soup.select_one("h1#firstHeading") or article_soup.find('h1')
            
            # Check if title exists
            if title_element is None:
                print(f"Skipping {url} as it doesn't have a title.")
                continue

            wikipage = self.wiki_wiki.page(title)

            title = title_element.text
            headings = scraper.get_headings(article_soup)
            content = scraper.get_content_under_headings(article_soup)
            hyperlinks = scraper.get_wikipedia_hyperlinks(article_soup)

            new_articles.append({
                'wiki_url': url,
                'title': title,
                'headings': headings,
                'content': content,
                'hyperlinks': hyperlinks,
                # 'backlinks':wikipage.getBacklinks(),
                'summary': wikipage.summary
            })

        self._save_metadata(new_articles)

        # Optional: If you want to print the tree structure for each article
        for article in new_articles:
            print(f"Headings for article: {article['title']}")
            tree = create_tree(article['headings'])
            tree.print()

if __name__ == "__main__":
    titles = ["Python (programming language)", "Web scraping", "Data science"]
    fetcher = WikipediaFetcher()
    fetcher.fetch_wikipedia_articles(titles)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total runtime: {elapsed_time:.2f} seconds")
