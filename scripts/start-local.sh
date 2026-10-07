#!/usr/bin/env bash
set -euo pipefail

docker compose up -d --build
docker compose exec ollama ollama pull qwen2.5:1.5b

until curl --fail --silent http://localhost:8080/health >/dev/null; do
  printf 'Waiting for the RAG API...\n'
  sleep 2
done

curl --fail --silent \
  -H 'Content-Type: application/json' \
  --data-binary @data/sample-docs.json \
  http://localhost:8080/ingest
printf '\nLocal RAG stack is ready at http://localhost:8080\n'