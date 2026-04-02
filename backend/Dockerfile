FROM python:3.11-slim

# System deps for WeasyPrint (cairo/pango) and matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev \
    libffi-dev shared-mime-info gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
