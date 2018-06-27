# Build RPM
FROM shreyb/gracc-reporting:base_2.0 as builder

# Version
ARG version

# Setup:  Install RPM tools 
RUN yum install -y rpm-build rpmdevtools python-setuptools python-srpm-macros python-rpm-macros python2-rpm-macros epel-rpm-macros

# Set up directory structure
RUN mkdir -p ~/rpmbuild/{RPMS,SRPMS,BUILD,SOURCES,SPECS,tmp}

COPY osg-reports-$version.tar.gz /tmp/osg-reports-$version.tar.gz
COPY osg-reports.spec /tmp

RUN cp /tmp/osg-reports-$version.tar.gz ~/rpmbuild/SOURCES/
RUN cp /tmp/osg-reports.spec ~/rpmbuild/SPECS/

WORKDIR ~/rpmbuild/SOURCES
RUN rpmbuild -ba ~/rpmbuild/SPECS/osg-reports.spec

# Build osg-reports image
FROM shreyb/gracc-reporting:base_2.0 as osg-reports
ARG version
COPY --from=builder /root/rpmbuild/RPMS/noarch/osg-reports-$version.noarch.rpm /tmp

# Install gracc-reporting
RUN yum -y install /tmp/osg-reports-$version.noarch.rpm

