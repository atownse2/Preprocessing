import os
import sys

top_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(top_dir)

import utils.sample_info as si
import utils.job_manager as jm

# produces = {
#     'FlatAODv3': f'{top_dir}/preprocessing/utils/scripts/run_FlatAOD.sh',
#     'MLNanoAODv9': f'{top_dir}/preprocessing/utils/scripts/run_MLNanoAODv9.sh',
# }

produces = {
    'FlatAODv3':  'scripts/run_FlatAOD.sh',
    'MLNanoAODv9':'scripts/run_MLNanoAODv9.sh',
}

def scheduleDataset(
    manager, input_dataset, output_format,
    maxEvents=-1,
    remake=False,
    verbose=False,
    output_base=si.vast_storage,
    test=False):

    executable = produces[output_format]
    
    output_dataset = si.Dataset(input_dataset.dType, input_dataset.dataset, output_format)
    output_dataset.update_sample_info(output_base, test=test)
    output_dir = os.path.dirname(output_dataset.access.split(':')[1])

    infiles = input_dataset.files
    if input_dataset.dType == 'data': # Only process 10% of the data for now
        infiles = infiles[:int(len(infiles)/10)]
    print(f'Processing {len(infiles)} files for {input_dataset.name}')

    num_files_to_process = 0
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
    
        # Add the job to manager
        job_name = f'{output_dataset.name}_{i}'
        args = f"{infile} {outfile} {maxEvents} {output_dataset.isMC}"
        manager.add_job(
            executable, args, job_name,
            callback=checkOutput)
        num_files_to_process += 1
        if test and num_files_to_process >= 2:
            break
    print(f'Added {num_files_to_process} jobs for {output_dataset.name}')

def checkOutput(arguments, verbose=False):
    import uproot
    infile, outfile, maxEvents, isMC = arguments.split(" ")
    if int(maxEvents) > 0:
        outfile = outfile.replace('.root', f'_numEvent{maxEvents}.root')
    if not os.path.exists(outfile):
        print(f"Output file {outfile} does not exist")
        return
    else:
        try:
            f = uproot.open(outfile)
            num_entries = f['Events'].num_entries
            if verbose: print(f"Output file {outfile} has {num_entries} entries")
        except:
            print(f"Error: File {outfile} could not be opened.")
            os.remove(outfile)
            return

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
        args.output_base = f'{top_dir}/preprocessing/test'


    input_datasets = si.Datasets(dTypes, era, "MiniAODv2", subset=subset)
    print(f'Processing {len(input_datasets)} datasets')
    manager = jm.Manager(verbose=args.verbose)

    for input_dataset in input_datasets:
        scheduleDataset(
            manager, input_dataset, args.output_format,
            maxEvents=args.maxEvents,
            remake=args.remake,
            output_base=args.output_base,
            test=args.test,
            verbose=args.verbose
            )
    
    if not args.print_only:
        manager.run(args.condor, nworkers=args.nworkers, test=args.test)
