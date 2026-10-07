import json
import os
import time
import uuid
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
from openai import OpenAI


app = FastAPI(title="Custom RAG OpenAI-Compatible API")

QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://qdrant.qdrant.svc.cluster.local:6333",
)
VLLM_BASE_URL = os.getenv(
    "VLLM_BASE_URL",
    "http://vllm.vllm.svc.cluster.local:8000/v1",
)
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
COLLECTION = os.getenv("RAG_COLLECTION", "docs")
BASE_MODEL = os.getenv("RAG_BASE_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
RAG_MODEL = os.getenv("RAG_MODEL", "rag-qwen")

qdrant = QdrantClient(
    url=QDRANT_URL
)

embedder = SentenceTransformer(
    EMBEDDING_MODEL
)

llm = OpenAI(
    base_url=VLLM_BASE_URL,
    api_key="dummy"
)


class IngestRequest(BaseModel):
    texts: list[str]


class QueryRequest(BaseModel):
    question: str


@app.on_event("startup")
def startup():
    dim = embedder.get_sentence_embedding_dimension()

    try:
        qdrant.get_collection(COLLECTION)
    except Exception:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=dim,
                distance=Distance.COSINE,
            ),
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest(req: IngestRequest):
    vectors = embedder.encode(req.texts).tolist()

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=v,
            payload={"text": t},
        )
        for t, v in zip(req.texts, vectors)
    ]

    qdrant.upsert(
        collection_name=COLLECTION,
        points=points,
    )

    return {"inserted": len(points)}


def retrieve_context(question: str, top_k: int = 3):
    vec = embedder.encode([question])[0].tolist()

    result = qdrant.query_points(
        collection_name=COLLECTION,
        query=vec,
        limit=top_k,
    )

    hits = result.points

    context = "\n\n".join(
        h.payload.get("text", "")
        for h in hits
        if h.payload and "text" in h.payload
    )

    sources = [
        h.payload
        for h in hits
        if h.payload
    ]

    return context, sources


def build_rag_prompt(question: str, context: str) -> str:
    return f"""
You are a retrieval-augmented generation assistant.

Answer the user's question using only the context below.

If the answer is present in the context, answer clearly and directly.
If the answer is not present in the context, say you do not know.

Context:
{context}

Question:
{question}
"""


def run_rag(question: str, max_tokens: int = 400) -> Dict[str, Any]:
    context, sources = retrieve_context(question)

    prompt = build_rag_prompt(
        question=question,
        context=context,
    )

    answer = llm.chat.completions.create(
        model=BASE_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=max_tokens,
    )

    return {
        "answer": answer.choices[0].message.content,
        "sources": sources,
    }


@app.post("/query")
def query(req: QueryRequest):
    result = run_rag(req.question)

    return {
        "answer": result["answer"],
        "sources": result["sources"],
    }


@app.get("/v1/models")
def openai_models():
    return {
        "object": "list",
        "data": [
            {
                "id": RAG_MODEL,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "custom-rag",
                "root": RAG_MODEL,
                "parent": None,
            }
        ],
    }


def extract_latest_user_message(messages: List[Dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content", "")

            if isinstance(content, str):
                return content

            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(item.get("text", ""))
                return "\n".join(parts)

    return ""


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    body = await request.json()

    messages = body.get("messages", [])
    stream = body.get("stream", False)
    max_tokens = body.get("max_tokens", 400)

    question = extract_latest_user_message(messages)

    if not question:
        question = "No user question was provided."

    rag_result = run_rag(
        question=question,
        max_tokens=max_tokens if max_tokens and max_tokens > 0 else 400,
    )

    answer_text = rag_result["answer"]
    completion_id = f"chatcmpl-rag-{uuid.uuid4().hex}"
    created = int(time.time())

    if stream:
        def event_stream():
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": RAG_MODEL,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": answer_text,
                        },
                        "finish_reason": None,
                    }
                ],
            }

            yield f"data: {json.dumps(chunk)}\n\n"

            final_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": RAG_MODEL,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }

            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
        )

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": RAG_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": answer_text,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "rag_sources": rag_result["sources"],
    }