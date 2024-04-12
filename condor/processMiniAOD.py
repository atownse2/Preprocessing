import os
import sys

top_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(top_dir)

import data_tools.sample_info as si
import preprocessing.utils.job_manager as jm

from setup import try_command

USER = os.environ['USER']

cache_dir = f"{top_dir}/cache"

produces = {
    'FlatAODv3': f'{top_dir}/preprocessing/tools/scripts/run_FlatAOD.sh',
    'MLNanoAODv9': f'{top_dir}/preprocessing/tools/scripts/run_MLNanoAODv9.sh',
}

releases = {
    'FlatAODv3': '/afs/crc.nd.edu/user/a/atownse2/Public/MLDiphotons/FlatAOD/CMSSW_10_6_19_patch2/src',
    'MLNanoAODv9': '/afs/crc.nd.edu/user/a/atownse2/Public/MLDiphotons/MLNanoAODv9/CMSSW_10_6_19_patch2/src'
}

configs = {
    'FlatAODv3': '/afs/crc.nd.edu/user/a/atownse2/Public/MLDiphotons/FlatAOD/CMSSW_10_6_19_patch2/src/MLPhotons/MLPhotons/python/Prod_FlatAOD.py',
    'MLNanoAODv9': '/afs/crc.nd.edu/user/a/atownse2/Public/MLDiphotons/MLNanoAODv9/CMSSW_10_6_19_patch2/src/Prod_MLNanoAODv9_TAG.py'
}

# produces = {
#     'FlatAODv3':  'scripts/run_FlatAOD.sh',
#     'MLNanoAODv9':'scripts/run_MLNanoAODv9.sh',
# }

import textwrap

def run_script(output_format, isMC, job_name):
    
    tag = 'mc' if isMC else 'data'

    release_dir = releases[output_format]
    config_file = configs[output_format]
    if output_format == 'MLNanoAODv9':
        config_file = config_file.replace('TAG', tag)

    script = textwrap.dedent(f"""
        #!/bin/bash
        #echo "Starting job on " `date` #Date/time of start of job
        #echo "Running on: `uname -a`" #Condor job is running on this node
        #echo "System software: `cat /etc/redhat-release`" #Operating System on that node

        infiles=$1
        outpath=$2
        maxEvents=$3

        source /cvmfs/cms.cern.ch/cmsset_default.sh 
        export SCRAM_ARCH=slc7_amd64_gcc10

        tmpdir=/tmp/{USER}-{job_name}
        mkdir -p $tmpdir

        outfile=$(basename $outpath)
        tmpoutfile=$tmpdir/$outfile

        cd {release_dir}
        eval `scramv1 runtime -sh` # cmsenv is an alias not on the workers
        cmsRun {config_file} inputFiles=$infiles outputFile=$tmpoutfile maxEvents=$maxEvents

        if [ $maxEvents -lt 0 ]; then
            mv $tmpoutfile $outpath
        else
            tmpoutfile=$tmpdir/${{outfile%.*}}_numEvent${{maxEvents}}.${{outfile##*.}}
            mv $tmpoutfile $outpath
        fi

        echo "Finished job on " `date`
        echo "Output file: $outpath"
        echo "Cleaning up"
        rm -rf $tmpdir
        """)

    a_executable = f"{cache_dir}/executables/{job_name}.sh"
    if not os.path.exists(os.path.dirname(a_executable)):
        os.makedirs(os.path.dirname(a_executable))
    with open(a_executable, 'w') as f:
        f.write(script)
    try_command(f"chmod +x {a_executable}")

    return a_executable

condordir = f'/scratch365/{USER}/RSTriPhoton/condor'
def submit_script(output_format, isMC, args, job_name, print_only=False):
    '''Submit a job to condor'''
    
    # Create the executable
    a_executable = run_script(output_format, isMC, job_name)

    # Format the arguments for condor
    arg_string = ""
    for cfg in args:
        arg_string += f"{cfg['batch']}, {cfg['inFiles']} {cfg['outpath']} {cfg['maxEvents']}"
        if cfg != args[-1]:
            arg_string += "\n            "
        
        # Remove log files
        os.system(f'rm -rf {condordir}/out/{job_name}_{cfg["batch"]}.out')
        os.system(f'rm -rf {condordir}/err/{job_name}_{cfg["batch"]}.err')
        os.system(f'rm -rf {condordir}/log/{job_name}_{cfg["batch"]}.log')

    submit = textwrap.dedent(
        f'''\
        executable = {a_executable}
        output = {condordir}/out/{job_name}_$(batch).out
        error = {condordir}/err/{job_name}_$(batch).err
        log = {condordir}/log/{job_name}_$(batch).log
        request_cpus = 1
        request_memory = 128MB
        request_disk = 128MB
        queue batch, arguments from (
            {arg_string}
        )
        ''')
    
    submit_file = f'{cache_dir}/submit/{job_name}.submit'
    if not os.path.exists(os.path.dirname(submit_file)):
        os.makedirs(os.path.dirname(submit_file))
    with open(submit_file, 'w') as f:
        f.write(submit)
    
    command = f"batch-name: {job_name}, condor_submit file: {submit_file}"
    if not print_only:
        os.system(command)
    else:
        print(f"Command: {command}")

def scheduleDataset(
    input_dataset, output_format,
    maxEvents=-1,
    remake=False,
    verbose=False,
    output_base=si.vast_storage,
    condor=False,
    test=False,
    print_only=False):

    executable = produces[output_format]
    
    output_dataset = si.Dataset(input_dataset.dType, input_dataset.dataset, output_format)
    output_dataset.update_sample_info(output_base, test=test)
    output_dir = os.path.dirname(output_dataset.access.split(':')[1])
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    infiles = input_dataset.files
    if input_dataset.dType == 'data': # Only process 10% of the data for now
        infiles = infiles[:int(len(infiles)/10)]
    if test:
        infiles = infiles[:2]

    num_files_to_process = 0
    args = []
    for i, infile in enumerate(infiles):
        outfile = f"{output_dir}/{output_dataset.name}_{i}.root"

        # Skip if the file already exists
        if not remake:
            if maxEvents > 0:
                look_for = outfile.replace('.root', f'_numEvent{maxEvents}.root') 
            else:
                look_for = outfile

            if os.path.exists(look_for):
                continue
    
        # Add the job configuration to the list
        cfg = {
            'batch': i,
            'inFiles': infile,
            'outpath': outfile,
            'maxEvents': maxEvents,
        }
        args.append(cfg)
        num_files_to_process += 1

    if num_files_to_process < 1:
        print(f'All files already processed for {output_dataset.name}')
        return
        
    job_name = input_dataset.name
    if test: job_name += '_test'

    print(f'Processing {num_files_to_process} files out of {len(input_dataset.files)} for {output_dataset.name}')

    if condor: 
        submit_script(output_format, input_dataset.isMC, args, job_name, print_only=print_only)
    else:
        for cfg in args:
            a_executable = run_script(output_format, input_dataset.isMC, job_name)
            try_command(f"{a_executable} {cfg['inFiles']} {cfg['outpath']} {cfg['maxEvents']}")
            

# def checkOutput(arguments, verbose=False):
#     import uproot
#     infile, outfile, maxEvents, isMC = arguments.split(" ")
#     if int(maxEvents) > 0:
#         outfile = outfile.replace('.root', f'_numEvent{maxEvents}.root')
#     if not os.path.exists(outfile):
#         print(f"Output file {outfile} does not exist")
#         return
#     else:
#         try:
#             f = uproot.open(outfile)
#             num_entries = f['Events'].num_entries
#             if verbose: print(f"Output file {outfile} has {num_entries} entries")
#         except:
#             print(f"Error: File {outfile} could not be opened.")
#             os.remove(outfile)
#             return

if __name__ == '__main__':
    import argparse

    ## Inputs
    parser = argparse.ArgumentParser('Process n_files_per_dataset files from every dataset in a dType, or a single dataset if specified.')
    parser.add_argument('dTypes', type=str, help='Data types to process joined by ","')
    parser.add_argument('--era', type=str, default='2018', help='Specify the era to process, default is 2018')
    parser.add_argument('--subset', '-d', type=str, default=None, help='Subset of datasets to process joined by ","')
    parser.add_argument('--condor', '-c', action='store_true', help='Submit jobs to condor')
    parser.add_argument('--nworkers', '-w', type=int, default=1, help='Number of workers to use')
    parser.add_argument('--output_format', '-o', type=str, default='MLNanoAODv9', help='Output format')
    parser.add_argument('--output_base', '-b', type=str, default=si.vast_storage, help='Output base directory')
    parser.add_argument('--maxEvents', '-m', type=int, default=-1, help='Maximum number of events to process')
    parser.add_argument('--remake', '-r', action='store_true', help='Remake existing files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print verbose output')
    parser.add_argument('--test', '-t', action='store_true', help='Test the script, only process <nworkers> files')
    parser.add_argument('--print_only', '-p', action='store_true', help='Print the commands without running them')

    args = parser.parse_args()

    dTypes = args.dTypes.split(',')
    era = args.era

    subset = args.subset
    if subset is not None:
        subset = subset.split(',')

    if args.test:
        print('Running in test mode')
        args.maxEvents = 10
        args.output_base = "/project01/ndcms/atownse2/RSTriPhoton/test"


    input_datasets = si.Datasets(dTypes, era, "MiniAODv2", subset=subset)
    print(f'Processing {len(input_datasets)} datasets')

    for input_dataset in input_datasets:
        scheduleDataset(
            input_dataset, args.output_format,
            maxEvents=args.maxEvents,
            remake=args.remake,
            output_base=args.output_base,
            condor=args.condor,
            test=args.test,
            print_only=args.print_only,
            verbose=args.verbose
            )
        if args.test:
            break

