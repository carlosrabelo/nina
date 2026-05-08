FROM python:3.12-slim

WORKDIR /app

# Install dependencies in a separate layer for better cache reuse.
# We copy only pyproject.toml first; pip resolves deps from it.
COPY pyproject.toml README.md ./
# Create a minimal stub so pip can parse the package without the full source.
RUN mkdir -p nina && \
    touch nina/__init__.py && \
    pip install --no-cache-dir -e . && \
    rm -rf nina

# Now copy the real source and reinstall (fast — deps already cached)
COPY nina/ ./nina/
COPY scripts/ ./scripts/
RUN pip install --no-cache-dir -e .

# Single volume for all persistent data (tokens, sessions, credentials, state)
VOLUME ["/data"]

EXPOSE 8765

ENV DATA_DIR=/data/db
ENV TOKENS_DIR=/data/tokens
ENV SESSIONS_DIR=/data/sessions
ENV GOOGLE_CREDENTIALS_FILE=/data/credentials/credentials.json
ENV NINA_HTTP_HOST=0.0.0.0

CMD ["python", "-m", "nina", "daemon"]
