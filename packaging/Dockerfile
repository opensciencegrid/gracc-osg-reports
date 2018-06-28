FROM shreyb/gracc-reporting:2.0 
ARG version

RUN apk update \
	&& apk add build-base \
	&& apk add postgresql-dev

ADD osg-reports-$version.tar.gz /tmp/osg-reports-$version.tar.gz
WORKDIR /tmp/osg-reports-$version.tar.gz/osg-reports-$version/

RUN python setup.py install

RUN mkdir /tmp/html_templates && mkdir /tmp/osg-reports-config

RUN cp /tmp/osg-reports-$version.tar.gz/osg-reports-$version/html_templates/* /tmp/html_templates


