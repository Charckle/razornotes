FROM python:3.11.5

EXPOSE 8000

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

# Add Tini, that will take care of handling the main process
RUN apt update && apt install tini -y
ENTRYPOINT ["/sbin/tini", "--"]

COPY . /app

CMD ["gunicorn",  "-b", "0.0.0.0:8000", "run:app", "-c", "gunicorn_config.py"]
