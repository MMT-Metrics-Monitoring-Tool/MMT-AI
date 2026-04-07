FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends --assume-yes \
        build-essential \
        curl \
    && rm --recursive --force /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv "$VIRTUAL_ENV" \
    && "$VIRTUAL_ENV/bin/python" -m pip install --upgrade pip==25.3 \
    && "$VIRTUAL_ENV/bin/python" -m pip install --requirement requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
