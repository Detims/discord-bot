FROM python:3.13-alpine

RUN apk add --no-cache git make build-base linux-headers

WORKDIR /discord-bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY assets ./assets

CMD ["python", "-u", "main.py"]