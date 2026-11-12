FROM python:3.12-slim
WORKDIR /app/panel
# PyTorch en version CPU (mucho mas liviana que la version con GPU).
# Se instala antes que lo demas para que Docker reutilice esta capa pesada.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Permite importar texto_embedding.py, que esta en la raiz del proyecto (/app)
ENV PYTHONPATH=/app
