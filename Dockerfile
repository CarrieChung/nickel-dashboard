FROM python:3.12-alpine

WORKDIR /app

COPY nickel/ ./nickel/

RUN pip install --no-cache-dir flask requests \
    && mkdir -p /app/data

ENV PYTHONPATH=/app \
    NICKEL_DB_PATH=/app/data/nickel.db

EXPOSE 8000

CMD ["python", "nickel/app.py"]