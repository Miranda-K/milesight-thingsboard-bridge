FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY import_resources.py .

CMD ["python", "-u", "import_resources.py"]