FROM python:3.12-slim

WORKDIR /app

# Install dependencies in a separate layer for better cache reuse.
# We copy only pyproject.toml first; pip resolves deps from it.
COPY pyproject.toml README.md ./
# Create minimal stubs so pip can parse the package without the full source.
RUN mkdir -p nina nina_play && \
    touch nina/__init__.py nina_play/__init__.py && \
    pip install --no-cache-dir -e . && \
    rm -rf nina nina_play

# Now copy the real source and reinstall (fast — deps already cached)
COPY nina/ ./nina/
COPY nina_play/ ./nina_play/
RUN pip install --no-cache-dir -e .

# Volumes for secrets — never baked into the image
VOLUME ["/app/tokens", "/app/credentials"]

EXPOSE 8765

ENV TOKENS_DIR=/app/tokens
ENV GOOGLE_CREDENTIALS_FILE=/app/credentials/credentials.json
ENV NINA_HTTP_HOST=0.0.0.0

CMD ["python", "-m", "nina", "daemon"]
