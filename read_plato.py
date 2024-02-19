import random
import json
import os
from nltk.tokenize import word_tokenize
from nltk.util import bigrams
from collections import Counter
import nltk
nltk.download('punkt')

class ArticleAnalyzer:
    def __init__(self, directory):
        self.directory = directory

    def load_articles(self):
        articles = []
        metadata_file = os.path.join(self.directory, "metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as file:
                articles = json.load(file)
        return articles

    def get_lexicon_and_bigrams(self, articles):
        all_words = []
        all_bigrams = []
        for article in articles:
            for content in article['content'].values():
                words = word_tokenize(content.lower())  # Tokenize and convert to lowercase
                all_words.extend(words)
                all_bigrams.extend(bigrams(words))

        lexicon = set(all_words)
        bigram_counts = Counter(all_bigrams)
        return lexicon, bigram_counts

    def display_results(self, lexicon, bigram_counts):
        print(f"Lexicon Size: {len(lexicon)}")
        print("Sample Lexicon Words:", random.choices(list(lexicon), k=10))  # Displaying a sample
        print("\nMost Common Bigrams:")
        for bigram, count in bigram_counts.most_common(10):
            print(f"{bigram}: {count}")

    def run_analysis(self):
        articles = self.load_articles()
        lexicon, bigram_counts = self.get_lexicon_and_bigrams(articles)
        self.display_results(lexicon, bigram_counts)

if __name__ == "__main__":
    analyzer = ArticleAnalyzer("sep_articles")
    # bigrams
    analyzer.run_analysis()
