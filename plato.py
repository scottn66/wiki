import time
start_time = time.time()
import requests
from bs4 import BeautifulSoup
import os
import json
from urllib.parse import urljoin
import re
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import logging



class WebScraper:
    def __init__(self, url):
        self.url = url

    def scrape(self):
        try:
            response = requests.get(self.url)
            # Check if the request was successful
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                return soup
            else:
                print(f"Failed to retrieve data. Status code: {response.status_code}")
                return None
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP Error for {self.url}: {e}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request Exception for {self.url}: {e}")
        return None

    def get_initial_paragraph(self, soup):
        # Locate the preamble div by its ID
        preamble_div = soup.find('div', id='preamble')
        if preamble_div:
            # Extract the text of the first paragraph within this div
            first_paragraph = preamble_div.find('p')
            if first_paragraph:
                return first_paragraph.text.strip()
        return ""

    def get_headings(self, soup):
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        return [heading.text.strip() for heading in headings]

    def get_content_under_headings(self, soup):
        content = {}
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            content[heading.text.strip()] = heading.find_next_sibling().text.strip() if heading.find_next_sibling() else ''
        return content

    """Get the Related Entries"""
    def get_related_entries(self, soup):
        related_entries = {}
        related_entries_div = soup.find('div', id='related-entries')
        if related_entries_div:
            links = related_entries_div.find_all('a')
            for link in links:
                title = link.text.strip()
                href = link.get('href')
                if href !=None or title != 'Related Entries':
                        #print(title, link, f"added as {title, link[3:]}")
                    clean_href = re.sub(r'^[^A-Za-z]+', '', href)
                    related_entries[title] = clean_href
                # related_entries[title] = href
        return related_entries

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


class DBreader:
    def __init__(self):
        self.directory = "sep_articles"
        if not os.path.exists(self.directory):
            os.mkdir(self.directory)
        self.data = self.load_data()
        self.urls = self.get_article_urls() if self.data else set()
        self.titles = self.get_metadata_titles() if self.data else set()

    def load_data(self):
        metadata_file = os.path.join(self.directory, "metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        else:
            with open(metadata_file, 'w', encoding='utf-8') as file:
                json.dump([], file, ensure_ascii=False, indent=4)
            return []

    def get_metadata_titles(self):
        return set(article['title'] for article in self.data)
            
    def get_article_urls(self):
        return set(article['sep_url'] for article in self.data)

    def has_title(self, title):
        if title in self.titles:
            return True
        else:
            return False

    def has_link(self, link):
        if link in self.urls:
            return True
        else:
            return False

    def find_article(self, article):
        for page_content in self.data:
            print(page_content["title"])
            if page_content["title"] == article:
                print("matched")
                return page_content

        if article in self.urls or article in self.titles:
            return self.data[article]
        print(f"{article} not found.")

    def get_related_entries(self, reference):
        for ent in self.data:
            if reference == ent['title'] or reference == ent['sep_url']:
                rels = {}
                for title, link in ent['related_entries'].items():
                    if link !=None or title != 'Related Entries' or not link:
                        rels[title] = link
                return rels

    def search(self, keyword):
        keyword = keyword.lower()
        matching_articles = []

        for article in self.data:
            # Check if keyword is in title or initial paragraph
            if keyword in article['title'].lower() or keyword in article.get('initial_paragraph', '').lower():
                matching_articles.append(article)
                continue

            # Check if keyword is in the content under any heading
            for content in article.get('content', {}).values():
                if keyword in content.lower():
                    matching_articles.append(article)
                    break  # Break to avoid adding the same article multiple times

        return matching_articles



class SepFetcher:

    def __init__(self):
        self.directory = "sep_articles"
        if not os.path.exists(self.directory):
            os.mkdir(self.directory)

    def _load_downloaded_articles(self):
        metadata_file = os.path.join(self.directory, "metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return set(article['sep_url'] for article in data)
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


    def _is_valid_article_link(self, link):
        return link.name == 'li' and link.a and 'href' in link.a.attrs and link.a['href'].startswith('entries/')

    def fetch_sep_article_named(self, article_title):
        # pretend articles just has one item
        print(f"fetching {article_title}...")
        articles = []
        articles.append(article_title)
        new_articles = []
        base_url = "https://plato.stanford.edu/entries/"
        for each_url in articles:
            url = urljoin(base_url, each_url)
            if url in self._load_downloaded_articles():
                print(f"Article: \t{url} Already downloaded.")
                continue
            article = self.ind_fetch_helper(url)
            new_articles.append(article)
        self._save_metadata(new_articles)

    def ind_fetch_helper(self, url):
        article_entry = {}
        scraper = WebScraper(url)
        article_soup = scraper.scrape()
        article_entry['sep_url'] = url
        article_entry['title'] = article_soup.find('h1').text
        article_entry['headings'] = scraper.get_headings(article_soup)
        article_entry['initial_paragraph'] = scraper.get_initial_paragraph(article_soup)
        article_entry['content'] = scraper.get_content_under_headings(article_soup)
        article_entry['related_entries'] = scraper.get_related_entries(article_soup)
        return article_entry




    def fetch_sep_articles(self, num_articles=3):
        base_url = "https://plato.stanford.edu/contents.html"
        response = requests.get(base_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # all_links = soup.find_all('a')
        # for link in all_links[:50]:
        #     print(link['href'] if 'href' in link.attrs else "No Href")


        article_links = [link for link in soup.find_all('li') if self._is_valid_article_link(link)]
        print(f"---------\narticle links: \n\n\n\n{len(article_links)}")
        new_articles = []

        start_index = 2000
        end_index = 2600

        for link in article_links[start_index:start_index+num_articles]:
            url = urljoin("https://plato.stanford.edu", link.a['href'])
            # print(url)
            if url in self._load_downloaded_articles():
                print(f"Article: {link.text} Already downloaded.")
                continue

            scraper = WebScraper(url)
            article_soup = scraper.scrape()
            initial_paragraph = scraper.get_initial_paragraph(article_soup)
            title_element = article_soup.find('h1')
            
            # Check if title exists
            if title_element is None:
                print(f"Skipping {url} as it doesn't have a title.")
                continue

            title = title_element.text
            headings = scraper.get_headings(article_soup)
            content = scraper.get_content_under_headings(article_soup)

            related_entries = scraper.get_related_entries(article_soup)

            new_articles.append({
                'sep_url': url,
                'title': title,
                'headings': headings,
                'initial_paragraph': initial_paragraph,
                'content': content,
                'related_entries': related_entries
            })

        self._save_metadata(new_articles)

def create_adjacency_matrix(graph):
    nodes = list(graph.keys())
    node_index = {node: i for i, node in enumerate(nodes)}
    matrix_size = len(nodes)
    adjacency_matrix = np.zeros((matrix_size, matrix_size))

    for node, neighbors in graph.items():
        for neighbor in neighbors:
            if node in node_index and neighbor in node_index:
                adjacency_matrix[node_index[node]][node_index[neighbor]] = 1
            else:
                print(f"Missing node or neighbor: {node}, {neighbor}")

    return adjacency_matrix

if __name__ == "__main__":

    db = DBreader()
    fetcher = SepFetcher()
    search_result = db.search('aristotle')[0]
    print(search_result['title'])
    for rel_title, rel_link in search_result['related_entries'].items():
        print(f"Fetching related article: {rel_title}")
        fetcher.fetch_sep_article_named(rel_link)


    # graph G: each node is a sep_page, arrows point to related entry pages.
    # G = {}
    #
    # for title in db.titles:
    #     rels = db.get_related_entries(title)
    #     G[title] = [rel for rel in rels.keys() if rel in db.titles]
    #     # for title, link in rels.items():
    #         # print('\n', title, link)
    #         # fetcher.fetch_sep_article_named(link)
    #
    # adj_m = create_adjacency_matrix(G)
    # print(adj_m)
    #
    # G_nx = nx.Graph()
    # for i in range(len(adj_m)):
    #     for j in range(len(adj_m)):
    #         if adj_m[i][j] == 1:
    #             G_nx.add_edge(i, j)
    #
    # # Choose a layout for your graph
    # layout = nx.spring_layout(G_nx)  # Other layouts: circular_layout, random_layout, shell_layout
    #
    # # Draw the graph
    # nx.draw_networkx(G_nx, layout)
    # nx.draw_networkx_nodes(G_nx, layout, node_color='blue', node_size=50)  # For more customization
    # nx.draw_networkx_edges(G_nx, layout, edge_color='gray')
    # nx.draw_networkx_labels(G_nx, layout)

    # Show the plot
    # plt.show()

    # To save the plot to a file
    # plt.savefig('graph_visualization.png')

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total runtime: {elapsed_time:.2f} seconds")