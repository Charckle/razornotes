FROM python:3.7.5

EXPOSE 8000

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT [ "gunicorn" ]

CMD [ "-b", "0.0.0.0:8000", "run:app" ]
