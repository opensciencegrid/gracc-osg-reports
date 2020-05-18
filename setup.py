"""Setup file for gracc_osg_reports"""
import sys
from setuptools import setup

setup(name='gracc-osg-reports',
      version='3.1.0',
      description='OSG GRACC Email Reports',
      author_email='sbhat@fnal.gov',
      author='Shreyas Bhat',
      url='https://github.com/opensciencegrid/gracc-reporting',
      packages=['gracc_osg_reports'],
      install_requires=['gracc_reporting', 'elasticsearch_dsl', 'psycopg2', 'requests',],
      entry_points={
          'console_scripts': [
              'osgflockingreport = gracc_osg_reports.OSGFlockingReporter:main',
              'osgprojectreport = gracc_osg_reports.OSGProjectReporter:main',
              'osgpersitereport = gracc_osg_reports.OSGPerSiteReporter:main',
              'osgprobereport = gracc_osg_reports.ProbeReport:main',
              'osgtopoppusagereport = gracc_osg_reports.TopOppUsageByFacility:main',
              'osgmissingprojects = gracc_osg_reports.MissingProject:main',
              'osgmissingvo = gracc_osg_reports.MissingVO:main',
              'monthlysites = gracc_osg_reports.MonthlySitesViewReporter:main',
              ]
          }
     )
