import os
import re
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from textblob import TextBlob  # pip install textblob

# ====== CONFIG ======
PINECONE_API_KEY = os.getenv(
    "PINECONE_API_KEY",
    "pcsk_3G8JGb_R6CJ2jquYjF1Rvx9HKtDGhZz24hqA5vAa6stE3LQ5AHPM3Ayr2NEKFJRH4YYgBe"
)
INDEX_NAME = "lotus-tc"

# ====== INIT EMBEDDING MODEL ======
model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions

# ====== INIT PINECONE ======
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# ====== CLEAN TEXT HELPER ======
def clean_text(text):
    """Remove extra spaces and line breaks from PDF text."""
    return re.sub(r'\s+', ' ', text).strip()

# ====== SPELL CORRECTOR ======
def correct_spelling(text):
    """Correct simple typos in the query."""
    return str(TextBlob(text).correct())

# ====== SEARCH FUNCTION ======
def search_terms(query, top_k=5):
    # Correct spelling before embedding
    corrected_query = correct_spelling(query)
    if corrected_query.lower() != query.lower():
        print(f"✅ Corrected query: {corrected_query}")

    # Embed the query
    query_embedding = model.encode(corrected_query).tolist()

    # Query Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )

    print(f"\n🔍 Query: {corrected_query}\n")
    for match in results['matches']:
        score = match['score']
        text = clean_text(match['metadata']['text'])
        print(f"Score: {score:.4f}\n{text}\n{'-'*60}")

# ====== EXAMPLE ======
if __name__ == "__main__":
    while True:
        user_query = input("\nEnter your question (or 'exit' to quit): ")
        if user_query.lower() in ["exit", "quit"]:
            break
        search_terms(user_query)
