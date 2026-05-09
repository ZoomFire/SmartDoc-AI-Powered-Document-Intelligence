from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

index = None
chunks = []

def create_embeddings(text):
    global index, chunks

    chunk_size = 400
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    embeddings = model.encode(chunks)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))


def search(query):
    global index, chunks

    if index is None:
        return ""

    query_vec = model.encode([query])
    D, I = index.search(np.array(query_vec), k=5)

    results = [chunks[i] for i in I[0]]
    return "\n".join(results)