import os
import requests
import json
import wikipediaapi
from SPARQLWrapper import SPARQLWrapper, JSON
from tqdm import tqdm

"""
Contains classes:

WikiPage - represents a wiki article page and structural metadata
WikiFetcher - uses requests to access wikipedia API to gather content

does not store anything in a metadata file.

"""

class WikiPage:
    def __init__(self, title, fetch=True):
        self.title = title
        self.links = []
        self.hyperlinks = {}    # title : Wikipage
        self.backlinks = []     # backlinks are titles
        self.numbacklinks = len(self.backlinks)
        self.content = ""
        self.summary = ""

        if fetch:
            self.fetch_content_and_links_from_wikipedia()

    def fetch_content_and_links_from_wikipedia(self, lang="en"):
        user_agent = "WikiPageBot/1.0 (https://github.com/scottn66/wiki; snelso43@lion.lmu.edu) wikipediaapi/0.1"
        wiki_wiki = wikipediaapi.Wikipedia(language=lang, user_agent=user_agent)
        page = wiki_wiki.page(self.title)

        if not page.exists():
            print(f"Page {self.title} does not exist.")
            return

        self.content = page.text
        self.summary = page.summary
        self.backlinks = list(page.backlinks.keys())
        self.numbacklinks = len(page.backlinks)

        for link in page.links:
            hyperlink_WikiPage = WikiPage(link, fetch=False)
            self.links.append(link)
            self.hyperlinks[link] = hyperlink_WikiPage

    def fetch_info_from_dbpedia(self):
        sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        sparql.setQuery(f"""
            SELECT ?comment WHERE {{
                ?page rdfs:label "{self.title}"@en .
                ?page rdfs:comment ?comment .
                FILTER(lang(?comment) = 'en')
            }}
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        for result in results["results"]["bindings"]:
            print(result["comment"]["value"])

    # Additional methods from previous code (like display_hyperlinks, add_backlink, etc) can be added here

class WikipediaFetcher:
    directory = "wikipedia_articles"
    user_agent = "WikiPageBot/1.0 (https://github.com/scottn66/wiki; snelso43@lion.lmu.edu) wikipediaapi/0.1"

    @staticmethod
    def fetch_wikipedia_articles(keyword, num_articles=3):
        base_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "format": "json",
            "utf8": 1,
            "srlimit": num_articles
        }

        headers = {
            "User-Agent": WikipediaFetcher.user_agent,
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"Wikipedia API request failed: {exc}")
            return []

        content_type = response.headers.get("Content-Type", "").lower()
        if "json" not in content_type:
            preview = response.text[:200].replace("\n", " ")
            print(f"Wikipedia API returned non-JSON response ({content_type}): {preview}")
            return []

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            preview = response.text[:200].replace("\n", " ")
            print(f"Wikipedia API JSON decode failed. Response preview: {preview}")
            return []

        search_results = data.get("query", {}).get("search", [])

        articles = []
        for article in search_results:
            title = article['title']
            wiki_page = WikiPage(title)
            articles.append(wiki_page)

        return articles

if __name__ == "__main__":
    # Example of how you might use it:
    fetcher = WikipediaFetcher()
    articles = fetcher.fetch_wikipedia_articles("philosophy", num_articles=3)
    for article in articles:
        print(article.title)
        print(article.summary)
        print("----")
