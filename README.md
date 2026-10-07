# AI Platform on MicroK8s

A self-hosted GPU AI platform for MicroK8s, combining vLLM, Open WebUI, Qdrant, a FastAPI-based RAG gateway, and LGTM observability (Grafana, Prometheus, Loki, Tempo, and OpenTelemetry).

This repository is an adapted and documented implementation based on the upstream project by Deepak Deorari. The original MIT license and copyright notice are retained in [LICENSE](LICENSE). The deployment layout and application configuration have been adjusted for this repository, including environment-driven service endpoints and model settings.

## Quick Start

The supported deployment target is an Ubuntu 24.04 MicroK8s node with an NVIDIA GPU. Start with the [deployment runbook](runbooks/full-deployment-runbook.md), then use the [troubleshooting notes](docs/troubleshooting.md) while validating each service.

Before deploying, update the Hugging Face token and confirm the model fits the available GPU memory. The manifests use a local image for the RAG gateway, so import that image into MicroK8s before applying `manifests/rag-app`.

## Configuration

The RAG gateway accepts these environment variables, making the application portable across namespaces or service implementations:

| Variable | Default |
| --- | --- |
| `QDRANT_URL` | `http://qdrant.qdrant.svc.cluster.local:6333` |
| `VLLM_BASE_URL` | `http://vllm.vllm.svc.cluster.local:8000/v1` |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |
| `RAG_COLLECTION` | `docs` |
| `RAG_BASE_MODEL` | `Qwen/Qwen2.5-1.5B-Instruct` |
| `RAG_MODEL` | `rag-qwen` |

---

# Project Overview

This project demonstrates how to build a production-style AI platform on Kubernetes using a single GPU-enabled EC2 instance.

The platform includes:

- GPU-enabled Kubernetes cluster using MicroK8s
- NVIDIA GPU Operator integration
- vLLM model serving
- Qwen2.5-1.5B-Instruct model
- Open WebUI chat interface
- Qdrant vector database
- Custom Retrieval-Augmented Generation (RAG) application
- Prometheus metrics
- Grafana dashboards
- Loki log aggregation
- Tempo distributed tracing
- OpenTelemetry Collector

The deployment was executed on:

```text
AWS EC2 g5.xlarge
Ubuntu 24.04 LTS
NVIDIA A10G GPU (24 GB VRAM)
MicroK8s Kubernetes
```

---

# Architecture

```text
                    ┌─────────────────┐
                    │   Open WebUI    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │      vLLM       │
                    │ Qwen2.5-1.5B    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     RAG API     │
                    │    FastAPI      │
                    └────────┬────────┘
                             │
           ┌─────────────────┴─────────────────┐
           │                                   │
           ▼                                   ▼
┌────────────────────┐               ┌────────────────────┐
│       Qdrant       │               │ SentenceTransformer│
│    Vector Store    │               │     Embeddings     │
└────────────────────┘               └────────────────────┘


                Observability Stack

┌───────────────────────────────────────────────┐
│                    Grafana                    │
└───────────────┬─────────────┬─────────────────┘
                │             │
                ▼             ▼
        Prometheus          Loki
         Metrics            Logs
                │             │
                └──────┬──────┘
                       ▼
                     Tempo
                     Traces
                       │
                       ▼
            OpenTelemetry Collector
```

---

# Technology Stack

## Infrastructure

- AWS EC2 g5.xlarge
- Ubuntu 24.04 LTS
- NVIDIA A10G GPU

## Container Platform

- Kubernetes
- MicroK8s
- Containerd
- Helm

## AI Components

- vLLM
- Qwen2.5-1.5B-Instruct
- Open WebUI
- FastAPI
- Qdrant
- Sentence Transformers

## Observability

- Grafana
- Prometheus
- Loki
- Promtail
- Tempo
- OpenTelemetry Collector

---

# Repository Structure

```text
.
├── README.md
├── docs/
├── manifests/
│   ├── vllm/
│   ├── qdrant/
│   ├── openwebui/
│   ├── rag-app/
│   └── observability/
│
├── applications/
│   └── rag-app/
│       ├── Dockerfile
│       ├── main.py
│       └── requirements.txt
│
├── runbooks/
├── scripts/
├── screenshots/
└── architecture/
```

---

# Features

## GPU Inference

- GPU-enabled Kubernetes scheduling
- NVIDIA GPU Operator
- CUDA validation
- vLLM GPU inference

## LLM Serving

- OpenAI-compatible API
- vLLM deployment
- Qwen2.5 model serving
- Open WebUI integration

## Retrieval-Augmented Generation

### Document Ingestion

```http
POST /ingest
```

### Semantic Search

```http
POST /query
```

### Health Check

```http
GET /health
```

### Vector Database

- Qdrant
- Dense embeddings
- Similarity search

## Observability

### Metrics

- Node Metrics
- Kubernetes Metrics
- AI Service Metrics

### Logs

- Loki
- Promtail
- Grafana Explore

### Traces

- Tempo
- OpenTelemetry Collector
- Distributed Tracing

---

# Validation Performed

Successfully validated:

- NVIDIA Driver Installation
- GPU Scheduling
- CUDA Test Pod
- vLLM Startup
- OpenAI Compatible Endpoint
- Open WebUI Integration
- Qdrant Deployment
- RAG Ingestion
- RAG Querying
- Prometheus Metrics
- Loki Logs
- Tempo Traces
- OpenTelemetry Collector

---

# Sample RAG Query

Request:

```json
{
  "question": "What is Qdrant used for?"
}
```

Response:

```json
{
  "answer": "...",
  "sources": [
    {
      "text": "Qdrant is a vector database used for retrieval augmented generation."
    }
  ]
}
```

---

# Resource Utilization

Final deployment resource usage:

```text
CPU Usage      ~7%
Memory Usage   ~49%
```

Running successfully on:

```text
4 vCPU
16 GB RAM
1 x NVIDIA A10G GPU
```

---

# Challenges Solved

## vLLM Kubernetes Service Variable Conflict

Issue:

```text
VLLM_PORT appears to be a URI
```

Solution:

```yaml
enableServiceLinks: false
```

---

## Open WebUI Context Length Errors

Issue:

```text
Maximum context length exceeded
```

Solution:

```yaml
--max-model-len 8192
```

---

## Qdrant Client Compatibility

Issue:

```python
AttributeError:
QdrantClient has no attribute search
```

Solution:

```python
query_points()
```

---

## Kubernetes CPU Scheduling

Issue:

```text
Insufficient CPU
```

Solution:

Optimized CPU requests across:

- vLLM
- Open WebUI
- Qdrant
- Prometheus

---

# Screenshots

Add screenshots here:

```text
screenshots/
├── open-webui.png
├── grafana-dashboard.png
├── loki-logs.png
├── tempo-traces.png
├── qdrant-health.png
└── vllm-api-test.png
```

---

# Future Enhancements

- Multi-node Kubernetes deployment
- Larger LLM models
- K6 load testing
- GitOps deployment using ArgoCD
- CI/CD integration
- GPU autoscaling
- Multi-tenant model serving

---

# Skills Demonstrated

- Kubernetes
- MicroK8s
- NVIDIA GPU Operator
- AWS EC2
- vLLM
- Open WebUI
- Qdrant
- RAG
- FastAPI
- Docker
- Helm
- Prometheus
- Grafana
- Loki
- Tempo
- OpenTelemetry
- Observability
- Platform Engineering
- Site Reliability Engineering

---

# Maintainer

Anvita Kulkarni (`anvii0`)

Adapted, configured, and published for the AI Platform on MicroK8s repository.

## Upstream Author

Deepak Deorari

DevOps-III (Site Reliability Engineer III)

Built as a hands-on AI Platform Engineering, Kubernetes, GPU Infrastructure and Observability project.
