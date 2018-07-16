GRACC OSG Reports
============

_gracc-osg-reports_ is a set of reports that collect and present data from the OSG monitoring 
system [GRACC](https://gracc.opensciencegrid.org) to Open Science Grid stakeholders.  These reports were 
previously packaged along with the underlying libraries [gracc-reporting](https://github.com/opensciencegrid/gracc-reporting), 
but have now been separated out to facilitate independent development on the reports or the libraries on which they 
depend.

For each report, you can specify a non-standard location for the config file with -c, template file with -T, or 
a logfile with -L.  In the absence of the latter, the reports log to stdout.  The -d, -n, and -v flags are, 
respectively, dryrun (test), no email, and verbose.


Installation
-------------

To set up gracc-osg-reports within a virtual environment:

Make sure you have the latest version of [pip.](https://pip.pypa.io/en/stable/installing/#do-i-need-to-install-pip)

Then:
Make sure pip is up to date:
```
   pip install -U pip
```
Install virtualenv if you haven't already:
```
   pip install virtualenv
```
The first time you do this:
```
   virtualenv gracc_venv                # Or whatever other name you want to give your virtualenv instance
   source gracc_venv/bin/activate       # Activate the virtualenv
```

You'll need to install [gracc-reporting](https://github.com/opensciencegrid/gracc-reporting) first.  Navigate to the previous link and 
follow the installation instructions there within the virtualenv.

Then, within the same virtualenv in which you've installed gracc-reporting, all you'll need to do is:

```
   python setup.py install              # Install gracc-osg-reports
```

To access this sandbox later, go to the dir with gracc_venv in it, and:
```
   source gracc_venv/bin/activate
```
and do whatever you need!  If you can't run pip installs on your machine,
then if you have virtualenv, activate it and then upgrade pip and install the 
requirements.

Running reports
---------------


Examples:

**OSG Project Usage Report:**
```
    osgprojectreport -s 2016-12-06 -e 2016-12-13 -r OSG-Connect -d -v -n   # No missing projects in this case
    osgprojectreport -s 2016-12-06 -e 2016-12-13 -r XD -d -v -n   # Missing projects in this case
```
**Missing Projects report:**
```
    osgmissingprojects -s 2016-12-06 -e 2017-01-31 -r XD -d -n -v
```
**OSG Usage Per Site Report:**
```
    osgpersitereport -s 2016/10/01 -d -v -n
```
**OSG Flocking Report:**
```
    osgflockingreport -s 2016-11-09 -e 2016-11-16 -d -v -n
```
**Gratia Probes that haven't reported in the past two days:**
```
    osgprobereport -d -n -v
```
**Top [N] Providers of Opportunistic Hours on the OSG (News Report):**

Monthly:
```
    osgtopoppusagereport -m 2 -N 20 -d -v -n
```
Absolute dates:
```
    osgtopoppusagereport -s "2016-12-01" -e "2017-02-01" -N 20 -d -v -n
```

Docker files 
------------

Included in this repository are a set of Dockerfiles, one per report, wrapper scripts, and docker-compose files meant for running
these reports (installed in /opt/gracc-osg-reports) individually.  If you use the docker images to run the reports, separate 
installation of gracc-osg-reports (as detailed above) is unnecessary.  

The Dockerfiles and docker-compose files can of course be modified for other setups.

If you'd like to simply run a container with the reports preinstalled, do:
```
	docker pull opensciencegrid/gracc-osg-reports:2.0
	docker run -it opensciencegrid/gracc-osg-reports:2.0 /bin/sh
```


