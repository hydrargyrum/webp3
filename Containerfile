FROM docker.io/python:3-slim AS wsgiref

LABEL org.opencontainers.image.title="WebP3"
LABEL org.opencontainers.image.description="web app to stream your audio files remotely"
LABEL org.opencontainers.image.source="https://gitlab.com/hydrargyrum/webp3"
LABEL org.opencontainers.image.licenses="WTFPL"
LABEL org.opencontainers.image.base.name="docker.io/python:3-slim"

RUN useradd --create-home webp3

COPY pyproject.toml /src/
COPY webp3/ /src/webp3/
COPY README.md /src/

USER webp3
WORKDIR /home/webp3

RUN python3 -m pip install --user --no-warn-script-location /src

CMD python3 -m webp3 --single-root media=/media

EXPOSE 8000
VOLUME /media

FROM wsgiref AS gunicorn

LABEL org.opencontainers.image.title="WebP3"
LABEL org.opencontainers.image.description="web app to stream your audio files remotely"
LABEL org.opencontainers.image.source="https://gitlab.com/hydrargyrum/webp3"
LABEL org.opencontainers.image.licenses="WTFPL"
LABEL org.opencontainers.image.base.name="docker.io/python:3-slim"

RUN python3 -m pip install --user --no-warn-script-location gunicorn

CMD WEBP3_SINGLE_ROOT=/media python3 -m gunicorn --bind=0.0.0.0:8000 --access-logfile=- --name=webp3 webp3.main_wsgi
