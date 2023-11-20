FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install --upgrade -r requirements.txt

COPY . .

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8000", "--reload"]
