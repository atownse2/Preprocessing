import sys
import os

import textwrap

top_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(top_dir)

from preprocessing.utils import signal_info as si
from preprocessing.utils import tuple_info as ti
from preprocessing.utils import submit_jobs as sj
from preprocessing.utils import clean_up_files as clean

from data_tools import sample_info
from setup import try_command

# Define paths
USER = os.getenv('USER')
output_base = f"/cms/cephfs/data/users/{USER}/RSTriPhoton"
test_base = f'{top_dir}/test/preprocessing/'
if not os.path.isdir(test_base):
    os.makedirs(test_base)

tools_dir = f"{top_dir}/preprocessing/tools"
script_dir = f"{tools_dir}/scripts"

# For gridpack generation
gridpackdir = f"{output_base}/gridpacks"
if not os.path.isdir(gridpackdir):
    os.makedirs(gridpackdir)

mgdir = f'{tools_dir}/genproductions/bin/MadGraph5_aMCatNLO/'
run_gridpack = f"{scripts_dir}/run_gridpack.sh"

# For event simulation and reconstruction
release_dir = f"{tools_dir}/releases"
config_dir = f"{tools_dir}/configs"
run_event_generation = f"{script_dir}/run_event_generation.sh"

# Gridpacks
def get_gridpack(signal_point, remake=False, condor=False, test=False):

    fragment = si.signal_point_tag(signal_point)
    if test: fragment += "_test"

    gridpath = f'{gridpackdir}/{fragment}_slc7_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz'
    if os.path.exists(gridpath):
        if remake:
            os.system(f'rm -rf {gridpath}')
        else:
            return gridpath

    arguments = f"{signal_point['M_BKK']} {signal_point['M_R']} {mgdir} {gridpath}"
    if condor:
        result = sj.submit_condor(run_gridpack, arguments, f'{fragment}_gridpack')
        return None
    else:
        from setup import try_command
        try_command(f"{run_gridpack} {arguments}", fail_message="Failed to generate gridpack")
        return gridpath

def generate_signal_point(
        signal_point,
        year,
        n_events_total,
        n_events_per_file=1000,
        output_format="MLNanoAODv9",
        gridpack_only=False,
        remake_gridpacks=False,
        saveAOD=False,
        saveMAOD=False,
        condor=False,
        test=False):

    outdir = f"{output_base}/{output_format}"
    if test:
        outdir = f"{test_base}/{output_format}"
    
    fragment = si.signal_point_tag(signal_point)
    dataset = sample_info.Dataset("signal", f"{fragment}_{year}", output_format)
    dataset.update_sample_info(output_base, test=test)

    if saveAOD:
        AOD_dataset = sample_info.Dataset("signal", f"{fragment}_{year}", "AOD")
        AOD_outdir = f"{output_base}/AOD"
    
    if output_format == "MiniAODv2": saveMAOD = True
    if saveMAOD:
        MAOD_dataset = sample_info.Dataset("signal", f"{fragment}_{year}", "MiniAODv2")
        MAOD_outdir = f"{output_base}/MiniAODv2"

    dataset = si.signal_dataset(signal_point, year)
    gridpack_path = get_gridpack(signal_point, remake=remake_gridpacks, batch=batch)

    if gridpack_only or gridpack_path is None:
        return

    # if not test:
    #     cleaner = clean.FileCleaner()
    #     cleaner.clean_up_files('signal', 'MiniAOD', datasets=[dataset])

    #     MiniAOD_info = cleaner.good_files['signal'][dataset]['MiniAOD']

    #     existing_files = MiniAOD_info['files'].keys()
    #     existing_events = MiniAOD_info['n_events']
    # else:
    #     existing_files = []
    #     existing_events = 0

    n_to_generate = n_events_total
    ibatch = -1
    while n_to_generate > 0:
        ibatch += 1

        outfile = f"{dataset.name}_{ibatch}.root"
        if outfile in dataset.files:
            continue

        if n_to_generate < n_events_per_file:
            n = n_to_generate
        else:
            n = n_events_per_file
        
        print(f"Generating {n} events for {dataset}...")

        tmpdir = f"/tmp/{USER}/{dataset.name}_{ibatch}"
        GENargs = f"gridpack={gridpack_path} nEvents={n}"

        generate_events = textwrap.dedent(f"""
            #!/bin/bash
            ./{run_event_generation} {tmpdir} {release_dir} {config_dir} {GENargs}
            """)

        if saveAOD:
            generate_events += f"mv {tmpdir}/AOD-0000.root {AOD_outdir}/{AOD_dataset.name}_{ibatch}.root\n"
        if saveMAOD:
            generate_events += f"cp {tmpdir}/MAOD-0000.root {MAOD_outdir}/{MAOD_dataset.name}_{ibatch}.root\n"
        
        if output_format == "MLNanoAODv9":
            nano_prod = f"{scripts_dir}/run_MLNanoAODv9.sh"
            generate_events += f"./{nano_prod} {tmpdir}/MAOD-0000.root NAOD-0000.root\n -1 True\n"
            generate_events += f"mv {tmpdir}/NAOD-0000.root {outdir}/{outfile}\n"
        elif output_format == "MiniAODv2":
            pass
        else:
            raise ValueError(f"Output format {output_format} not recognized")

        # Clean up
        generate_events += f"rm -rf {tmpdir}\n"
        generate_events += f"echo 'Done'\n"

        if condor:
            sj.submit_condor(generate_events, f'{dataset.name}_{ibatch}', test=test)
        else:
            try_command(generate_events)

        n_to_generate -= n
        if test:
            break

    return

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description='Generate MiniAOD signal events')
    parser.add_argument('--n_total_events', '-n', type=int, default=10, help='Number of events to have per mass point.')
    parser.add_argument('--n_events_per_file', '-nf', type=int, default=1000, help='Number of events per file.')
    parser.add_argument('--m_m' , nargs=2, type=float, metavar=('M_BKK', 'M_R'), help='Specify a single point in the mass grid to generate events for.')
    parser.add_argument('--m_moe', nargs=2, type=float, metavar=('M_BKK', 'MOE'), help='Specify a single point in the mass grid to generate events for.')
    parser.add_argument('--mass_grid_version', '-mgv', type=str, default='new', help='Specify the mass grid version to use. Default is current.')
    parser.add_argument('--year', type=str, default='2018', help='Specify the era to use for the fragment. Default is 2018.')
    parser.add_argument('--batch', '-b', action='store_true', help='Submit jobs to condor.')
    parser.add_argument('--gridpack_only', '-g', action='store_true', help='Only generate gridpacks. Do not generate events.')
    parser.add_argument('--remake_gridpacks', '-r', action='store_true', help='Remake gridpacks even if they already exist.')
    parser.add_argument('--saveAOD', action='store_true', help='Save AOD as well as MiniAOD')
    parser.add_argument('--test', '-t', action='store_true', help='Run in test mode generating events for a single point in the mass grid.')

    args = parser.parse_args()

    signal_point = None
    if args.m_moe:
        signal_point = si.m_moe_to_m_m({'M_BKK': args.m_moe[0], 'MOE': args.m_moe[1]})
    elif args.m_m:
        signal_point = {'M_BKK': args.m_m[0], 'M_R': args.m_m[1]}

    if signal_point is not None:
        mass_grid = [signal_point]
    else:
        mass_grid = si.get_mass_grid(args.mass_grid_version)

    for signal_point in mass_grid:
        generate_signal_point(signal_point,
                              args.year,
                              args.n_total_events,
                              n_events_per_file=args.n_events_per_file,
                              gridpack_only=args.gridpack_only,
                              remake_gridpacks=args.remake_gridpacks,
                              saveAOD=args.saveAOD,
                              batch=args.batch,
                              test=args.test)
        if args.test:
            break