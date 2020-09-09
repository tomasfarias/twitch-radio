FROM python:3.8.5

WORKDIR /usr/src/twitch-radio

RUN pip install poetry
COPY . .

RUN poetry install --no-dev

CMD ["twitch-radio"]
