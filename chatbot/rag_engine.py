"""
RAG Engine for ClassAudit AI Chatbot.
- Per-principal ChromaDB collections (each school has its own knowledge base).
- Supports PDF, Markdown, and TXT files.
- Uses sentence-transformers for embeddings and Groq (LLaMA 3.3 70B) for generation.
"""

import os
import re
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
from django.conf import settings

# ── Singletons ──
_embedding_model = None
_chroma_client = None
_groq_client = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def _get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        chroma_dir = os.path.join(settings.BASE_DIR, "chroma_db")
        os.makedirs(chroma_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=chroma_dir)
    return _chroma_client


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = getattr(settings, "GROQ_API_KEY", None) or os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in settings or environment.")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_collection(principal_id: int) -> chromadb.Collection:
    """Get or create a ChromaDB collection for a specific principal."""
    client = _get_chroma_client()
    collection_name = f"principal_{principal_id}"
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


# ── Text Extraction ──

def _extract_text_from_file(file_path: str) -> str:
    """Extract raw text from PDF, Markdown, or TXT files."""
    ext = file_path.rsplit(".", 1)[-1].lower()

    if ext in ("md", "txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif ext == "pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except Exception as e:
            raise ValueError(f"Failed to read PDF '{os.path.basename(file_path)}': {e}")

    else:
        raise ValueError(f"Unsupported file type: .{ext}. Please upload PDF, MD, or TXT files.")


def _clean_text(text: str) -> str:
    """Strip markdown syntax for cleaner embedding."""
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text, flags=re.DOTALL)
    text = re.sub(r'\|[-| :]+\|', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'---+', '', text)
    return text.strip()


def _chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks on paragraph boundaries."""
    paragraphs = re.split(r'\n\n+', text)
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = (current_chunk + "\n\n" + para).strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sub = ""
                for s in sentences:
                    if len(sub) + len(s) + 1 <= chunk_size:
                        sub = (sub + " " + s).strip()
                    else:
                        if sub:
                            chunks.append(sub)
                        sub = s
                current_chunk = sub
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return [c for c in chunks if len(c.strip()) > 30]


# ── Ingestion ──

def ingest_file_for_principal(
    principal_id: int,
    file_path: str,
    title: str,
    doc_id: str,
) -> int:
    """
    Extract, chunk, embed, and store a single document into the principal's collection.
    Returns the number of chunks ingested.
    """
    embed_model = _get_embedding_model()
    collection = _get_collection(principal_id)
    filename = os.path.basename(file_path)

    # Remove old chunks for this file (clean re-ingest)
    try:
        collection.delete(where={"source_file": filename})
    except Exception:
        pass

    raw_text = _extract_text_from_file(file_path)
    cleaned = _clean_text(raw_text)
    chunks = _chunk_text(cleaned)

    if not chunks:
        raise ValueError(f"No text could be extracted from '{title}'.")

    for i, chunk in enumerate(chunks):
        embedding = embed_model.encode(chunk).tolist()
        chunk_id = f"{doc_id}_chunk_{i:04d}"
        collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{
                "title": title,
                "doc_id": doc_id,
                "source_file": filename,
                "principal_id": str(principal_id),
                "chunk_index": i,
            }]
        )

    return len(chunks)


def delete_file_from_principal(principal_id: int, filename: str) -> None:
    """Remove all chunks belonging to a specific file from a principal's collection."""
    try:
        collection = _get_collection(principal_id)
        collection.delete(where={"source_file": filename})
    except Exception:
        pass


# ── Retrieval ──

def retrieve_context(query: str, principal_id: int, n_results: int = 5) -> list[dict]:
    """Retrieve top-N relevant chunks from the principal's collection."""
    embed_model = _get_embedding_model()
    collection = _get_collection(principal_id)

    # Check if collection has any documents
    if collection.count() == 0:
        return []

    query_embedding = embed_model.encode(query).tolist()
    actual_n = min(n_results, collection.count())

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=actual_n,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "text": doc,
            "title": meta.get("title", "Unknown Document"),
            "doc_id": meta.get("doc_id", ""),
            "relevance_score": round(1 - dist, 3),
        })

    return chunks


# ── Generation ──

SYSTEM_PROMPT = """You are the ClassAudit AI Institutional Assistant — a professional, helpful, and accurate assistant for teachers and principals at an educational institution.

You answer questions exclusively based on the provided institutional documents: policies, guidelines, handbooks, and system guides.

Rules you MUST follow:
1. Answer ONLY from the provided Context. Do not invent policies or rules.
2. If the answer is not in the context, say: "I couldn't find this information in the institutional documents. Please contact your Head of Department or Principal."
3. Keep responses clear, structured, and professional.
4. When citing a rule, reference the document name (e.g., "According to the Attendance Policy...").
5. Use bullet points or numbered steps for procedural answers.
6. Be concise — do not repeat information unnecessarily."""


def generate_answer(query: str, context_chunks: list[dict]) -> str:
    """Generate an answer using Groq LLaMA 3.3 70B from retrieved context."""
    client = _get_groq_client()

    context_text = ""
    for i, chunk in enumerate(context_chunks, 1):
        context_text += f"\n--- Source {i}: {chunk['title']} ---\n{chunk['text']}\n"

    user_message = f"CONTEXT FROM INSTITUTIONAL DOCUMENTS:\n{context_text}\n\nUSER QUESTION:\n{query}"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error generating response: {str(e)}"


# ── Main Entry Point ──

def chat(query: str, principal_id: int) -> dict:
    """
    RAG chat — retrieves from principal's own knowledge base and generates answer.
    """
    if not query or not query.strip():
        return {"answer": "Please ask a question.", "sources": []}

    try:
        context_chunks = retrieve_context(query, principal_id, n_results=5)

        if not context_chunks:
            return {
                "answer": "📭 No documents have been uploaded to your institution's knowledge base yet.\n\nIf you are a **Principal**, please go to **Principal Dashboard → Manage Documents** to upload your school's policy files.\n\nIf you are a **Teacher**, please contact your Principal.",
                "sources": []
            }

        answer = generate_answer(query, context_chunks)

        # Deduplicate sources
        seen = set()
        sources = []
        for chunk in context_chunks:
            if chunk["doc_id"] not in seen:
                sources.append({
                    "title": chunk["title"],
                    "doc_id": chunk["doc_id"],
                    "relevance": chunk["relevance_score"]
                })
                seen.add(chunk["doc_id"])

        return {"answer": answer, "sources": sources}

    except Exception as e:
        return {"answer": f"⚠️ An error occurred: {str(e)}", "sources": []}


def get_document_count(principal_id: int) -> int:
    """Returns total number of chunks in a principal's collection."""
    try:
        collection = _get_collection(principal_id)
        return collection.count()
    except Exception:
        return 0
