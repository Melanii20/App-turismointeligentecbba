FROM python:3.12-slim
WORKDIR /app/asistente
# PyTorch en version CPU (mucho mas liviana que la version con GPU).
# Esta capa es igual a la del panel, asi que Docker la reutiliza y no la descarga de nuevo.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Permite importar texto_embedding.py, que esta en la raiz del proyecto (/app)
ENV PYTHONPATH=/app
