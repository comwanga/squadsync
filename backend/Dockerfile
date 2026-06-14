FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libffi-dev libssl-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Apply database migrations before serving so a fresh deployment starts with a
# fully-provisioned schema instead of a tableless database.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
