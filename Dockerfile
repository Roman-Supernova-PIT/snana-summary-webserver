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
# So the command for both, run from here, might be:
#
#  docker run -d --name snana-summary -p 8080:8080 \
#    --mount type=bind,source=$PWD,target=/code \
#    --mount type=bind,source=$PWD/data,target=/data \
#    snana-summary-webserver
#
# where <datadir> is where the .pkl files exported from
# lib/parse_snana.py live (perhaps $PWD/data).
#

FROM rknop/devuan-daedalus-rknop AS base

MAINTAINER Rob Knop <raknop@lbl.gov>

SHELL [ "/bin/bash", "-c" ]

RUN apt-get update \
    && DEBIAN_FRONTEND="noninteractive" apt-get -y upgrade \
    && DEBIAN_FRONTEND="noninteractive" TZ="US/Pacific" apt-get -y install -y \
         python3 python3-venv \
    && apt-get -y autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ======================================================================
# pip installs a full dev environment, which we don't want
#  in our final image.  (400 unnecessary MB.)

FROM base AS build

RUN apt-get update \
    && DEBIAN_FRONTEND="noninteractive" apt-get install -y python3-pip

RUN mkdir /venv
RUN python3 -mvenv /venv

RUN source /venv/bin/activate \
  && pip install \
       gunicorn flask pyyaml numpy pandas matplotlib astropy

RUN mkdir /tmp/build
RUN mkdir /code

COPY . /tmp/build
WORKDIR /tmp/build

RUN make INSTALLDIR=/code install

# ======================================================================

FROM base AS final

COPY --from=build /venv/ /venv/
ENV PATH=/venv/bin:$PATH

COPY --from=build /code/ /code/
WORKDIR /code

COPY data /data
RUN mkdir /snana_sim

CMD [ "gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "--timeout", "0", \
      "webservice:app" ]
