import sys
import os

import textwrap

preprocessing_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
top_dir = os.path.dirname(preprocessing_dir)
sys.path.append(top_dir)

import job_manager as jm

from data_tools import sample_info
import preprocessing.setup as setup

## Define paths
USER = os.environ['USER']

tools_dir = f"{preprocessing_dir}/tools"
scripts_dir = f"{tools_dir}/scripts"

mgdir = f'{tools_dir}/genproductions/bin/MadGraph5_aMCatNLO/'
run_gridpack = f"{scripts_dir}/run_gridpack.sh"

# For event simulation and reconstruction
release_dir = f"{tools_dir}/releases"
config_dir = f"{tools_dir}/configs"
run_event_generation = f"{scripts_dir}/run_event_generation.sh"

## Signal mass grid and functions
signal_tag = 'BkkToGRadionToGGG'

# Calculate mass grid from list of BKK masses and MOEs
def get_mass_grid(BKKs, MOEs):
    return [{"M_BKK": M_BKK, "M_R": round(MOE*(M_BKK/2), 4)} for M_BKK in BKKs for MOE in MOEs]

mass_grids = {
    'old' : get_mass_grid([180, 250, 500, 1000, 3000], [0.04, 0.02, 0.01, 0.005, 0.0025]),
    'current' : get_mass_grid([180, 250, 500, 1000, 1500, 2000, 2500, 3000], [0.04, 0.02, 0.01, 0.005, 0.0025]),
}

def signal_point_tag(signal_point, decimal=False):
    M_BKK = signal_point['M_BKK']
    M_R = signal_point['M_R']
    if M_BKK/int(M_BKK) == 1:
        M_BKK = int(M_BKK)
    if int(M_R) != 0 and M_R/int(M_R) == 1:
        M_R = int(M_R)
    
    tag = f'{signal_tag}_M1-{M_BKK}_R0-{M_R}'
    if decimal == False:
        tag = tag.replace('.', 'p')

    return tag

def m_moe_to_m_m(m_moe):
    '''Converts the m_moe to m_m'''
    M_BKK = m_moe['M_BKK']
    MOE = m_moe['MOE']
    return {'M_BKK': M_BKK, 'M_R': (M_BKK/2)*MOE}


## Gridpacks
def get_gridpack(signal_point, output_base, remake=False, condor=False):
    '''Generate gridpack for a signal point'''

    gridpackdir = f"{output_base}/gridpacks"
    if not os.path.isdir(gridpackdir):
        os.makedirs(gridpackdir)

    gridpath = f'{gridpackdir}/{signal_point_tag(signal_point)}_slc7_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz'
    if os.path.exists(gridpath) and not remake:
        return gridpath

    fragment = signal_point_tag(signal_point, decimal=True)
    cards_dir = f"cards/production/2017/13TeV/{signal_tag}"
    run_gridpack = textwrap.dedent(
        f"""
        cleanup() {{
            if [ -d {fragment} ]; then
                echo "Cleaning up..."
                rm -rf {fragment}*
                rm -rf {cards_dir}/{fragment}*
            fi
        }}
            
        echo "Generating gridpack for {fragment}"
        cd {mgdir}
        cleanup
        python {cards_dir}/{signal_tag}_M1_R0_gen_card.py {signal_point['M_BKK']} {signal_point['M_R']}
        ./gridpack_generation.sh {fragment} {cards_dir}/{fragment}
        cp {fragment}_slc7_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz {gridpath}
        cleanup
        """)              

    if condor:
        result = jm.submit_condor(run_gridpack, f'{fragment}_gridpack')
        return None
    else:
        setup.try_command(run_gridpack, fail_message="Failed to generate gridpack")
        if not os.path.exists(gridpath):
            print(f"Falied to generate gridpack for {fragment}")
            quit()
        return gridpath

## Event generation
def generate_signal_point(
        signal_point,
        year,
        output_format,
        n_events_total,
        n_events_per_file=1000,
        output_base=sample_info.vast_storage,
        gridpack_only=False,
        remake_gridpacks=False,
        save_additional_formats=[],
        condor=False,
        remake=False,
        test=False,
        no_exec=False
        ):
    
    print(f"Generating {n_events_total} events for signal point {signal_point}...")

    if test:
        output_base += "/test"

    # Set up dataset
    dataset_name = f"{signal_point_tag(signal_point)}_{year}"
    dataset = sample_info.Dataset(
        "signal", dataset_name, output_format,
        storage_base=output_base
        )

    if not test: dataset.update_sample_info()

    # Get gridpack
    gridpack_path = get_gridpack(
        signal_point, output_base,
        remake=remake_gridpacks,
        condor=condor
        )
    
    if gridpack_only or gridpack_path is None:
        return

    # Load production config
    config = setup.get_production_config()
    run = "#!/bin/bash\n"
    run += textwrap.dedent(
        f"""
        source {scripts_dir}/utils.sh
        
        nEvents=$1
        batch=$2

        tmpdir=/tmp/{USER}/{dataset_name}_$batch
        cfgdir={config_dir}
        reldir={release_dir}
        year={year}

        ensure_dir $tmpdir
        echo "Starting event generation for {dataset_name}"
        """)

    # Run event generation steps
    steps = ["wmLHEGEN", "SIM", "DIGI", "HLT", "AOD", "MiniAODv2"]
    if output_format not in steps: steps.append(output_format)
    for step in steps:
        args = ""
        if step == "wmLHEGEN":
            args = f"gridpack={gridpack_path} nEvents=${{nEvents}}"

        step_cfg = config[year][step]
        run += f'run_step {step} {step_cfg["release"]} "{args}" \n'

    # Save outputs
    outpath = f"{dataset.storage_dir}/{dataset.name}_$batch.root"
    formats = [output_format] + save_additional_formats
    for f in formats:
        # Ensure output directory exists
        _outdir = dataset.storage_dir.replace(output_format, f)
        if not os.path.isdir(_outdir):
            os.makedirs(_outdir)

        _out = outpath.replace(output_format, f)
        run += f"cp $tmpdir/{f}.root {_out}\n"

    # Clean up
    run += f"rm -rf $tmpdir\n"
    run += f"echo 'Done'\n"
    
    # Configure arguments
    args = []

    n_to_generate = n_events_total
    ibatch = 0
    while n_to_generate > 0:
        outfile = f"{dataset.name}_{ibatch}.root"
        if outfile in os.listdir(dataset.storage_dir) and not remake:
            ibatch += 1
            continue

        if n_to_generate < n_events_per_file:
            n = n_to_generate
        else:
            n = n_events_per_file
        
        args.append(f"{n} {ibatch}")
        n_to_generate -= n
        ibatch += 1

    # Create executable
    gen_evt = f"{top_dir}/cache/condor/{dataset.name}_generate.sh"
    with open(gen_evt, "w") as f:
        f.write(run)
    os.chmod(gen_evt, 0o755)

    if no_exec:
        print(f"Executable created: {gen_evt}")
        return

    if condor:
        jm.submit_condor(gen_evt, f'{dataset.name}_{ibatch}', arguments=args)
    else:
        for arg in args:
            setup.try_command(f"{gen_evt} {arg}", fail_message="Failed to generate events")
            if test:
                break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate MiniAOD signal events')
    parser.add_argument('--n_total_events', '-n', type=int, default=10, help='Number of events to have per mass point.')
    parser.add_argument('--n_events_per_file', '-nf', type=int, default=1000, help='Number of events per file.')
    parser.add_argument('--m_m' , nargs=2, type=float, metavar=('M_BKK', 'M_R'), help='Specify a single point in the mass grid to generate events for.')
    parser.add_argument('--m_moe', nargs=2, type=float, metavar=('M_BKK', 'MOE'), help='Specify a single point in the mass grid to generate events for.')
    parser.add_argument('--mass_grid_version', type=str, default='current', help='Specify the mass grid version to use. Default is current.')
    parser.add_argument('--year', type=str, default='2018', help='Specify the era to use for the fragment. Default is 2018.')
    parser.add_argument('--output_format', '-f', type=str, default='NanoAODv9', help='Specify the output format. Default is MLNanoAODv9.')
    parser.add_argument('--output_base', '-o', type=str, default=sample_info.vast_storage, help='Specify the output base directory. Default is vast.')
    parser.add_argument('--condor', '-c', action='store_true', help='Submit jobs to condor.')
    parser.add_argument('--gridpack_only', '-g', action='store_true', help='Only generate gridpacks. Do not generate events.')
    parser.add_argument('--remake_gridpacks', '-r', action='store_true', help='Remake gridpacks even if they already exist.')
    parser.add_argument('--saveAOD', action='store_true', help='Save AOD as well as MiniAOD')
    parser.add_argument('--saveMiniAODv2', type=bool, default=True, help='Save MiniAOD')
    parser.add_argument('--test', '-t', action='store_true', help='Run in test mode generating events for a single point in the mass grid.')
    parser.add_argument('--no_exec', action='store_true', help='Do not execute the commands, only create the executable.')

    args = parser.parse_args()

    # Ensure necessary tools and configurations are set up
    setup.ensure_dataTools()
    setup.ensure_genproductions()
    setup.ensure_configs([args.year])
    if args.output_format == 'MLNanoAODv9':
        setup.ensure_MLPhotons()

    # Get mass grid/point
    signal_point = None
    if args.m_moe:
        signal_point = m_moe_to_m_m({'M_BKK': args.m_moe[0], 'MOE': args.m_moe[1]})
    elif args.m_m:
        signal_point = {'M_BKK': args.m_m[0], 'M_R': args.m_m[1]}

    if signal_point is not None:
        mass_grid = [signal_point]
    else:
        mass_grid = mass_grids[args.mass_grid_version]

    if args.test:
        args.n_total_events = 10

    additional_formats = []
    if args.saveAOD:
        additional_formats.append('AOD')
    if args.saveMiniAODv2:
        additional_formats.append('MiniAODv2')

    # Generate events
    print("Generating signal events with configuration: ")
    print("Number of total events: ", args.n_total_events)
    print("Output format: ", args.output_format)
    print("Year: ", args.year)
    print("Output base: ", args.output_base)
    print("Save AOD: ", args.saveAOD)
    print("Save MAOD: ", args.saveMiniAODv2)

    for signal_point in mass_grid:
        generate_signal_point(
            signal_point,
            args.year,
            args.output_format,
            args.n_total_events,
            n_events_per_file=args.n_events_per_file,
            output_base=args.output_base,
            gridpack_only=args.gridpack_only,
            remake_gridpacks=args.remake_gridpacks,
            save_additional_formats=additional_formats,
            condor=args.condor,
            test=args.test,
            no_exec=args.no_exec)
        if args.test:
            break