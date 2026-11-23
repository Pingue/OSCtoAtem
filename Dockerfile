FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mapper.py .
COPY osctoatem.py .

RUN useradd --uid 1000 --create-home app
USER app
EXPOSE 1337/udp
ENTRYPOINT ["python", "osctoatem.py"]
