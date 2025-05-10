FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DEBUG=False
ENV PORT=8000

EXPOSE 8000

VOLUME ["/app/data", "/app/logs"]

CMD ["python", "app.py"] 