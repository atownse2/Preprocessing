Run Lobster
```
unset PYTHONPATH
conda activate lobster-with-conda
export PATH="$PATH:/afs/crc.nd.edu/group/ccl/software/x86_64/redhat7/cctools/lobster-171-cd5e3e2c-cvmfs-70dfa0d6/bin"
lobster process processMiniAODwithLobster.py
```
Can I run this on Glados if I do: `export SCRAM_ARCH=slc7_amd64_gcc10` ?

To start a Lobster factory do:

```bash
conda activate lobster-with-conda
work_queue_factory -T condor -C lobster_factory.json -M "lobster_$USER.*" -dall -o /scratch365/atownse2/RSTriPhoton/lobster/factory.debug
```
On CRC the factory command needs to be told to use singularity:
```bash
nohup work_queue_factory -T condor -M "lobster_$USER.*" -d all -o /scratch365/atownse2/RSTriPhoton/lobster/factory.debug -C lobster_factory_CRC.json --wrapper "python /afs/crc.nd.edu/group/ccl/software/runos/runos.py rhel7" --extra-options="--workdir=/disk" --worker-binary=/afs/crc.nd.edu/group/ccl/software/x86_64/redhat7/cctools/$cctools/7.8.1/bin/work_queue_worker >&! /tmp/${USER}_lobster_factory.log &
```

To start lobster do
```bash
lobster process processMiniAODwithLobster.py
```


with nohup:
```bash
nohup work_queue_factory -T condor -C lobster_factory.json -M "lobster_$USER.*" -dall -o /scratch365/atownse2/RSTriPhoton/lobster/factory.debug > /scratch365/atownse2/RSTriPhoton/lobster/factory.log &
```