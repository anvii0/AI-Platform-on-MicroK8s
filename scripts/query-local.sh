#!/usr/bin/env bash
set -euo pipefail

question="${*:-What is Qdrant used for?}"

curl --fail --silent \
  -H 'Content-Type: application/json' \
  --data "{\"question\": $(printf '%s' "$question" | python3 -c 'import json, sys; print(json.dumps(sys.stdin.read()))')}" \
  http://localhost:8080/query
printf '\n'