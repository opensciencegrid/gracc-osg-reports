#!/bin/sh

# Wrapper script to run the OSG Flocking report inside a Docker container
# Example:  ./flocking_run.sh weekly


export VERSIONRELEASE=2.0.1
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

function dc_error_handle {
        SHELLERROR=$1
        DCERROR=$2
        ERRMSG=$3
        if [ $SHELLERROR -ne 0 ] || [ $DCERROR -ne 0 ];
        then
                ERRCODE=`expr $SHELLERROR + $DCERROR`
                echo $ERRMSG >> $SCRIPTLOGFILE
                echo "END" `date` >> $SCRIPTLOGFILE
                exit $ERRCODE
        fi
}

function prom_push {
        # Update Prometheus metrics
        export UPDATEPROMDIR=${TOPDIR}/updateinfo

        ${DOCKER_COMPOSE_EXEC} -f ${UPDATEPROMDIR}/docker-compose.yml up -d
        ERR=$?
        dc_EXITCODE=`${DOCKER_COMPOSE_EXEC} -f ${UPDATEPROMDIR}/docker-compose.yml ps -q | xargs docker inspect -f '{{ .State.ExitCode}}'`
        MSG="Error updating Prometheus Metrics"

        dc_error_handle $ERR $dc_EXITCODE "$MSG"

        echo "Updated Prometheus Metrics" >> $SCRIPTLOGFILE
}

# Initialize everything
# Check arguments
if [[ $# -lt 1 || $# -gt 2 ]] || [[ $1 == "-h" ]] || [[ $1 == "--help" ]] ;
then
    usage
fi

# Check for prometheus flag
if [[ $1 == "-p" ]] ;
then
        PUSHPROMMETRICS=1
        echo "Pushing metrics"
        shift
else
        PUSHPROMMETRICS=0
fi

set_dates $1
export endtime=`date +"%F %T"`

# Check to see if logdir exists.  Create it if it doesn't
if [ ! -d "$LOCALLOGDIR" ]; then
        mkdir -p $LOCALLOGDIR
fi

touch ${REPORTLOGFILE}
chmod a+w ${REPORTLOGFILE}

# Find docker-compose
PATH=$PATH:/usr/local/bin
DOCKER_COMPOSE_EXEC=`which docker-compose`

if [[ $? -ne 0 ]]; 
then
        ERRCODE=$?
        echo "Could not find docker-compose.  Exiting"
        exit $ERRCODE 
fi

# Run the report container
echo "START" `date` >> $SCRIPTLOGFILE

${DOCKER_COMPOSE_EXEC} up
ERR=$?
dc_EXITCODE=`${DOCKER_COMPOSE_EXEC} ps -q | xargs docker inspect -f '{{ .State.ExitCode}}'`
MSG="Error sending report. Please investigate"

dc_error_handle $ERR $dc_EXITCODE "$MSG"

echo "Sent report" >> $SCRIPTLOGFILE

if [[ $PUSHPROMMETRICS == 1 ]] ;
then
        prom_push
fi

echo "END" `date` >> $SCRIPTLOGFILE
exit 0
