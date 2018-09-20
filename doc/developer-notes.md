gracc-osg-reports Developer Documentation
================

These are the developer docs for _gracc-osg-reports_.  They're by no means complete, but I've attempted to 
note the important info for anyone coming in and trying to write a report.

_gracc-osg-reports_ is a set of reports and a couple of helper modules built on top of [_gracc-reporting_](https://github.com/opensciencegrid/gracc-reporting),
that query [GRACC](https://gracc.opensciencegrid.org/) elasticsearch, aggregate and process the results
into a report, and email those to stakeholders.

Currently, the _gracc-osg-reports_ package assume that queries to the GRACC instance will be made using
Honza Kral's [elasticsearch-dsl-py](https://github.com/elastic/elasticsearch-dsl-py) library, and 
indeed, this is a dependency of this package.  Any report queries should be made using this API.  However, this may change in the 
future, since the ultimate aim is to provide flexibility for future report writers to simply 
send an HTTP POST or GET request to the GRACC instance, or use another API of their choosing.


# Parts of a gracc-osg report 

There are two main ways that the reports are structured.  The first uses the gracc-reporting library's 
text-processing utilities to automatically generate the report from the organized data, and should be used for 
all simpler reports (and whenever possible).  An example of this is the Flocking report.  The second method is to 
do all of the text manipulation and populate the HTML template manually.  An example of this is the Top Opportunistic Usage by Facility (news) report.

For both methods, you'll need to create a class for the report that subclasses ReportUtils.Reporter from gracc_reporting, and pass its required parameters into __init__ (config, start, end).
 This class will have to implement the following methods:

## run_report(self)


This is the higher-level method that simply calls all/any of the other methods.  In its simplest form, 
you can get away with just calling "send_report" (see below) from there.

## query(self)

This is where you define the elasticsearch query and the necessary aggregations.  To work with the run_query() method from ReportUtils.Reporter, query() should return the elasticsearch_dsl.Search() object after defining the query and aggregations.

## generate(self)

This is the higher level method that calls ReportUtils.Reporter.run_query(), goes through the results, and 
generates the raw data for the report.  Usually, it's a good idea to have this method yield rows of data 
for some other method to parse or act on.

## format_report(self)

This method is not required to be defined. Best practice, however, is to define either this or generate_report_file() (see below).
This method should take the data after parsing, and organize it into a dictionary of lists, with each list 
representing a column.  In that case, self.header (a list) should list the columns in order from left-to-right.  ReportUtils.Reporter.send_report will then insert this into the HTML template, 
a CSV file, and plaintext and send it.  Again, for an example, please see the Flocking Report (OsgFlockingReporter.py).

## generate_report_file(self)

This is the standard name used for a method that, instead of format_report, will populate the self.text 
attribute with the HTML that will be sent.  If you use this method, you should read in the HTML template, 
insert the text as needed along with any HTML, and save that HTML text to self.text.  ReportUtils.Reporter.send_report() 
will use this and send an HTML report.  An example that uses this method is the Top Opportunistic Usage by Facility Report (TopOppUsageByFacility.py).



# Putting it together into a report

The easiest way, then to write a report from these is to simply instantiate the report class from main() and then to call run_report() from that instantiation.  Without error handling, that might look like this:

```python
def main():
    CONFIG = "my_config.toml"
    m = MyReport(config_file=CONFIG, 
    		 start="2018-09-01", 
		 end="2018-09-08", 
		 template="/path/to/template_file")
    m.run_report()
    print "Yay, it worked!"
```

Of course, it's a better idea to actually do error checking.  To help with that, Reporter.ReportUtils has a 
function runerror(config_file, exception, traceback, logfile), that can be used to email the admins 
configured in your configuration file (see below) in case of an error.  Using this, you'd pass any exception up 
through the calls until you got here, and then run that function on the error inside an except clause.



## Helper methods in Reporter.ReportUtils


### runerror

Function for handling errors during execution of report.  Ideally, all errors are passed to the top 
level of the report, which then has _runerror_ in an *except* clause.  _runerror_ will log the error, 
the traceback, and email the admins (test.emails).

### coroutine

A helper decorator that advances a coroutine to its first yield point.  Adapted from
http://www.dabeaz.com/coroutines/Coroutines.pdf

### get_report_parser

Creates a parser for evaluating command-line options.  Can be called with time options (start, end) by 
default, or without by calling get_report_parser(no_time_options=True).  




# Configuration

The configuration file that all _gracc_reporting_-based packages expect is a toml file.  It should, at the minimum, have
the following:

```toml
 [elasticsearch]
    hostname = 'https://gracc.opensciencegrid.org/q'

# Email
# Set the global email related values under this section
[email]
    # This is the FQDN of the mail server, which GRACC will use to send the email
    smtphost = 'smtp.example.com'

    [email.from]
        name = 'GRACC Operations'  # This is the real name from which the report appears to be emailed from
        email = 'somebody@somewhere.com'  # This is the email from which the reports appears to be emailed from

    # Tester emails
    [email.test]
        names = ['Test Recipient', ]
	emails = ['admin@somwhere.com', ]

# Report-specific
[report_name]
    index_pattern='some.index.pattern'
    to_emails = ['nobody@example.com', ]
    to_names = ['Recipient Name', ]
 ```

 If using the Report.get_report_parser, the command-line flag to specify a config file is -c.  There is a sample toml file included in the repository.


# How to build gracc-osg-reports

Building _gracc-osg-reports_ is quite simple.  To build the package, first make any necessary changes in 
setup.py in the root of the repository.  Then, simply run 
```
python setup.py sdist
```
You can then unwind the tarball created in the _dist_ directory wherever you want to deploy this, and run 
```
python setup.py install
```
Make sure _gracc-reporting_ is installed before you try to install _gracc-osg-reports_.

For an OSG installation, for which we use a docker container to build reports on, navigate to 
_packaging/_ and run _create_docker_image.sh_.  Keep in mind that you must have write access to the Open 
Science Grid docker hub gracc-reporting repository in order to run this script.
