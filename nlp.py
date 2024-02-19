import spacy

class NLPAnalyzer:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")  # Load the English model

    def analyze_text(self, text):
        doc = self.nlp(text)
        # Example analysis: Extracting entities
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        return entities
