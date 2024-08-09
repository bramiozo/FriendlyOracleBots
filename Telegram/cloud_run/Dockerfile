FROM python:3.9-slim

WORKDIR /app

RUN pip install poetry

ENV POETRY_VIRTUALENVS_CREATE=false
ENV PORT=80

COPY pyproject.toml .

RUN poetry install

COPY . .

COPY start.sh .
RUN chmod +x ./start.sh
CMD ["./start.sh"]
