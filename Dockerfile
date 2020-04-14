FROM python:3-alpine
ARG version

RUN apk update \
	&& apk add build-base \
	&& apk add postgresql-dev

ADD . /gracc-osg-reports
WORKDIR /gracc-osg-reports

RUN python setup.py install

RUN mkdir /tmp/html_templates && mkdir /tmp/gracc-osg-reports-config

RUN cp /gracc-osg-reports/html_templates/* /tmp/html_templates


