# build with
#   docker build -t snana-summary-webserver .
#
# run with
#   docker run -d --name snana-summary -p 8080:8080 snana-summary-webserver
#
# To bind-mount the source directory for testing purposes, after -d:
#    --mount type=bind,source=$PWD,target=/code
#
# For this to work, you need to drop a symbolic link in static:
#   cd static
#   ln -s ../rkwebutil/rkwebutil.js rkwebutil.js
#
# To bind-mount an external data dir, also add:
#    --mount type=bind,source=<datadir>,target=/data \
#
# where <datadir> is where the .pkl files exported from
# lib/parse_snana.py live (perhaps $PWD/data).
#

FROM docker.io/alpine:3.19.1

RUN apk update \
    && apk add python3 py3-pip \
    && apk cache clean \
    && rm -rf /var/cache/apk/*

#    && libc6-compat

RUN rm /usr/lib/python3.11/EXTERNALLY-MANAGED

RUN pip install gunicorn flask pyyaml numpy pandas \
    && rm -rf /.cache/pip

RUN mkdir /code
RUN mkdir /code/static
RUN mkdir /code/templates
RUN mkdir /code/lib
WORKDIR /code
COPY webservice.py webservice.py
COPY static/*.js /code/static/
COPY rkwebutil/rkwebutil.js /code/static/rkwebutil.js
COPY templates/*.html /code/templates/
COPY lib/parse_snana.py /code/lib/

COPY data /data

CMD [ "gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "--timeout", "0", \
      "webservice:app" ]
