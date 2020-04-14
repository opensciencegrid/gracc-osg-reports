import datetime
import traceback
import sys
from collections import defaultdict
import argparse

from elasticsearch_dsl import Search

from gracc_reporting import ReportUtils, TimeUtils


LOGFILE = 'osgflockingreport.log'
MAXINT = 2**31 - 1


class FlockingReport(ReportUtils.Reporter):
    """Class to hold information for and to run OSG Flocking report

    :param str config_file: Report Configuration filename
    :param str start: Start time of report range
    :param str end: End time of report range
    """
    def __init__(self, config_file, start, end, **kwargs):
        report = 'Flocking'

        super(FlockingReport, self).__init__(config_file=config_file, 
                                             start=start, 
                                             end=end,
                                             report_type=report,
                                             **kwargs)
        self.title = "OSG Flocking: Usage of OSG Sites for {0} - {1}".format(
            start, end)

        self.header = ["VOName", "SiteName", "ProbeName", "ProjectName",
                       "Wall Hours"]

    def run_report(self):
        """Higher level method to handle the process flow of the report
        being run"""
        self.send_report()

    def query(self):
        """Method to query Elasticsearch cluster for Flocking Report
        information

        :return elasticsearch_dsl.Search: Search object containing ES query
        """
        # Gather parameters, format them for the query
        starttimeq = self.start_time.isoformat()
        endtimeq = self.end_time.isoformat()

        if self.verbose:
            self.logger.info(self.indexpattern)

        probeslist = self.config[self.report_type.lower()]['probe_list']

        # Elasticsearch query and aggregations
        s = Search(using=self.client, index=self.indexpattern) \
                .filter("range", EndTime={"gte": starttimeq, "lt": endtimeq}) \
                .filter("terms", ProbeName=probeslist)\
                .filter("term", ResourceType="Payload")[0:0]
        # Size 0 to return only aggregations

        # Bucket aggs
        Bucket = s.aggs.bucket('group_Site', 'terms', field='SiteName', size=MAXINT) \
            .bucket('group_VOName', 'terms', field='ReportableVOName', size=MAXINT) \
            .bucket('group_ProbeName', 'terms', field='ProbeName', size=MAXINT) \
            .bucket('group_ProjectName', 'terms', field='ProjectName', missing='N/A', size=MAXINT)

        # Metric aggs
        Bucket.metric("CoreHours_sum", "sum", field="CoreHours")

        return s

    def generate(self):
        """Higher-level generator method that calls the lower-level functions
        to generate the raw data for this report.

        Yields rows of raw data
        """
        results = self.run_query()

        # Iterate through the buckets to get our data, yield it
        for site in results.group_Site.buckets:
            sitekey = site.key
            for vo in site.group_VOName.buckets:
                vokey = vo.key
                for probe in vo.group_ProbeName.buckets:
                    probekey = probe.key
                    projects = (project for project in probe.group_ProjectName.buckets)
                    for project in projects:
                        yield (sitekey, vokey, probekey, project.key, project.CoreHours_sum.value)

    def format_report(self):
        """Report formatter.  Returns a dictionary called report containing the
        columns of the report.

        :return dict: Constructed dict of report information for
        Reporter.send_report to send report from"""
        report = defaultdict(list)

        for result_tuple in self.generate():
            if self.verbose:
                print("{0}\t{1}\t{2}\t{3}\t{4}".format(*result_tuple))

            mapdict = dict(list(zip(self.header, result_tuple)))
            for key, item in mapdict.items():
                report[key].append(item)

        tot = sum(report['Wall Hours'])
        for col in self.header:
            if col == 'VOName':
                report[col].append('Total')
            elif col == 'Wall Hours':
                report[col].append(tot)
            else:
                report[col].append('')

        if self.verbose:
            print("The total Wall hours in this report are {0}".format(tot))

        return report


def main():
    args = ReportUtils.get_report_parser().parse_args()
    logfile_fname = args.logfile if args.logfile is not None else LOGFILE

    try:
        # Create an FlockingReport object, and run the report
        f = FlockingReport(config_file = args.config,
                           start=args.start,
                           end=args.end,
                           template=args.template,
                           is_test=args.is_test,
                           no_email=args.no_email,
                           verbose=args.verbose,
                           logfile=logfile_fname)

        f.run_report()
        print("OSG Flocking Report execution successful")
    except Exception as e:
        errstring = '{0}: Error running OSG Flocking Report. ' \
                    '{1}'.format(datetime.datetime.now(), traceback.format_exc())
        ReportUtils.runerror(args.config, e, errstring, logfile_fname)
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()

