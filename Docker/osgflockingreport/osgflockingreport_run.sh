#!/bin/sh

# Wrapper script to run the OSG Flocking report inside a Docker container
# Example:  ./flocking_run.sh weekly


export TOPDIR=/opt/gracc-osg-reports
export LOCALLOGDIR=${TOPDIR}/log
export SCRIPTLOGFILE=${LOCALLOGDIR}/flocking_run.log
export REPORTLOGFILE=${LOCALLOGDIR}/osgflockingreport.log
export CONFIGDIR=${TOPDIR}/config

function usage {
    echo "Usage:    ./flocking_run.sh [-p] <time period>"
    echo ""
    echo "Time periods are: daily, weekly, bimonthly, monthly, yearly"
    echo "-p flag (optional) logs report runs to prometheus pushgateway"
    exit
}

function set_dates {
        case $1 in
                "daily") export starttime=`date --date='1 day ago' +"%F %T"`;;
                "weekly") export starttime=`date --date='1 week ago' +"%F %T"`;;
                "bimonthly") export starttime=`date --date='2 month ago' +"%F %T"`;;
                "monthly") export starttime=`date --date='1 month ago' +"%F %T"`;;
                "yearly") export starttime=`date --date='1 year ago' +"%F %T"`;;
                *) echo "Error: unknown period $1. Use weekly, monthly or yearly"
                         exit 1;;
        esac
        echo $starttime
}


# Initialize everything
# Check arguments
if [[ $# -lt 1 || $# -gt 2 ]] || [[ $1 == "-h" ]] || [[ $1 == "--help" ]] ;
then
    usage
fi

set_dates $1
export endtime=`date +"%F %T"`

# Check to see if logdir exists.  Create it if it doesn't
if [ ! -d "$LOCALLOGDIR" ]; then
        mkdir -p $LOCALLOGDIR
fi

touch ${REPORTLOGFILE}
chmod a+w ${REPORTLOGFILE}

# Run the docker command
docker run --rm \
        -v ${CONFIGDIR}:/tmp/gracc-osg-reports-config \
        -v ${LOCALLOGDIR}:/tmp/log \
        opensciencegrid/gracc-osg-reports:derek-test osgflockingreport \
        -s "${starttime}" \
        -e "${endtime}" \
        -c /tmp/gracc-osg-reports-config/osg.toml \
        -T /tmp/html_templates/template_flocking.html

echo "END" `date` >> $SCRIPTLOGFILE
exit 0
