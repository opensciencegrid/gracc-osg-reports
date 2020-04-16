import sys
import traceback
import datetime
import copy
import argparse
from collections import namedtuple
from collections import defaultdict


from dateutil.relativedelta import *

from elasticsearch_dsl import Search

from gracc_reporting import ReportUtils, TimeUtils
from gracc_reporting.NiceNum import niceNum
#from .NameCorrection import NameCorrection


LOGFILE = 'topoppusage.log'
MAXINT = 2**31-1
facilities = {}


# Helper functions
def get_time_range(start=None, end=None, months=None):
    """
    Returns time ranges for current and prior reporting periods  Can either
    handle absolute range (start-end) or a certain number of months prior to
    today's date (months)

    :param str start: Start of current reporting period.  Date/time as 
    datetime.datetime object
    :param str end: Same as start, but end of current reporting period
    :param int months: Number of months prior to current date, to define
    reporting period.
    :return namedtuple: Tuple of tuples of datetime.datetime objects representing
    date ranges (prior_period, cur_period)  
    """
    if months:
        if start or end:
            raise Exception("Cannot define both months and start/end times")
        end = datetime.datetime.today()
        diff = relativedelta(months=months)
        start = end - diff
    else:
        diff = relativedelta(end, start)
    pri_end = start - relativedelta(days=1)
    pri_start = pri_end - diff
    date_range = namedtuple('date_range', ['start', 'end'])
    range_pair = namedtuple('range_pair', ['prior', 'current'])
    r = range_pair(prior=date_range(start=pri_start, end=pri_end), 
                   current=date_range(start=start, end=end))
    return r


def parse_report_args():
    """
    Specific argument parser for this report.
    :return: Namespace of parsed arguments
    """
    parser = argparse.ArgumentParser(parents=[ReportUtils.get_report_parser()])
    parser.add_argument("-m", "--months", dest="months",
                        help="Number of months to run report for",
                        default=None, type=int)
    parser.add_argument("-N", "--numrank", dest="numrank",
                        help="Number of Facilities to rank",
                        default=None, type=int)
    return parser.parse_args()


class TopOppUsageByFacility(ReportUtils.Reporter):
    """
    Class to hold information and generate Top Opp Usage by Facility report

    :param str config: Report Configuration file
    :param str start: Start time of report range
    :param str end: End time of report range
    :param int numrank: Number of Facilities to rank.  Default 10.
    :param int months: Number of months prior to today to set start of report
    range
    """
    def __init__(self, config_file, start=None, end=None, numrank=10, 
                 months=None, **kwargs):
        report = 'news'


        super(TopOppUsageByFacility, self).__init__(report_type=report,
                                                    config_file=config_file,
                                                    start=start,
                                                    end=end,
                                                    **kwargs)

        self.numrank = numrank
        self.text = ''
        self.table = ''
        self.daterange = get_time_range(self.start_time, self.end_time, months)

        dates_formatted = (x.strftime("%Y-%m-%d %H:%M") for x in self.daterange.current)
        self.title = "Opportunistic Resources provided by the top {0} OSG " \
                     "Sites for the OSG Open Facility ({1} - {2})".format(
                        self.numrank, *dates_formatted)
        self.header = ["Facility", "Core Hours"]

    def run_report(self):
        """Handles the data flow throughout the report generation.  Generates
        the raw data, the HTML report, and sends the email.

        :return None
        """
        self.send_report()
        return

    def query(self):
        """
        Method to query Elasticsearch cluster for EfficiencyReport information

        :return elasticsearch_dsl.Search: Search object containing ES query
        """
        # Gather parameters, format them for the query
        starttimeq = self.start_time.isoformat()
        endtimeq = self.end_time.isoformat()

        probelist = self.config[self.report_type.lower()]['OSG_flocking_probe_list']

        if self.verbose:
            self.logger.info(self.indexpattern)
            self.logger.info(probelist)

        # Elasticsearch query and aggregations
        s = Search(using=self.client, index=self.indexpattern) \
                .filter("range", EndTime={"gte": starttimeq, "lt": endtimeq}) \
                .filter("terms", ProbeName=probelist) \
                .filter("term", ResourceType="Payload")[0:0]

        # Size 0 to return only aggregations

        Bucket = s.aggs.bucket('OIM_Facility', 'terms', field='OIM_Facility',
                                   size=MAXINT, order={'CoreHours': 'desc'})

        Bucket.metric('CoreHours', 'sum', field='CoreHours')

        print(s.to_dict())
        return s

    def generate_report(self):
        """
        Runs the ES query, checks for success, and then
        sends the raw data to parser for processing.

        :return: None
        """
        results = self.run_query()
        unique_terms = ['OIM_Facility']
        metrics = ['CoreHours']

        def recurseBucket(curData, curBucket, index, data):
            """
            Recursively process the buckets down the nested aggregations

            :param curData: Current parsed data that describes curBucket and will be copied and appended to
            :param bucket curBucket: A elasticsearch bucket object
            :param int index: Index of the unique_terms that we are processing
            :param data: list of dicts that holds results of processing

            :return: None.  But this will operate on a list *data* that's passed in and modify it
            """
            curTerm = unique_terms[index]

            # Check if we are at the end of the list
            if not curBucket[curTerm]['buckets']:
                # Make a copy of the data
                nowData = copy.deepcopy(curData)
                data.append(nowData)
            else:
                # Get the current key, and add it to the data
                for bucket in curBucket[curTerm]['buckets']:
                    nowData = copy.deepcopy(
                        curData)  # Hold a copy of curData so we can pass that in to any future recursion
                    nowData[curTerm] = bucket['key']
                    if index == (len(unique_terms) - 1):
                        # reached the end of the unique terms
                        for metric in metrics:
                            nowData[metric] = bucket[metric].value
                            # Add the doc count
                        nowData["Count"] = bucket['doc_count']
                        data.append(nowData)
                    else:
                        recurseBucket(nowData, bucket, index + 1, data)

        data = []
        recurseBucket({}, results, 0, data)
        allterms = copy.copy(unique_terms)
        allterms.extend(metrics)

        for entry in data:
            yield [entry[field] for field in allterms]


    def format_report(self):
        """Report formatter.  Returns a dictionary called report containing the
        columns of the report.

        :return dict: Constructed dict of report information for
        Reporter.send_report to send report from"""
        report = defaultdict(list)

        for result_list in self.generate_report():
            mapdict = dict(list(zip(self.header, result_list)))
            for key, item in mapdict.items():
                report[key].append(item)

        return report


def main():
    args = parse_report_args()
    logfile_fname = args.logfile if args.logfile is not None else LOGFILE


    try:
        r = TopOppUsageByFacility(config_file=args.config,
                                  start=args.start,
                                  end=args.end,
                                  template=args.template,
                                  months=args.months,
                                  is_test=args.is_test,
                                  no_email=args.no_email,
                                  verbose=args.verbose,
                                  numrank=args.numrank,
                                  logfile=logfile_fname)
        r.run_report()
        print("Top Opportunistic Usage per Facility Report execution successful")

    except Exception as e:
        errstring = '{0}: Error running Top Opportunistic Usage Report. ' \
                    '{1}'.format(datetime.datetime.now(),
                                 traceback.format_exc())
        ReportUtils.runerror(args.config, e, errstring, logfile_fname)
        sys.exit(1)


if __name__ == "__main__":
    main()
    sys.exit(0)
