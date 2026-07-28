# Use Python 3.10 slim image as base
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY src/ src/
COPY templates/ templates/
COPY static/ static/

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

EXPOSE 3000

CMD ["python", "app.py"]
