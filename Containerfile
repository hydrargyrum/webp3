FROM python:3-slim AS wsgiref

RUN useradd --create-home webp3

COPY pyproject.toml /src/
COPY webp3/ /src/webp3/
COPY README.md /src/

USER webp3
WORKDIR /home/webp3

RUN python3 -m pip install /src

CMD python3 -m webp3 --single-root media=/media

EXPOSE 8000
VOLUME /media

FROM wsgiref AS gunicorn

RUN python3 -m pip install gunicorn

CMD WEBP3_SINGLE_ROOT=/media python3 -m gunicorn --bind=0.0.0.0:8000 --access-logfile=- --name=webp3 webp3.main_wsgi
