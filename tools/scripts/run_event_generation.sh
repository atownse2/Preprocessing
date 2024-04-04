#Generates events for a given gridpack (in GENargs)
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=slc7_amd64_gcc10

#### Arguments
tmpdir=$1
releasedir=$2
cfgdir=$3
GENargs=$4

if [ -d $tmpdir ]
then
  echo "Removing existing temporary directory."
  rm -rf $tmpdir
  mkdir $tmpdir
else
  echo "Creating temporary directory"
  mkdir $tmpdir
fi

echo "Starting GEN to MiniAOD steps"

echo "GEN step"
cd $releasedir/CMSSW_10_6_19_patch3/src
eval `scramv1 runtime -sh`
cd $wkdir # Not sure why this is needed
cmsRun $cfgdir/20UL18_wmLHEGEN_cfg.py $GENargs

# Check exit status
if [ $? -ne 0 ]
then
  echo "GEN step failed with exit code $?, exiting."
  exit 1
fi

echo "SIM step"
cd $releasedir/CMSSW_10_6_17_patch1/src
eval `scramv1 runtime -sh`
cmsRun $cfgdir/20UL18_SIM_cfg.py
rm $tmpdir/GEN-0000.root

echo "DIGI step"
cd $releasedir/CMSSW_10_6_17_patch1/src
eval `scramv1 runtime -sh`
cmsRun $cfgdir/20UL18_DIGI_cfg.py
rm $tmpdir/SIM-0000.root

echo "HLT step"
cd $releasedir/CMSSW_10_2_16_UL/src
eval `scramv1 runtime -sh`
cmsRun $cfgdir/20UL18_HLT_cfg.py
rm $tmpdir/DIGI-0000.root

echo "RECO step"
cd $releasedir/CMSSW_10_6_17_patch1/src
eval `scramv1 runtime -sh`
cmsRun $cfgdir/20UL18_RECO_cfg.py
rm $tmpdir/HLT-0000.root

echo "MiniAOD step"
cd $releasedir/CMSSW_10_6_17_patch1/src
eval `scramv1 runtime -sh` 
cmsRun $cfgdir/20UL18_MAOD_cfg.py

echo "Done with GEN to MiniAOD steps"
echo "Output is in $tmpdir"
exit 0