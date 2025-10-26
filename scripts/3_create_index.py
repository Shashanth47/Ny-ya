import pickle
import faiss
import numpy as np

with open("embeddings/embeddings.pkl", "rb") as f:
    embeddings = pickle.load(f)

if len(embeddings) == 0:
    raise ValueError("❌ No embeddings found. Check chunking or API step.")

dimension = len(embeddings[0])
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings).astype("float32"))

faiss.write_index(index, "embeddings/faiss_index.index")
print("✅ FAISS index created.")
