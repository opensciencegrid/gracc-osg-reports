import re
import traceback
import sys
import copy
from collections import defaultdict
import argparse
import pandas as pd
import datetime
import calendar
import dateutil.parser

from elasticsearch_dsl import Search

from gracc_reporting import ReportUtils

LOGFILE = 'osgmonthlysites.log'
MAXINT = 2**31 - 1


# Helper Functions
def key_to_lower(bucket):
    return bucket.key.lower()


def parse_report_args():
    """
    Specific argument parser for this report.
    :return: Namespace of parsed arguments
    """
    parser = argparse.ArgumentParser(parents=[ReportUtils.get_report_parser()])
    return parser.parse_args()


class OSGMonthlySitesViewReporter(ReportUtils.Reporter):
    """Class to hold the information for and run the OSG Project Report

    :param str report_type: OSG, XD. or OSG-Connect
    :param str config_file: Configuration file
    :param str start: Start time for report range
    :param str end: End time for report range
    :param bool isSum: Show a total line at bottom of report, defaults to True
    """
    def __init__(self, config_file, start, end=None,
                 **kwargs):

        report_type = "MonthlySites"
        super(OSGMonthlySitesViewReporter, self).__init__(report_type=report_type,
                                          config_file=config_file,
                                          start=start,
                                          end=end,
                                          **kwargs)
        #self.report_type = "MonthlySites"
        self.title = "OSG site hours by month as of {}".format(datetime.datetime.now().strftime("%Y-%m-%d"))
        self.logger.info("Report Type: {0}".format(self.report_type))

    def run_report(self):
        """Higher level method to handle the process flow of the report
        being run"""
        self.send_report()

    def query(self):
        """Method to query Elasticsearch cluster for OSGProjectReporter information

        :return elasticsearch_dsl.Search: Search object containing ES query
        """
        # Gather parameters, format them for the query
        index = "gracc.osg.summary"
        from_date = datetime.datetime.now() - datetime.timedelta(days=365)
        from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0, day=1)
        to_date = datetime.datetime.now()
        s = Search(using=self.client, index=index)
        s = s.filter('range', **{'EndTime': {'from': from_date, 'to': to_date }})
        s = s.query('match', ResourceType="Batch")

        unique_terms = ["EndTime", "OIM_Site", "VOName"]
        metrics = ["CoreHours"]

        curBucket = s.aggs.bucket(unique_terms[0], 'date_histogram', field=unique_terms[0], interval="month")
        new_unique_terms = unique_terms[1:]

        for term in new_unique_terms:
            curBucket = curBucket.bucket(term, 'terms', field=term, size=(2**31)-1)

        for metric in metrics:
            curBucket.metric(metric, 'sum', field=metric)
        

        return s


    def generate_report_file(self):
        """Takes data from query response and parses it to send to other
        functions for processing"""
        

        response = self.query().execute()

        unique_terms = ["EndTime", "OIM_Site", "VOName"]
        metrics = ["CoreHours"]

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
                for bucket in self.sorted_buckets(curBucket[curTerm], key=key_to_lower):
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


        df = pd.DataFrame()
        for month in response.aggregations['EndTime']['buckets']:
            data = []
            recurseBucket({"EndTime": month['key_as_string']}, month, 1, data)
            temp_df = pd.DataFrame(data)
            df = pd.concat([df, temp_df], axis=0)


        # Convert to datetime, and remove everything but the date, no time needed
        df['EndTime'] = pd.to_datetime(df['EndTime'])
        df['EndTime'] = df['EndTime'].dt.date

        # Use a pivot table to create a good table with the columns as time
        table = pd.pivot_table(df, columns=["EndTime"], values=["CoreHours"], index=["OIM_Site"], fill_value=0.0)
        table.columns = table.columns.get_level_values(1)
        return table

    def format_report(self):
        """Report formatter.  Returns a dictionary called report containing the
        columns of the report.

        :return dict: Constructed dict of report information for
        Reporter.send_report to send report from"""

        table = self.generate_report_file()

        # Figure out the percentage of the month we have completed
        now = datetime.datetime.now()
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        percentage = float(now.day) / float(days_in_month)

        # Convert the headers to just YYYY-MM
        def date_to_yeardate(date):
            return date.strftime("%Y-%m")

        results = map(date_to_yeardate, table.columns)
        table.columns = results

        # Multiply the last full month by the percent completed
        full_month = table.columns.values.tolist()[-2]
        multiplied_column = table[table.columns[-2]] * percentage
        table.insert(len(table.columns)-1, "{} * {:.2f}".format(full_month, percentage), multiplied_column)

        print(table.reset_index().to_csv(index=False))
        return table.reset_index()




def main():
    args = parse_report_args()
    logfile_fname = args.logfile if args.logfile is not None else LOGFILE

    try:
        r = OSGMonthlySitesViewReporter(config_file=args.config,
                        start=args.start,
                        end=args.end,
                        verbose=args.verbose,
                        is_test=args.is_test,
                        no_email=args.no_email,
                        logfile=logfile_fname,
                        template=args.template)
        r.run_report()
        r.logger.info("OSG Project Report executed successfully")

    except Exception as e:
        ReportUtils.runerror(args.config, e, traceback.format_exc(), args.logfile)
        sys.exit(1)
    sys.exit(0)


if __name__=="__main__":
    main()
