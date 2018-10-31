FROM opensciencegrid/gracc-reporting:2.0.1 
ARG version

RUN apk update \
	&& apk add build-base \
	&& apk add postgresql-dev

ADD gracc-osg-reports-$version.tar.gz /tmp/gracc-osg-reports-$version.tar.gz
WORKDIR /tmp/gracc-osg-reports-$version.tar.gz/gracc-osg-reports-$version/

RUN python setup.py install

RUN mkdir /tmp/html_templates && mkdir /tmp/gracc-osg-reports-config

RUN cp /tmp/gracc-osg-reports-$version.tar.gz/gracc-osg-reports-$version/html_templates/* /tmp/html_templates


