import os
import pickle
from pathlib import Path

import pdfplumber
import numpy as np
import faiss
import argparse
from sentence_transformers import SentenceTransformer

INPUT_DIR = Path("data/karnataka_acts")
EMB_DIR = Path("embeddings")
CHUNK_SIZE = 300
MODEL_NAME = "all-MiniLM-L6-v2"


def ensure_dirs():
    EMB_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_from_pdfs(input_dir: Path) -> dict:
    text_data = {}
    for pdf_path in sorted(input_dir.glob("*.pdf")):
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                text = []
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    if t:
                        text.append(t)
                text_joined = "\n".join(text)
                if text_joined.strip():
                    text_data[pdf_path.name] = text_joined
                    print(f"Extracted: {pdf_path.name} ({len(text_joined)} chars)")
                else:
                    print(f"No text in: {pdf_path.name}")
        except Exception as e:
            print(f"Failed to read {pdf_path.name}: {e}")
    return text_data


def write_text_artifacts(text_data: dict):
    # Save text_data.pkl
    with open(EMB_DIR / "text_data.pkl", "wb") as f:
        pickle.dump(text_data, f)
    # Save all_text.txt (concatenated)
    all_text = "\n\n".join(text_data.values())
    (EMB_DIR / "all_text.txt").write_text(all_text, encoding="utf-8")


def chunk_text_data(text_data: dict):
    chunks = []
    sources = []
    for filename, text in text_data.items():
        words = text.split()
        for i in range(0, len(words), CHUNK_SIZE):
            chunk = " ".join(words[i:i + CHUNK_SIZE])
            if chunk.strip():
                chunks.append(chunk)
                sources.append(filename)
    return chunks, sources


def embed_chunks(chunks: list[str]):
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(chunks)
    return embeddings


def build_faiss_index(embeddings):
    if len(embeddings) == 0:
        raise ValueError("No embeddings to index.")
    dimension = len(embeddings[0])
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype("float32"))
    faiss.write_index(index, str(EMB_DIR / "faiss_index.index"))


def parse_args():
    parser = argparse.ArgumentParser(description="Build text, chunks, embeddings, and FAISS index")
    parser.add_argument("--input-dir", default=str(INPUT_DIR), help="Directory containing PDFs")
    parser.add_argument("--output-dir", default=str(EMB_DIR), help="Directory to save embeddings artifacts")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help="Words per chunk")
    parser.add_argument("--model", default=MODEL_NAME, help="SentenceTransformer model name")
    return parser.parse_args()


def main():
    args = parse_args()

    # Override globals with CLI args
    global EMB_DIR, CHUNK_SIZE, MODEL_NAME
    input_dir = Path(args.input_dir)
    EMB_DIR = Path(args.output_dir)
    CHUNK_SIZE = args.chunk_size
    MODEL_NAME = args.model

    ensure_dirs()

    print(f"Scanning PDFs in: {input_dir}")
    text_data = extract_text_from_pdfs(input_dir)
    print(f"PDFs with text: {len(text_data)}")

    write_text_artifacts(text_data)
    print("Saved text_data.pkl and all_text.txt")

    chunks, sources = chunk_text_data(text_data)
    print(f"Chunks: {len(chunks)} | Sources: {len(sources)}")

    embeddings = embed_chunks(chunks)
    print(f"Embeddings: {len(embeddings)}")

    with open(EMB_DIR / "chunks.pkl", "wb") as f:
        pickle.dump(chunks, f)
    with open(EMB_DIR / "sources.pkl", "wb") as f:
        pickle.dump(sources, f)
    with open(EMB_DIR / "embeddings.pkl", "wb") as f:
        pickle.dump(embeddings, f)

    build_faiss_index(embeddings)
    print("FAISS index created.")

    print("Done building embeddings and index from PDFs.")


if __name__ == "__main__":
    main()