FROM python:3-slim
ARG version

ADD . /gracc-osg-reports
WORKDIR /gracc-osg-reports
RUN pip install -r requirements.txt
RUN python setup.py install

RUN mkdir /tmp/html_templates && mkdir /tmp/gracc-osg-reports-config

RUN cp /gracc-osg-reports/html_templates/* /tmp/html_templates


