FROM python:3.10-slim

WORKDIR /app
COPY ./backend /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
