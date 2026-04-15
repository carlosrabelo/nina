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

# Single volume for all persistent data (tokens, sessions, credentials, state)
VOLUME ["/data"]

EXPOSE 8765

ENV DATA_DIR=/data/db
ENV TOKENS_DIR=/data/tokens
ENV SESSIONS_DIR=/data/sessions
ENV GOOGLE_CREDENTIALS_FILE=/data/credentials/credentials.json
ENV NINA_HTTP_HOST=0.0.0.0

CMD ["python", "-m", "nina", "daemon"]
