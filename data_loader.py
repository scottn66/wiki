import json

def load_articles(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        articles = json.load(file)
    return articles
