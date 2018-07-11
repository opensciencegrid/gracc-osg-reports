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
