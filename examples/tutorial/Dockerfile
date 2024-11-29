FROM python:3.10

WORKDIR /app

COPY . .

RUN make setup

CMD ["python", "-m", "dashboard", "run"]