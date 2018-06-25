"""Setup file for osg_reports"""
import sys
from setuptools import setup

# Enforce python version
VERSION_TUPLE = (2, 7)
if sys.version_info < VERSION_TUPLE:
    print "Sorry, installing osg_reports requires Python {0}.{1} " \
          "or above".format(*VERSION_TUPLE)
    exit(1)

setup(name='osg-reports',
      version='2.0',
      description='OSG GRACC Email Reports',
      author_email='sbhat@fnal.gov',
      author='Shreyas Bhat',
      url='https://github.com/opensciencegrid/gracc-reporting',
      packages=['osg_reports'],
      install_requires=['gracc_reporting>=2.0', 'elasticsearch_dsl==5.4.0',],
      entry_points={
          'console_scripts': [
              'osgflockingreport = osg_reports.OSGFlockingReporter:main',
              'osgprojectreport = osg_reports.OSGProjectReporter:main',
              'osgpersitereport = osg_reports.OSGPerSiteReporter:main',
              'osgprobereport = osg_reports.ProbeReport:main',
              'osgtopoppusagereport = osg_reports.TopOppUsageByFacility:main',
              'osgmissingprojects = osg_reports.MissingProject:main',
              ]
          }
     )
