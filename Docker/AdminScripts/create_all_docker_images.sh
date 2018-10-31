#!/bin/bash

START=${PWD}
TOPDIR=${START}/..
ROOTDIR=${TOPDIR}/..
OSG_REPORTS_DOCKER_IMG_PREFIX="opensciencegrid/gracc-osg-reports"
SETUP_DOT_PY=${ROOTDIR}/setup.py

REPORTS=`cd ${TOPDIR}; ls -d1 osg*report | cut -f1 -d'/'`

VERSION=`grep -E "version=\'.+\'\,$" ${SETUP_DOT_PY}`  # VERSION will be something like "version='2.0'," without surrounding "
VERSION=${VERSION%\'*}	# Remove trailing quotation, comma
VERSION=${VERSION#*\'}	# Remove everything up until the first quotation

OSG_REPORTS_DOCKER_IMG="${OSG_REPORTS_DOCKER_IMG_PREFIX}:${VERSION}"

DOCKER=`which docker`

if [[ "x$DOCKER" == "x" ]] ; then
	echo "Could not find docker executable.  Exiting."
	exit 1
fi


for REPORT in $REPORTS ; do 
	echo $REPORT
	REPORTDIR=${TOPDIR}/${REPORT}
	WRAPPER=${REPORTDIR}/${REPORT}_run.sh
	TMPWRAPPER=${REPORTDIR}/${REPORT}_run.sh.tmp
	DOCKERFILE=${REPORTDIR}/Dockerfile
	TMPDOCKERFILE=${REPORTDIR}/Dockerfile.tmp
	DOCKER_COMPOSE_FILE=${REPORTDIR}/docker-compose.yml
	REPORT_IMAGE="${OSG_REPORTS_DOCKER_IMG_PREFIX}:${REPORT}_${VERSION}"

	# Update Dockerfile
	echo "Updating Dockerfile for $REPORT"
	NEW_FROM_LINE="FROM ${OSG_REPORTS_DOCKER_IMG}"

	while read line; do 
		if [[ $line == FROM* ]] ; then  
			echo ${NEW_FROM_LINE}
		else 
			echo $line; 
		fi 
	done < $DOCKERFILE > $TMPDOCKERFILE

	mv $TMPDOCKERFILE $DOCKERFILE

	# Build and push Docker Image
	echo "Building new docker image for $REPORT"
	cd $REPORTDIR
	$DOCKER build . -t ${REPORT_IMAGE}

	STATUS=$?
	if [[ $STATUS != 0 ]] ; then 
		echo "Docker build failed for $REPORT_IMAGE.  Exiting"
		exit 1
	fi

	echo "Pushing new docker image for $REPORT"
	cd $REPORTDIR
	$DOCKER push ${REPORT_IMAGE}
	cd $TOPDIR


	# Update Wrapper Script
	echo "Updating wrapper script for $REPORT"
	NEW_WRAPPER_LINE="export VERSIONRELEASE=${VERSION}"

	cat $WRAPPER | sed "s/^export\ VERSIONRELEASE\=.*\$/${NEW_WRAPPER_LINE}/" > $TMPWRAPPER
	mv $TMPWRAPPER $WRAPPER
	chmod 755 $WRAPPER
	
	echo "Git add change for $REPORT"
	git add ${WRAPPER} ${DOCKERFILE}

done

# Git commit
git add ${TOPDIR}/version
MESSAGE="Rebuilt all images using create_all_docker_images.sh with version ${VERSION}."
git commit -m "${MESSAGE}" 
