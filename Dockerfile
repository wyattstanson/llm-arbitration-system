# Single image used by both the API and the Streamlit UI services (they differ
# only in their start command). Python 3.11 for broad, stable wheel availability.
FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal; everything else is pip wheels.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching). pyproject defines them.
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "pydantic>=2.7" "instructor>=1.5" "openai>=1.40" "anthropic>=0.34" \
    "langgraph>=0.2" "tenacity>=8.5" "python-dotenv>=1.0" \
    "fastapi>=0.111" "uvicorn>=0.30" "streamlit>=1.37"

COPY src ./src
COPY ui ./ui
COPY tests/fixtures ./tests/fixtures

# Store the SQLite audit trail on a mounted volume so it survives restarts.
ENV ARBITRATION_DB_PATH=/data/arbitrations.db
EXPOSE 8000 8501

# Default to the API; the UI service overrides this command in compose.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
