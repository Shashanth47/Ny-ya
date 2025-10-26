import pickle
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

CHUNK_SIZE = 300
model = SentenceTransformer('all-MiniLM-L6-v2')

with open("embeddings/text_data.pkl", "rb") as f:
    text_data = pickle.load(f)

chunks = []
sources = []

for filename, text in text_data.items():
    words = text.split()
    for i in range(0, len(words), CHUNK_SIZE):
        chunk = " ".join(words[i:i+CHUNK_SIZE])
        if any(word not in ENGLISH_STOP_WORDS for word in chunk.split()):
            chunks.append(chunk)
            sources.append(filename)

embeddings = model.encode(chunks)

with open("embeddings/chunks.pkl", "wb") as f:
    pickle.dump(chunks, f)

with open("embeddings/sources.pkl", "wb") as f:
    pickle.dump(sources, f)

with open("embeddings/embeddings.pkl", "wb") as f:
    pickle.dump(embeddings, f)

print("✅ Text chunked and embedded.")
