source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=slc7_amd64_gcc10

ensure_dir() {
  local dir=$1
  if [ ! -d "$dir" ]; then
    echo "Creating directory $dir"
    mkdir -p $dir
  fi
}

run_step() {
  local step=$1
  local release=$2
  local cfg_args=$3

  # If output exists skip (useful for debugging)
  if [ -f "$tmpdir/${step}.root" ]; then
    echo "${step} output file already exists, skipping."
    return
  fi

  echo "${step} step"
  cd $reldir/${release}/src
  eval `scramv1 runtime -sh`
  cd $tmpdir
  cmsRun $cfgdir/${year}_${step}_cfg.py $cfg_args

  if [ ! -f "$tmpdir/${step}.root" ]; then
    echo "${step} output file not found, exiting."
    exit 1
  fi
}