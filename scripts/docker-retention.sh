#!/usr/bin/env bash
# Delete old Docker Hub tags, keeping only the most recent N.
#
# Usage:
#   DOCKERHUB_USER=you DOCKERHUB_TOKEN=pat_xxx ./scripts/docker-retention.sh [image] [keep]
#
# Defaults: image=nina, keep=3
# Create the token at: https://hub.docker.com -> Account Settings -> Security -> New Access Token
#   (needs Read & Write permissions)

set -euo pipefail

IMAGE="${1:-nina}"
KEEP="${2:-3}"
USER="${DOCKERHUB_USER:?set DOCKERHUB_USER}"
TOKEN="${DOCKERHUB_TOKEN:?set DOCKERHUB_TOKEN}"

REPO="${USER}/${IMAGE}"

echo "repo=${REPO}  keep=${KEEP}"

# Fetch all tags sorted by last_updated (newest first).
TAGS=$(curl -sf -H "Authorization: Bearer ${TOKEN}" \
    "https://hub.docker.com/v2/repositories/${REPO}/tags/?page_size=100&ordering=last_updated" \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
tags = [r['name'] for r in data.get('results', []) if r['name'] != 'latest']
for t in tags:
    print(t)
")

TOTAL=$(echo "${TAGS}" | wc -l)
echo "found ${TOTAL} tags (excluding latest)"

COUNT=0
SKIP=0
while IFS= read -r tag; do
    SKIP=$((SKIP + 1))
    if [ "${SKIP}" -le "${KEEP}" ]; then
        echo "  keep  ${tag}"
        continue
    fi
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" \
        -X DELETE \
        -H "Authorization: Bearer ${TOKEN}" \
        "https://hub.docker.com/v2/repositories/${REPO}/tags/${tag}/")
    if [ "${HTTP_CODE}" = "204" ] || [ "${HTTP_CODE}" = "200" ]; then
        echo "  deleted  ${tag}"
        COUNT=$((COUNT + 1))
    else
        echo "  FAILED  ${tag}  (HTTP ${HTTP_CODE})"
    fi
done <<< "${TAGS}"

echo "done — ${COUNT} tag(s) removed, ${KEEP} kept (+ latest)"
