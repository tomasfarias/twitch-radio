FROM python:3.8.5

WORKDIR /usr/src/twitch-radio

RUN pip install poetry
COPY . .

RUN poetry config virtualenvs.create false \
 && poetry install --no-dev --no-interaction

CMD ["twitch-radio"]
