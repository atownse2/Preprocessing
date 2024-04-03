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

tmpdir=/tmp/atownse2_MLNanoAODv9
tmpoutfile=$tmpdir/$filename

if [ ! -d "$tmpdir" ]; then
    echo "Creating tmpdir $tmpdir"
    mkdir $tmpdir
fi

# is isMC == True then use Prod_MLNanoAODv9_mc.py, else use Prod_MLNanoAODv9_data.py
if [ "$isMC" = "True" ]; then
    echo "Running on MC"
    dtag="mc"
else
    echo "Running on Data"
    dtag="data"
fi

filename=$(basename "$outfile")

echo "Running MLNanoAODv9 $dtag production for file $filename"

cd /afs/crc.nd.edu/user/a/atownse2/Public/MLDiphotons/MLNanoAODv9/CMSSW_10_6_19_patch2/src
eval `scramv1 runtime -sh` # cmsenv is an alias not on the workers

cmsRun Prod_MLNanoAODv9_$dtag.py inputFiles=$infiles outputFile=$tmpoutfile maxEvents=$maxEvents
mv $tmpoutfile $outfile
echo "Output written to $outfile"
