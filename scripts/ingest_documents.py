"""
Document Ingestion Script for ClassAudit AI RAG Chatbot.
Reads all markdown documents from docs/institutional/, chunks them,
embeds them using sentence-transformers, and stores in ChromaDB.

Run this script ONCE (and re-run after any document updates):
    python scripts/ingest_documents.py
"""

import os
import sys
import re
import chromadb
from sentence_transformers import SentenceTransformer
import django

# ── Ensure Django settings are loaded (needed for BASE_DIR) ──
# Add the project root to the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'facere.settings')
django.setup()

from django.conf import settings


# ── CONFIG ──
DOCS_DIR = os.path.join(settings.BASE_DIR, "docs", "institutional")
CHROMA_DIR = os.path.join(settings.BASE_DIR, "chroma_db")
COLLECTION_NAME = "institutional_docs"
CHUNK_SIZE = 600       # characters per chunk
CHUNK_OVERLAP = 100    # overlap between consecutive chunks
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Metadata mapping: filename → document metadata
DOC_METADATA = {
    "attendance_policy.md": {
        "title": "Attendance Policy",
        "doc_type": "policy",
        "doc_id": "POL-ATT-001",
    },
    "faculty_leave_policy.md": {
        "title": "Faculty Leave Policy",
        "doc_type": "policy",
        "doc_id": "POL-LVE-002",
    },
    "faculty_handbook.md": {
        "title": "Faculty Handbook",
        "doc_type": "handbook",
        "doc_id": "HBK-FAC-003",
    },
    "live_monitoring_sop.md": {
        "title": "Live Monitoring Standard Operating Procedure",
        "doc_type": "sop",
        "doc_id": "SOP-MON-004",
    },
    "teacher_help_guide.md": {
        "title": "Teacher Help Guide",
        "doc_type": "guide",
        "doc_id": "HLP-TCH-005",
    },
    "principal_audit_manual.md": {
        "title": "Principal Audit Manual",
        "doc_type": "manual",
        "doc_id": "MAN-AUD-006",
    },
}


def clean_text(text: str) -> str:
    """Remove markdown syntax for cleaner embedding."""
    # Remove markdown headers, bold, italic, tables borders, code blocks
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text, flags=re.DOTALL)
    text = re.sub(r'\|[-| :]+\|', '', text)        # Table separators
    text = re.sub(r'\n{3,}', '\n\n', text)          # Collapse blank lines
    text = re.sub(r'---+', '', text)                # Horizontal rules
    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks on paragraph boundaries where possible."""
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
            # If a single paragraph is too large, split by sentence
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sub_chunk = ""
                for sentence in sentences:
                    if len(sub_chunk) + len(sentence) + 1 <= chunk_size:
                        sub_chunk = (sub_chunk + " " + sentence).strip()
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = sentence
                if sub_chunk:
                    current_chunk = sub_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return [c for c in chunks if len(c.strip()) > 30]  # Filter tiny fragments


def ingest_documents():
    print("=" * 60)
    print("ClassAudit AI — Document Ingestion Pipeline")
    print("=" * 60)

    # 1. Init embedding model
    print(f"\n[1/4] Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("      ✅ Model loaded.")

    # 2. Init ChromaDB
    print(f"\n[2/4] Connecting to ChromaDB at: {CHROMA_DIR}")
    os.makedirs(CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Delete existing collection for a clean re-ingest
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"      🗑️  Deleted existing collection '{COLLECTION_NAME}'.")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    print(f"      ✅ Created collection '{COLLECTION_NAME}'.")

    # 3. Process documents
    print(f"\n[3/4] Processing documents from: {DOCS_DIR}\n")
    total_chunks = 0

    if not os.path.exists(DOCS_DIR):
        print(f"      ❌ Documents directory not found: {DOCS_DIR}")
        return

    for filename in os.listdir(DOCS_DIR):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(DOCS_DIR, filename)
        meta = DOC_METADATA.get(filename, {
            "title": filename.replace(".md", "").replace("_", " ").title(),
            "doc_type": "general",
            "doc_id": "UNKNOWN",
        })

        print(f"  📄 Processing: {meta['title']} ({filename})")

        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()

        cleaned = clean_text(raw_text)
        chunks = chunk_text(cleaned)

        print(f"      → {len(chunks)} chunks created.")

        # Embed and insert
        for i, chunk in enumerate(chunks):
            embedding = model.encode(chunk).tolist()
            chunk_id = f"{meta['doc_id']}_chunk_{i:04d}"

            collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "title": meta["title"],
                    "doc_type": meta["doc_type"],
                    "doc_id": meta["doc_id"],
                    "chunk_index": i,
                    "source_file": filename,
                }]
            )
            total_chunks += 1

        print(f"      ✅ Ingested {len(chunks)} chunks for '{meta['title']}'.\n")

    # 4. Summary
    print(f"\n[4/4] Ingestion Complete!")
    print(f"      📦 Total chunks stored in ChromaDB: {total_chunks}")
    print(f"      📁 Vector store location: {CHROMA_DIR}")
    print(f"      🚀 Your RAG chatbot is now ready!\n")


if __name__ == "__main__":
    ingest_documents()
