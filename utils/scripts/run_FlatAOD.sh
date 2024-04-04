#!/bin/bash
#echo "Starting job on " `date` #Date/time of start of job
#echo "Running on: `uname -a`" #Condor job is running on this node
#echo "System software: `cat /etc/redhat-release`" #Operating System on that node

source /cvmfs/cms.cern.ch/cmsset_default.sh 
export SCRAM_ARCH=slc7_amd64_gcc10

infiles=$1
outfile=$2
maxEvents=$3
isMC=$4

filename=$(basename "$outfile")

echo "Running FlatAOD production for file $filename"

cd /afs/crc.nd.edu/user/a/atownse2/Public/MLDiphotons/FlatAOD/CMSSW_10_6_19_patch2/src
eval `scramv1 runtime -sh` # cmsenv is an alias not on the workers

cd MLDiphotons/MLDiphotons/python
cmsRun Prod_FlatAOD.py inputFiles=$infiles outputFile=$outfile maxEvents=$maxEvents isMC=$isMC
