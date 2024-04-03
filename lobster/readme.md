Run Lobster
```
unset PYTHONPATH
conda activate lobster-with-conda
export PATH="$PATH:/afs/crc.nd.edu/group/ccl/software/x86_64/redhat7/cctools/lobster-171-cd5e3e2c-cvmfs-70dfa0d6/bin"
lobster process processMiniAODwithLobster.py
```
Can I run this on Glados if I do: `export SCRAM_ARCH=slc7_amd64_gcc10` ?

To start a Lobster factory do:

```
conda activate lobster-with-conda
work_queue_factory -T condor -C lobster_factory.json -M "lobster_$USER.*" -dall -o /scratch365/atownse2/RSTriPhoton/lobster/factory.debug
```
with nohup:
```
nohup work_queue_factory -T condor -C lobster_factory.json -M "lobster_$USER.*" -dall -o /scratch365/atownse2/RSTriPhoton/lobster/factory.debug > /scratch365/atownse2/RSTriPhoton/lobster/factory.log &
```