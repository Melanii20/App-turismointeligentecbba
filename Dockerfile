FROM python:3.12-slim
WORKDIR /app
# PyTorch en version CPU (mucho mas liviana que la version con GPU)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir psycopg2-binary pgvector sentence-transformers
