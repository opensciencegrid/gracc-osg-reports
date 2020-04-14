import re
import traceback
import sys
import copy
from collections import defaultdict
import argparse
import requests
import xml.etree.ElementTree as ET

from elasticsearch_dsl import Search

from gracc_reporting import ReportUtils

LOGFILE = 'osgprojectreporter.log'
MAXINT = 2**31 - 1


# Helper Functions
def key_to_lower(bucket):
    return bucket.key.lower()


class MissingVOReporter(ReportUtils.Reporter):
    """Class to hold the information for and run the OSG Project Report

    :param str config_file: Configuration file
    :param str start: Start time for report range
    :param str end: End time for report range
    """
    def __init__(self, config_file, start, end=None, **kwargs):
        report = 'missingvo'
        super(MissingVOReporter, self).__init__(report_type=report, 
                                          config_file=config_file, 
                                          start=start, 
                                          end=end, 
                                          **kwargs)
        self.header = ["VO Name", "Reporting Probe", "Core Hours"]
        self.title = "Missing VO Report"

    def run_report(self):
        """Higher level method to handle the process flow of the report
        being run"""
        self.send_report()

    def query(self):
        """Method to query Elasticsearch cluster for OSGVOReporter information

        :return elasticsearch_dsl.Search: Search object containing ES query
        """
        # Gather parameters, format them for the query
        starttimeq = self.start_time.isoformat()
        endtimeq = self.end_time.isoformat()

        if self.verbose:
            self.logger.info(self.indexpattern)

        # Elasticsearch query and aggregations
        s = Search(using=self.client, index=self.indexpattern) \
                .filter("range", EndTime={"gte": starttimeq, "lt": endtimeq}) \
                .filter("range", WallDuration={"gt": 0}) #\
                #.filter("term", ResourceType="Batch")[0:0]
        # Size 0 to return only aggregations
        # Bucket, metric aggs
        Bucket = s.aggs.bucket("VOName", "terms", field="VOName",
                               size=MAXINT, order={"_term":"asc"},
                               missing="UNKNOWN") \
                    .bucket("ProbeName", "terms", field="ProbeName", missing="UNKNOWN", size=MAXINT)\

        Bucket.metric("CoreHours", "sum", field="CoreHours")

        return s

    def generate_report_file(self):
        """Takes data from query response and parses it to send to other
        functions for processing"""
        results = self.run_query()

        unique_terms = ['VOName', 'ProbeName']
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

        data = []
        recurseBucket({}, results, 0, data)
        allterms = copy.copy(unique_terms)
        allterms.extend(metrics)

        print(data)
        for entry in data:
            yield [entry[field] for field in allterms]

    def getAuthortativeVOs(self):

        oim_url = self.config['missingvo']['vo_oim_url']
        full_xml = requests.get(oim_url)
        tree = ET.fromstring(full_xml.text.encode('utf-8'))
        vos = {}
        #root = tree.getroot()
        for vo_elt in tree.findall('./VO/Name'):
            vo_name = vo_elt.text
            vos[vo_name.lower()] = 1
        
        return vos


    def format_report(self):
        """Report formatter.  Returns a dictionary called report containing the
        columns of the report.

        :return dict: Constructed dict of report information for
        Reporter.send_report to send report from"""
        report = defaultdict(list)
        authortative_vos = self.getAuthortativeVOs()

        for result_list in self.generate_report_file():

            #if self.verbose:
            #    print u"{0}\t{1}\t{2}\t{3}\t{4}".format(*result_list)
            if result_list[0] in authortative_vos:
                continue
            mapdict = dict(list(zip(self.header, result_list)))
            print(("Adding bad VO: {}".format(result_list)))
            for key, item in mapdict.items():
                report[key].append(item)

        
        tot = sum(report['Core Hours'])
        for field in self.header:
            if field == 'VO Name':
                report[field].append('Total')
            elif field == 'Core Hours':
                report[field].append(tot)
            else:
                report[field].append('')

        if self.verbose:
            self.logger.info("The total wall hours in this report are "
                                "{0}".format(tot))

        return report



def main():
    args = ReportUtils.get_report_parser().parse_args()
    logfile_fname = args.logfile if args.logfile is not None else LOGFILE

    #try:
    r = MissingVOReporter(config_file=args.config,
                    start=args.start,
                    end=args.end,
                    verbose=args.verbose,
                    is_test=args.is_test,
                    no_email=args.no_email,
                    logfile=logfile_fname,
                    template=args.template)
    r.run_report()
    r.logger.info("OSG Missing VO Report executed successfully")

    #except Exception as e:
    #    ReportUtils.runerror(args.config, e, traceback.format_exc(), args.logfile)
    #    sys.exit(1)
    #sys.exit(0)


if __name__=="__main__":
    main()
