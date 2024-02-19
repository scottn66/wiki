from data_loader import load_articles
from nlp import NLPAnalyzer

def main():
    articles = load_articles('sep_articles/metadata.json')
    analyzer = NLPAnalyzer()

    for article in articles:
        # Assuming each article has a 'content' field
        content = article['content']
        analysis_results = analyzer.analyze_text(content)
        print(f"Analysis for {article['title']}: {analysis_results}")

if __name__ == "__main__":
    main()