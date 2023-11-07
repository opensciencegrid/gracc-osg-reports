import re
import traceback
import sys
import copy
from collections import defaultdict
import argparse
import pandas as pd
import numpy as np
import datetime
import calendar
import dateutil.parser
import requests
import yaml

from elasticsearch_dsl import Search

from gracc_reporting import ReportUtils

LOGFILE = 'osgpayloadandbatch.log'
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


class PayloadAndPilotHours(ReportUtils.Reporter):
    """Class to hold the information for and run the OSG Project Report

    :param str report_type: OSG, XD. or OSG-Connect
    :param str config_file: Configuration file
    :param str start: Start time for report range
    :param str end: End time for report range
    :param bool isSum: Show a total line at bottom of report, defaults to True
    """
    def __init__(self, config_file, start, end=None,
                 **kwargs):

        report_type = "PayloadAndPilot"
        super(PayloadAndPilotHours, self).__init__(report_type=report_type,
                                          config_file=config_file,
                                          start=start,
                                          end=end,
                                          **kwargs)
        #self.report_type = "MonthlySites"
        self.title = "OSG Payload and Pilot hours per site {}".format(datetime.datetime.now().strftime("%Y-%m-%d"))
        self.logger.info("Report Type: {0}".format(self.report_type))
        self.sites = None
        self.overrides = {}

    def run_report(self):
        """Higher level method to handle the process flow of the report
        being run"""
        self.send_report()


    def query(self, record_type="Payload", sites = []):
        """Method to query Elasticsearch cluster for Payload information

        :return elasticsearch_dsl.Search: Search object containing ES query
        """
        # Gather parameters, format them for the query
        index = "gracc.osg.summary"
        from_date = datetime.datetime.now() - datetime.timedelta(days=14)
        from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
        to_date = datetime.datetime.now()
        s = Search(using=self.client, index=index)
        s = s.filter('range', **{'EndTime': {'from': from_date, 'to': to_date }}) \
             .filter('terms', OIM_Site=sites)
        s = s.query('match', ResourceType=record_type)

        # Limit to the osg vo.
        s = s.query('match', VOName='osg')

        unique_terms = ["EndTime", "OIM_Site"]
        metrics = ["CoreHours", "Njobs"]

        curBucket = s.aggs.bucket(unique_terms[0], 'date_histogram', field=unique_terms[0], interval="day")
        new_unique_terms = unique_terms[1:]

        for term in new_unique_terms:
            curBucket = curBucket.bucket(term, 'terms', field=term, size=(2**31)-1)

        for metric in metrics:
            curBucket.metric(metric, 'sum', field=metric, missing=0)
        

        return s


    def download_sites(self) -> list:
        """Downloads the list of sites from github raw and parses it

        :return list: List of sites
        """
        # Download the list of sites from github raw and parse it
        if self.sites is not None:
            return self.sites
        self.sites = []
        self.overrides = {}
        sites_url = self.config[self.report_type.lower()]['sites_url']
        response = requests.get(sites_url)
        print(response)
        if response.status_code == 200:
            # We got the sites config, parse it as yaml
            sites_config = yaml.safe_load(response.text)

            # sites is just a list of the keys
            self.sites = list(sites_config.keys())

            # But, we have to loop through all the sites looking for name_overrides
            for site in sites_config.keys():
                if sites_config[site] == None:
                    continue
                if 'name_override' in sites_config[site]:
                    self.overrides[site] = sites_config[site]['name_override']

        else:
            self.logger.error("Unable to download sites from github.  Status code: {}".format(response.status_code))
        return self.sites


    def generate_report_file(self):
        """Takes data from query response and parses it to send to other
        functions for processing"""
        
        # These could probably be combined into one query, but I'm not sure how to do that
        # Or these could be farmed out to separate threads or processes
        sites = self.download_sites()
        #sites = self.config[self.report_type.lower()]['sites']
        response_payload = self.query("Payload", sites).execute()
        response_pilot = self.query("Batch", sites).execute()

        unique_terms = ["EndTime", "OIM_Site"]
        metrics = ["CoreHours", "Njobs"]

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


        df_payload = pd.DataFrame()

        # Process the payload data
        for day in response_payload.aggregations['EndTime']['buckets']:
            data = []
            recurseBucket({"EndTime": day['key_as_string']}, day, 1, data)
            temp_df = pd.DataFrame(data)
            df_payload = pd.concat([df_payload, temp_df], axis=0)
        
        df_pilot = pd.DataFrame()
        # Process the pilot data
        for day in response_pilot.aggregations['EndTime']['buckets']:
            data = []
            recurseBucket({"EndTime": day['key_as_string']}, day, 1, data)
            temp_df = pd.DataFrame(data)
            df_pilot = pd.concat([df_pilot, temp_df], axis=0)

        #df_payload['OIM_Site'] = df_payload['OIM_Site'].map(lambda name: name + " (Payload)")
        #df_pilot['OIM_Site'] = df_pilot['OIM_Site'].map(lambda name: name + " (Pilot)")

        # Add a column for payload or pilot
        df_payload['ResourceType'] = "Payload"
        df_pilot['ResourceType'] = "Batch"

        # Convert to datetime, and remove everything but the date, no time needed
        df = pd.concat([df_payload, df_pilot], axis=0)
        df['EndTime'] = pd.to_datetime(df['EndTime'])
        df['EndTime'] = df['EndTime'].dt.date

        # Use a pivot table to create a good table with the columns as time
        hours_table = pd.pivot_table(df, columns=["EndTime"], values=["CoreHours"], index=["OIM_Site", 'ResourceType'], fill_value=0.0, aggfunc=np.sum)
        hours_table.columns = hours_table.columns.droplevel(0)
        hours_table['Values'] = "Hours"

        # And with the number of jobs as well
        jobs_table = pd.pivot_table(df, columns=["EndTime"], values=["Njobs"], index=["OIM_Site", 'ResourceType'], fill_value=0.0, aggfunc=np.sum)
        jobs_table.columns = jobs_table.columns.droplevel(0)
        jobs_table['Values'] = "#Jobs"

        # Concatenate the two tables
        table = pd.concat([hours_table, jobs_table], axis=0)

        # Add the Values to the index
        table.set_index(['Values'], append=True, inplace=True)

        # Add a sum and average column
        sum_col = table.sum(axis=1)
        mean_col = table.mean(axis=1, numeric_only=True, skipna=True)
        table['Sum'] = sum_col
        table['Average'] = mean_col

        # Check for missing sites, add them if necessary:
        for site in sites:
            for resource_type in ["Payload", "Batch"]:
                for values_type in ["Hours", "#Jobs"]:
                    if (site, resource_type, values_type) not in table.index:
                        # Append a row to the table
                        ser = pd.Series(name=(site, resource_type, values_type), data=np.full(table.shape[1], "-"), index=table.columns)
                        table = table.append(ser)

        
        return table

    def format_report(self):
        """Report formatter.  Returns a dictionary called report containing the
        columns of the report.

        :return dict: Constructed dict of report information for
        Reporter.send_report to send report from"""

        table = self.generate_report_file()
        
        # Truncate the decimals in the columns
        table = table.applymap(lambda x: round(x) if isinstance(x, float) and not pd.isnull(x) else x)

        # Sort the table first by site, then by resource type
        # This will put the Batch rows after the Payload rows
        # The first sort is mostly just to order to the resourceType column
        table.sort_values(by=["OIM_Site", "Values", "ResourceType"], ascending=[True, True, True], inplace=True)

        # Reindex the table to put the sites in the order from the downloaded sites file
        table = table.reindex(self.download_sites(), level=0)

        # Add a blank row between each site
        # Calculate the total size of the new dataframe, 1 new row for each 2 existing rows
        new_size = len(table) + int(len(table)/4)

        # Create a new dataframe with the new size
        table.reset_index(inplace=True)
        new_index = pd.RangeIndex(start=0, stop=new_size, step=1)
        new_df = pd.DataFrame(np.nan, index=new_index, columns=table.columns)

        # A function to perform the following mapping to add a blank line between each site:
        # 0 -> 0
        # 1 -> 1
        # 2 -> 2
        # 3 -> 3
        # 4 -> 5
        # 5 -> 6
        # There has got to be a better algorithm for this, but I can't think of one
        next_row = 0
        for i in range(0, len(table), 4):
            # Copy the 4 rows from the old table to the new table
            for j in range(4):
                new_df.loc[next_row+j] = table.iloc[i+j]
            new_df.loc[next_row+4] = np.nan
            next_row += 5

        table = new_df

        # Convert the headers to just MM-DD
        def date_to_monthdate(date):
            if isinstance(date, str):
                return date
            return date.strftime("%m-%d")

        results = map(date_to_monthdate, table.columns)
        table.columns = results

        # Set the index to the OIM_Site and ResourceType
        table.set_index(["OIM_Site", "ResourceType", "Values"], inplace=True)

        # Convert the sites (first column) using the overrides dictionary
        table.rename(index=self.overrides, level=0, inplace=True)

        # Create the report

        return table.reset_index()




def main():
    args = parse_report_args()
    logfile_fname = args.logfile if args.logfile is not None else LOGFILE

    try:
        r = PayloadAndPilotHours(config_file=args.config,
                        start=args.start,
                        end=args.end,
                        verbose=args.verbose,
                        is_test=args.is_test,
                        no_email=args.no_email,
                        logfile=logfile_fname,
                        template=args.template)
        r.run_report()
        r.logger.info("OSG Payload and Batch Report executed successfully")

    except Exception as e:
        ReportUtils.runerror(args.config, e, traceback.format_exc(), args.logfile)
        sys.exit(1)
    sys.exit(0)


if __name__=="__main__":
    main()
