%define name osg-reports
%define version 2.0
%define unmangled_version 2.0 
%define release 1
%define _rpmfilename %%{ARCH}/%%{NAME}-%%{VERSION}.%%{ARCH}.rpm

Summary: 	OSG email reports
Name: 		%{name}
Version: 	%{version}
Release: 	%{release}
Source0: 	%{name}-%{unmangled_version}.tar.gz
License: 	ASL 2.0
BuildRoot: 	%{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: 	%{_prefix}
BuildArch: 	noarch
Url: 		https://github.com/opensciencegrid/gracc-reporting

# BuildRequires:  systemd
BuildRequires:  python-setuptools
BuildRequires:  python-srpm-macros 
BuildRequires:  python-rpm-macros 
BuildRequires:  python2-rpm-macros 
BuildRequires:  epel-rpm-macros
Requires:       python-elasticsearch-dsl
Requires:	python-elasticsearch
Requires:       python-dateutil
Requires: 	python-psycopg2
Requires:	python-requests
Requires:   	python-toml
Requires:	gracc-reporting
Requires:	python-urllib3
Requires(pre): shadow-utils

%description
osg-reports is a set of reports that collect and present data from the Open Science Grid accounting system GRACC.

%prep
test ! -d %{buildroot} || {
	rm -rf %{buildroot}
}
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
%{py2_build}

%install
%{py2_install}

# Install config and html_template files in /etc/osg-reports
install -d -m 0755 %{buildroot}/%{_sysconfdir}/%{name}
install -m 0744 osg.toml %{buildroot}/%{_sysconfdir}/%{name}/
install -d -m 0755 %{buildroot}/%{_sysconfdir}/%{name}/html_templates/
install -m 0744 html_templates/* %{buildroot}/%{_sysconfdir}/%{name}/html_templates/

# Install doc files to /usr/share/docs/osg-reports
install -d -m 0755 %{buildroot}/%{_defaultdocdir}/%{name}/ 
install -m 0744 OSG_README.md %{buildroot}/%{_defaultdocdir}/%{name}/ 

# Empty dir
install -d -m 0644 %{buildroot}/var/log/%{name}

%files
# Permissions
%defattr(-, root, root)

# Python package files
%{python2_sitelib}/osg_reports
%{python2_sitelib}/osg_reports-%{version}-py2.7.egg-info

# Include config and doc files
%doc %{_defaultdocdir}/%{name}/*
%config(noreplace) %{_sysconfdir}/%{name}/osg.toml
%config(noreplace) %{_sysconfdir}/%{name}/html_templates/*.html

# Binaries
%attr(755, root, root) %{_bindir}/*

# Log dir
%dir /var/log/%{name}

%clean
rm -rf $RPM_BUILD_ROOT

%changelog
* Wed Jun 27 2018 Shreyas Bhat <sbhat@fnal.gov> - 2.0.1
- First version of this spec file.  Previously, this was installed along with gracc-reports (now a dependency) 
