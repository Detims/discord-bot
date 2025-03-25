FROM python:3.11-alpine

RUN apk update && apk upgrade
RUN apk add --no-cache git make build-base linux-headers
WORKDIR /discord-bot
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "main.py"]