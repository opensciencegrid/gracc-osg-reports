#!/bin/sh

# Wrapper script to run the OSG Probe report inside a Docker container

export TOPDIR=/opt/gracc-osg-reports
export LOCALLOGDIR=${TOPDIR}/log
export SCRIPTLOGFILE=${LOCALLOGDIR}/probereport_run.log
export REPORTLOGFILE=${LOCALLOGDIR}/osgprobereport.log
export CONFIGDIR=${TOPDIR}/config

function usage {
    echo "Usage:    ./probereport_run.sh [-p]"
    echo ""
    exit
}

# Initialize everything
# Check arguments
if [[ $# -gt 1 ]] || [[ $1 == "-h" ]] || [[ $1 == "--help" ]] ;
then
    usage
fi

# Check to see if logdir exists.  Create it if it doesn't
if [ ! -d "$LOCALLOGDIR" ]; then
        mkdir -p $LOCALLOGDIR
fi

touch ${REPORTLOGFILE}
chmod a+w ${REPORTLOGFILE}

# Run the report container
echo "START" `date` >> $SCRIPTLOGFILE

docker run \
        -v ${CONFIGDIR}:/tmp/gracc-osg-reports-config \
        -v ${LOCALLOGDIR}:/tmp/log
        opensciencegrid/gracc-osg-reports:latest osgpersitereport \
        -c /tmp/gracc-osg-reports-config/osg.toml \
        -S /tmp/log/probereporthistory.log

echo "Sent report" >> $SCRIPTLOGFILE

echo "END" `date` >> $SCRIPTLOGFILE
exit 0
