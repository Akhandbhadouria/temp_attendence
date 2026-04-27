import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from accounts.models import PrincipalDocument
from . import rag_engine


# ── Helper: resolve principal_id for any logged-in user ──
def _get_principal_id(request) -> int | None:
    """Returns the principal ID that owns this user's knowledge base."""
    user = request.user
    if hasattr(user, 'principal'):
        return user.principal.id
    if hasattr(user, 'teacher'):
        return user.teacher.principal.id
    return None


# ── Chat Page ──
@login_required
def chatbot_page(request):
    """Render the chatbot chat page."""
    user = request.user
    is_principal = hasattr(user, 'principal')
    is_teacher = hasattr(user, 'teacher')
    principal_id = _get_principal_id(request)

    doc_count = rag_engine.get_document_count(principal_id) if principal_id else 0

    # Get uploaded documents for sidebar (principal only)
    uploaded_docs = []
    if is_principal:
        uploaded_docs = PrincipalDocument.objects.filter(
            principal=user.principal, is_ingested=True
        )

    context = {
        'is_principal': is_principal,
        'is_teacher': is_teacher,
        'user_name': user.teacher.name if is_teacher else user.username,
        'doc_count': doc_count,
        'uploaded_docs': uploaded_docs,
    }
    return render(request, 'chatbot/chat.html', context)


# ── Chat API ──
@login_required
@require_http_methods(["POST"])
def chat_api(request):
    """POST /chatbot/api/ — accepts a query, returns RAG answer."""
    principal_id = _get_principal_id(request)
    if not principal_id:
        return JsonResponse({"error": "Could not identify your institution."}, status=400)

    try:
        body = json.loads(request.body)
        query = body.get("query", "").strip()

        if not query:
            return JsonResponse({"error": "No query provided."}, status=400)
        if len(query) > 1000:
            return JsonResponse({"error": "Query too long. Max 1000 characters."}, status=400)

        result = rag_engine.chat(query, principal_id)
        return JsonResponse({"answer": result["answer"], "sources": result["sources"]})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)


# ── Document Management (Principal only) ──
@login_required
def manage_documents(request):
    """Principal uploads and manages their knowledge base documents."""
    if not hasattr(request.user, 'principal'):
        messages.error(request, "Only principals can manage documents.")
        return redirect('home')

    principal = request.user.principal
    documents = PrincipalDocument.objects.filter(principal=principal)
    doc_count = rag_engine.get_document_count(principal.id)

    return render(request, 'chatbot/manage_documents.html', {
        'documents': documents,
        'doc_count': doc_count,
        'school_name': principal.school_name,
    })


@login_required
@require_http_methods(["POST"])
def upload_documents(request):
    """Handle multi-file upload and immediate ingestion."""
    if not hasattr(request.user, 'principal'):
        return JsonResponse({"error": "Only principals can upload documents."}, status=403)

    principal = request.user.principal
    files = request.FILES.getlist('documents')

    if not files:
        return JsonResponse({"error": "No files were uploaded."}, status=400)

    results = []
    for f in files:
        filename = f.name
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext not in ("pdf", "md", "txt"):
            results.append({
                "filename": filename,
                "status": "error",
                "message": "Unsupported file type. Only PDF, MD, and TXT are allowed."
            })
            continue

        title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

        # Save to DB and disk
        doc = PrincipalDocument.objects.create(
            principal=principal,
            title=title,
            file=f,
            file_type=ext,
            is_ingested=False,
        )

        # Ingest into ChromaDB
        try:
            doc_id = f"p{principal.id}_doc{doc.id}"
            chunk_count = rag_engine.ingest_file_for_principal(
                principal_id=principal.id,
                file_path=doc.file.path,
                title=title,
                doc_id=doc_id,
            )
            doc.is_ingested = True
            doc.save(update_fields=["is_ingested"])

            results.append({
                "filename": filename,
                "status": "success",
                "message": f"✅ '{title}' ingested — {chunk_count} chunks added.",
                "doc_id": doc.id,
            })
        except Exception as e:
            doc.delete()  # Clean up DB record if ingestion fails
            results.append({
                "filename": filename,
                "status": "error",
                "message": f"❌ Failed to process '{title}': {str(e)}"
            })

    success_count = sum(1 for r in results if r["status"] == "success")
    return JsonResponse({
        "results": results,
        "summary": f"{success_count}/{len(files)} files uploaded successfully.",
        "doc_count": rag_engine.get_document_count(principal.id),
    })


@login_required
@require_http_methods(["POST"])
def delete_document(request, doc_id):
    """Delete a document from DB and remove its chunks from ChromaDB."""
    if not hasattr(request.user, 'principal'):
        return JsonResponse({"error": "Only principals can delete documents."}, status=403)

    doc = get_object_or_404(PrincipalDocument, id=doc_id, principal=request.user.principal)
    filename = os.path.basename(doc.file.name)
    principal_id = request.user.principal.id
    title = doc.title

    # Delete file from disk
    try:
        if doc.file and os.path.exists(doc.file.path):
            os.remove(doc.file.path)
    except Exception:
        pass

    # Delete DB record (signal fires to remove ChromaDB chunks too)
    doc.delete()

    return JsonResponse({
        "status": "success",
        "message": f"'{title}' removed from knowledge base.",
        "doc_count": rag_engine.get_document_count(principal_id),
    })
