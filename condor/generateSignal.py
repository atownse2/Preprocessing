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

def signal_point_tag(signal_point):
    M_BKK = signal_point['M_BKK']
    M_R = signal_point['M_R']
    if M_BKK/int(M_BKK) == 1:
        M_BKK = int(M_BKK)
    if int(M_R) != 0 and M_R/int(M_R) == 1:
        M_R = int(M_R)
    
    tag = f'{signal_tag}_M1-{M_BKK}_R0-{M_R}'.replace('.','p')
    return tag

def m_moe_to_m_m(m_moe):
    '''Converts the m_moe to m_m'''
    M_BKK = m_moe['M_BKK']
    MOE = m_moe['MOE']
    return {'M_BKK': M_BKK, 'M_R': (M_BKK/2)*MOE}


## Gridpacks
def get_gridpack(signal_point, output_base, remake=False, condor=False, test=False):

    gridpackdir = f"{output_base}/gridpacks"
    if not os.path.isdir(gridpackdir):
        os.system(f'mkdir {gridpackdir}')

    fragment = signal_point_tag(signal_point)
    if test: fragment += "_test"

    gridpath = f'{gridpackdir}/{fragment}_slc7_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz'
    if os.path.exists(gridpath):
        if remake:
            os.system(f'rm -rf {gridpath}')
        else:
            return gridpath

    arguments = f"{signal_point['M_BKK']} {signal_point['M_R']} {mgdir} {gridpath}"
    if condor:
        result = jm.submit_condor(run_gridpack, arguments, f'{fragment}_gridpack')
        return None
    else:
        setup.try_command(f"{run_gridpack} {arguments}", fail_message="Failed to generate gridpack")
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
        saveAOD=False,
        saveMiniAODv2=True,
        condor=False,
        remake=False,
        test=False
        ):
    
    print(f"Generating {n_events_total} events for signal point {signal_point}...")

    # Configure paths
    if test:
        output_base += "/test"
    
    dataset = sample_info.Dataset(
        "signal", f"{signal_point_tag(signal_point)}_{year}", output_format,
        storage_base=output_base)
    
    if not test:
        dataset.update_sample_info()

    # Ensure output directories exists
    if not os.path.isdir(dataset.storage_dir):
        os.makedirs(dataset.storage_dir)
    if saveAOD and not os.path.isdir(dataset.storage_dir.replace(output_format, "AOD")):
        os.makedirs(dataset.storage_dir.replace(output_format, "AOD"))
    if saveMiniAODv2 and not os.path.isdir(dataset.storage_dir.replace(output_format, "MiniAODv2")):
        os.makedirs(dataset.storage_dir.replace(output_format, "MiniAODv2"))

    # Generate gridpack
    gridpack_path = get_gridpack(signal_point, output_base, remake=remake_gridpacks, condor=condor, test=test)
    if gridpack_only or gridpack_path is None:
        return

    # Generate events
    n_to_generate = n_events_total
    ibatch = -1
    while n_to_generate > 0:
        ibatch += 1

        outfile = f"{dataset.name}_{ibatch}.root"
        outpath = f"{dataset.storage_dir}/{outfile}"
        if outfile in dataset.files:
            continue

        if n_to_generate < n_events_per_file:
            n = n_to_generate
        else:
            n = n_events_per_file
        
        print(f"Generating {n} events for {dataset.name}...")

        tmpdir = f"/tmp/{USER}_{dataset.name}_{ibatch}"
        GENargs = f"gridpack={gridpack_path} nEvents={n}"

        generate_events = ""
        if remake:
            generate_events += textwrap.dedent(f"""
                if [ -d "{tmpdir}" ]; then
                    rm -rf {tmpdir}
                fi
            """)

        generate_events += f"bash {run_event_generation} {tmpdir} {release_dir} {config_dir} {GENargs}\n"
        generate_events += textwrap.dedent(f"""
            if [ ! -f "{tmpdir}/MiniAODv2.root" ]; then
                echo "MiniAODv2 output file not found, exiting."
                exit 1
            fi
        """)

        if saveAOD:
            generate_events += f"cp {tmpdir}/AOD.root {outpath.replace(output_format, 'AOD')}\n"
        if saveMiniAODv2 or output_format == "MiniAODv2":
            generate_events += f"cp {tmpdir}/MiniAODv2.root {outpath.replace(output_format, 'MiniAODv2')}\n"
        
        if output_format == "MLNanoAODv9":
            generate_events += textwrap.dedent(f"""
                cd {tools_dir}/MLPhotons/CMSSW_10_6_19_patch2/src
                eval `scram runtime -sh`
                cmsRun Prod_MLNanoAODv9_mc.py inputFiles=file:{tmpdir}/MiniAODv2.root outputFile={tmpdir}/MLNanoAODv9.root
                mv {tmpdir}/MLNanoAODv9.root {outpath}
            """)
        elif output_format == "NanoAODv9":
            generate_events += textwrap.dedent(f"""
                cd {release_dir}/CMSSW_10_6_27/src
                eval `scram runtime -sh`
                cd {tmpdir}
                cmsRun {config_dir}/2018_NanoAODv9_cfg.py
                mv {tmpdir}/NanoAODv9.root {outpath}
            """)
        elif output_format == "MiniAODv2":
            pass
        else:
            raise ValueError(f"Output format {output_format} not recognized")

        # Clean up
        generate_events += f"rm -rf {tmpdir}\n"
        generate_events += f"echo 'Done'\n"

        if condor:
            jm.submit_condor(generate_events, "", f'{dataset.name}_{ibatch}')
        else:
            setup.try_command(generate_events)

        n_to_generate -= n

    return

if __name__ == "__main__":

    import preprocessing.setup as setup
    import argparse

    parser = argparse.ArgumentParser(description='Generate MiniAOD signal events')
    parser.add_argument('--n_total_events', '-n', type=int, default=10, help='Number of events to have per mass point.')
    parser.add_argument('--n_events_per_file', '-nf', type=int, default=1000, help='Number of events per file.')
    parser.add_argument('--m_m' , nargs=2, type=float, metavar=('M_BKK', 'M_R'), help='Specify a single point in the mass grid to generate events for.')
    parser.add_argument('--m_moe', nargs=2, type=float, metavar=('M_BKK', 'MOE'), help='Specify a single point in the mass grid to generate events for.')
    parser.add_argument('--mass_grid_version', type=str, default='current', help='Specify the mass grid version to use. Default is current.')
    parser.add_argument('--year', type=str, default='2018', help='Specify the era to use for the fragment. Default is 2018.')
    parser.add_argument('--output_format', '-f', type=str, default='MLNanoAODv9', help='Specify the output format. Default is MLNanoAODv9.')
    parser.add_argument('--output_base', '-o', type=str, default=sample_info.vast_storage, help='Specify the output base directory. Default is vast.')
    parser.add_argument('--condor', '-c', action='store_true', help='Submit jobs to condor.')
    parser.add_argument('--gridpack_only', '-g', action='store_true', help='Only generate gridpacks. Do not generate events.')
    parser.add_argument('--remake_gridpacks', '-r', action='store_true', help='Remake gridpacks even if they already exist.')
    parser.add_argument('--saveAOD', type=bool, default=True, help='Save AOD as well as MiniAOD')
    parser.add_argument('--saveMiniAODv2', type=bool, default=True, help='Save MiniAOD')
    parser.add_argument('--test', '-t', action='store_true', help='Run in test mode generating events for a single point in the mass grid.')

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

    # Generate events
    print("Generating signal events with configuration: ")
    print("Number of total events: ", args.n_total_events)
    print("Output format: ", args.output_format)
    print("Year: ", args.year)
    print("Output base: ", args.output_base)
    print("Save AOD: ", args.saveAOD)
    print("Save MAOD: ", args.saveMAOD)

    for signal_point in mass_grid:
        generate_signal_point(signal_point,
                              args.year,
                              args.output_format,
                              args.n_total_events,
                              n_events_per_file=args.n_events_per_file,
                              output_base=args.output_base,
                              gridpack_only=args.gridpack_only,
                              remake_gridpacks=args.remake_gridpacks,
                              saveAOD=args.saveAOD,
                              saveMiniAODv2=args.saveMiniAODv2,
                              condor=args.condor,
                              test=args.test)
        if args.test:
            break