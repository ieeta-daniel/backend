FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install --upgrade -r requirements.txt

COPY . .

CMD ["python3", "handler.py"]