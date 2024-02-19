import time
start_time = time.time()
import json
import random
import matplotlib.pyplot as plt
import numpy as np

"""
ArticleDisplay - grabs a SEP article and spits out its ordered contents

## does not include contextual paragraph

WikipediaDisplay - grabs a Wiki article and spits out its ordered contents
"""

class ArticleDisplay:

    def __init__(self, metadata_file="sep_articles/metadata.json"):
        with open(metadata_file, 'r', encoding='utf-8') as file:
            self.articles = json.load(file)
        self.article = random.choice(self.articles)
        self.article_title = self.article.get('title', "No Title")

    def display_random_article(self):
        self.display_article(self.article)

    def display_article(self, article):
        title = article.get('title', "No Title")
        sep_url = article.get('sep_url', "No URL")
        content = article.get('content', {})
        
        separator = "-" * 50
        
        print(separator)
        print(f"Title: {title}")
        print(f"URL: {sep_url}")
        print(separator)
        
        for heading, text in content.items():
            print(f"\n{heading}\n")
            print(text)
            print(separator)



class WikipediaDisplay:
    def __init__(self, metadata_file="wikipedia_articles/metadata.json"):
        with open(metadata_file, 'r', encoding='utf-8') as file:
            self.articles = json.load(file)

    def display_random_article(self):
        article = random.choice(self.articles)
        self.display_article(article)

    def display_article(self, article):
        title = article.get('title', "No Title")
        wiki_url = article.get('wiki_url', "No URL")
        content = article.get('content', {})
        summary = article.get('summary', "No Summary")
        
        separator = "-" * 50
        
        print(separator)
        print(f"Title: {title}")
        print(f"URL: {wiki_url}")
        print(f"Summary: {summary}")
        print(separator)
        
        for heading, text in content.items():
            print(f"\n{heading}\n")
            print(text)
            print(separator)


if __name__ == "__main__":


    # Aesthetic border
    # print("\n\n\n" + "%" * 50)
    # print("%" + " " * 48 + "%")
    # print("%" + " " * 20 + "MEDIA" + " " * 23 + "%")
    # print("%" + " " * 48 + "%")
    # print("%" * 50 + "\n")
    display = ArticleDisplay()
    display.display_random_article()
    display_width = len(display.article_title) + 12
    title_width = len(display.article_title)
    total_padding = display_width - 2 - title_width
    padding_left = total_padding // 2
    padding_right = total_padding - padding_left
    print("\n\n\n" + "%" * display_width)
    print("%" + " " * (display_width - 2) + "%")
    print("%" + " " * padding_left + display.article_title + " " * padding_right + "%")
    print("%" + " " * (display_width - 2) + "%")
    print("%" * display_width + "\n")

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total runtime: {elapsed_time:.2f} seconds")
