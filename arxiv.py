import time
start_time = time.time()
import os
import unittest
import feedparser
from datetime import datetime
import requests
import PyPDF2
import json

"""
This file, axiv.py
uses the ARXIV API to scrape journal articlesto save in a metadata file.
"""



"""
 -- ADVANCED QUERY
ti: for Title
au: for Author
abs: for Abstract
cat: for Categories
(e.g. http://export.arxiv.org/api/query?search_query=au:Einstein)

start: Starting point (pagination)
max_results: Number of results per request. Default is 10, but you can request up to 2,000 results per call.
(e.g. query?search_query=quantum+physics&start=0&max_results=50
)
"""

class ArxivFetcher:


	arxiv_categories = {
	    "Artificial Intelligence": "cs.AI",
	    "Computation and Language": "cs.CL",
	    "Computational Complexity": "cs.CC",
	    "Computational Geometry": "cs.CG",
	    "Computer Science and Game Theory": "cs.GT",
	    "Computer Vision and Pattern Recognition": "cs.CV",
	    "Computers and Society": "cs.CY",
	    "Cryptography and Security": "cs.CR",
	    "Data Structures and Algorithms": "cs.DS",
	    "Databases": "cs.DB",
	    "Digital Libraries": "cs.DL",
	    "Discrete Mathematics": "cs.DM",
	    "Distributed, Parallel, and Cluster Computing": "cs.DC",
	    "Emerging Technologies": "cs.ET",
	    "Formal Languages and Automata Theory": "cs.FL",
	    "General Literature": "cs.GL",
	    "Graphics": "cs.GR",
	    "Human-Computer Interaction": "cs.HC",
	    "Information Retrieval": "cs.IR",
	    "Information Theory": "cs.IT",
	    "Logic in Computer Science": "cs.LO",
	    "Machine Learning": "cs.LG",
	    "Mathematical Software": "cs.MS",
	    "Multiagent Systems": "cs.MA",
	    "Multimedia": "cs.MM",
	    "Networking and Internet Architecture": "cs.NI",
	    "Neural and Evolutionary Computing": "cs.NE",
	    "Numerical Analysis": "cs.NA",
	    "Operating Systems": "cs.OS",
	    "Performance": "cs.PF",
	    "Programming Languages": "cs.PL",
	    "Robotics": "cs.RO",
	    "Software Engineering": "cs.SE",
	    "Sound": "cs.SD",
	    "Symbolic Computation": "cs.SC",
	    "Systems and Control": "cs.SY"
	}

	def __init__(self):
		self.directory = "arxiv_articles"
		if not os.path.exists(self.directory):
			os.makedirs(self.directory)

	def _is_article_downloaded(self, arxiv_id):
		"""check if the article has been downloaded to the directory already"""
		filename = os.path.join(self.directory, arxiv_id + ".pdf")
		return os.path.exists(filename)

	def _load_downloaded_articles(self):
		"""Load the set of already downloaded arXiv IDs."""
		metadata_file = os.path.join(self.directory, "metadata.json")
		if os.path.exists(metadata_file):
			with open(metadata_file, 'r', encoding='utf-8') as file:
				data = json.load(file)
				return set(article['arxiv_id'] for article in data)
		return set()

	def _save_metadata(self, articles):
		"""Save article metadata to a single JSON file."""
		metadata_file = os.path.join(self.directory, "metadata.json")
		existing_data = []
		if os.path.exists(metadata_file):
			with open(metadata_file, 'r', encoding='utf-8') as file:
				existing_data = json.load(file)

		with open(metadata_file, 'w', encoding='utf-8') as file:
			combined_data = existing_data + articles
			json.dump(combined_data, file, ensure_ascii=False, indent=4)

	def fetch_arxiv_articles(self, category_key, num_articles=3):
		category = self.arxiv_categories.get(category_key, None)
		if not category:
			print(f"Invalid category: {category_key}")
			return

		downloaded_ids = self._load_downloaded_articles()
		new_articles = []

		base_url = "http://export.arxiv.org/api"
		query = f"/query?search_query=cat:{category}&sortBy=submittedDate&sortOrder=descending&start=0&max_results={num_articles}"
		url = base_url + query

		feed = feedparser.parse(url)

		for entry in feed.entries:
			arxiv_id = entry.id.split('/')[-1]
			if arxiv_id in downloaded_ids:
				print(f"Article: {entry.title} Already downloaded.")
				continue

			for link in entry.links:
				if link.type == 'application/pdf':
					pdf_link = link.href
					try:
						response = requests.get(pdf_link)
						response.raise_for_status()  
						filename = os.path.join(self.directory, arxiv_id + ".pdf")
						with open(filename, 'wb') as f:
							f.write(response.content)
						print(f"--Downloaded-- {entry.title} and saved as {filename}")
					except requests.RequestException as e:
						print(f"Failed to download {entry.title}. Error: {e}")

			date_string = entry.published
			date_object = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ')
			formatted_date = date_object.strftime('%B %d, %Y')

			new_articles.append({
				'arxiv_id': arxiv_id,
				'title': entry.title,
				'date_published': formatted_date,
				'summary':entry.summary
			})
		self._save_metadata(new_articles)

fetcher = ArxivFetcher()
# want to gather articles by multiple means (i.e. au: Daphne Koller, keywords: probabilistic)
fetcher.fetch_arxiv_articles(category_key="Artificial Intelligence", num_articles=3)


end_time = time.time()
elapsed_time = end_time - start_time
print(f"Total runtime: {elapsed_time:.2f} seconds")
