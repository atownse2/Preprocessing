#Generates events for a given gridpack (in GENargs)
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=slc7_amd64_gcc10

#### Arguments
tmpdir=$1
releasedir=$2
cfgdir=$3
GENargs=$4

if [ ! -d $tmpdir ]; then
  echo "Creating temporary directory"
  mkdir $tmpdir
fi

run_step() {
  local step=$1
  local release=$2
  local cfg_args=$3

  # If output exists skip (useful for debugging)
  if [ -f "$tmpdir/${step}-0000.root" ]; then
    echo "${step} output file already exists, skipping."
    return
  fi

  echo "${step} step"
  cd $releasedir/${release}/src
  eval `scramv1 runtime -sh`
  cd $tmpdir
  cmsRun $cfgdir/20UL18_${step}_cfg.py $cfg_args

  if [ ! -f "$tmpdir/${step}-0000.root" ]; then
    echo "${step} output file not found, exiting."
    exit 1
  fi
}

echo "Starting GEN to MiniAOD steps"

run_step "wmLHEGEN" "CMSSW_10_6_17_patch1" $GENargs
run_step "SIM" "CMSSW_10_6_17_patch1"
run_step "DIGI" "CMSSW_10_6_17_patch1"
run_step "HLT" "CMSSW_10_2_16_UL"
run_step "RECO" "CMSSW_10_6_17_patch1"
run_step "MAODv2" "CMSSW_10_6_20"

echo "Done with GEN to MiniAOD steps"
echo "Output is in $tmpdir, you need to do some cleanup..."
exit 0