from flask import Flask, request, jsonify, render_template
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import requests
import os

# Initialize Flask app
app = Flask(__name__, template_folder='../templates')

# Load your index and data
with open('embeddings/chunks.pkl', 'rb') as f:
    chunks = pickle.load(f)
with open('embeddings/sources.pkl', 'rb') as f:
    sources = pickle.load(f)

model = SentenceTransformer('all-MiniLM-L6-v2')
try:
    index = faiss.read_index('embeddings/faiss_index.index')
    index_loaded = True
except Exception:
    index_loaded = False
    dim = len(model.encode([""])[0])
    index = faiss.IndexFlatL2(dim)

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# Chat endpoint
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_question = data.get('question')

    # Convert question to embedding
    question_embedding = model.encode([user_question])
    question_embedding = np.array(question_embedding).astype('float32')

    # Find most similar document chunk
    k = 3
    retrieved_chunks = []
    if getattr(index, 'ntotal', 0) > 0 and len(chunks) > 0:
        distances, indices = index.search(question_embedding, k)
        retrieved_chunks = [chunks[i] for i in indices[0] if i != -1]

    # Construct the prompt
    context = "\n".join(retrieved_chunks)
    prompt = f"""Answer the following question based on the provided legal context:\n\nContext:\n{context}\n\nQuestion: {user_question}\nAnswer:"""

    # Guard: ensure API key exists
    if not TOGETHER_API_KEY:
        return jsonify({"error": "Missing Together API key (set TOGETHER_API_KEY env)"}), 500

    # Call Together API
    response = requests.post(
        "https://api.together.xyz/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.7
        }
    )

    if response.status_code == 200:
        ai_answer = response.json()["choices"][0]["message"]["content"]
        return jsonify({"answer": ai_answer.strip()})
    else:
        return jsonify({"error": "API call failed", "details": response.text}), 500

@app.route('/', methods=['GET'])
def home():
    return render_template('chat.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json() or {}
    user_question = data.get('query') or ''
    if not user_question.strip():
        return jsonify({"error": "Missing 'query'"}), 400

    question_embedding = model.encode([user_question])
    question_embedding = np.array(question_embedding).astype('float32')

    k = 3
    retrieved_chunks = []
    retrieved_indices = []
    if getattr(index, 'ntotal', 0) > 0 and len(chunks) > 0:
        distances, indices = index.search(question_embedding, k)
        retrieved_indices = [i for i in indices[0] if i != -1]
        retrieved_chunks = [chunks[i] for i in retrieved_indices]

    # Build citations list from sources corresponding to retrieved indices
    retrieved_sources = []
    for i in retrieved_indices:
        if 0 <= i < len(sources):
            src = sources[i]
            if src and src not in retrieved_sources:
                retrieved_sources.append(src)

    context = "\n".join(retrieved_chunks)
    prompt = f"""
You are Nyāya (ನ್ಯಾಯ), a Karnataka-focused legal assistant.
Use facts from Context when available; otherwise give general Karnataka guidance. Do not invent section numbers or cases. Cite only filenames in Sources if referenced.

OUTPUT FORMAT (plain text, no headings before the first paragraph):
- Start directly with a short, friendly simple explanation using a relatable analogy. Do NOT include “User Query:” or “Simple Explanation:” headings.
- Then add a newline and the label “⚖️ Legal Explanation:” followed by applicable Karnataka legal principles. Mention act/rule names only if in Context or widely known; avoid fabricating section numbers.
- Then add “🧾 Example Reference Case:” summarizing any retrieved case; if none, say “No specific case retrieved.”
- Then add “💡 Recommendations (Next Steps):” with 3–5 concrete, numbered steps.
- Finish with “Disclaimer: This is general information, not a substitute for legal advice.”

Context:
{context if context else "[No specific sources retrieved]"}

Sources:
{chr(10).join(retrieved_sources) if retrieved_sources else "[none]"}
"""

    # Guard: ensure API key exists
    if not TOGETHER_API_KEY:
        return jsonify({"error": "Missing Together API key (set TOGETHER_API_KEY env)"}), 500

    response = requests.post(
        "https://api.together.xyz/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
            "temperature": 0.3
        }
    )

    if response.status_code == 200:
        ai_answer = response.json()["choices"][0]["message"]["content"]
        return jsonify({"response": ai_answer.strip(), "citations": retrieved_sources})
    else:
        return jsonify({"error": "API call failed", "details": response.text}), 500


if __name__ == '__main__':
    app.run(debug=True)
