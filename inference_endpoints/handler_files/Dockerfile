FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY ../requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY handler.py handler.py
COPY main.py main.py

EXPOSE 8000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "8", "--reload"]