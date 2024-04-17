import sys
import os

import json

import textwrap

preprocessing_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
top_dir = os.path.dirname(preprocessing_dir)
sys.path.append(top_dir)

class Produce():
    def __init__(self, input_format, output_format, file_tag, output_base, year='2018'):
        self.input_format = input_format
        self.output_format = output_format
        self.year = year
        
        self.get_config()
        self.init_run()
    
    def get_config(self):
        config_file = f"{preprocessing_dir}/production_config.json"
        with open(config_file, "r") as f:
            self.config = json.load(f)

    def init_run(self):
        self.run = textwrap.dedent(
            f"""
            source /cvmfs/cms.cern.ch/cmsset_default.sh
            export SCRAM_ARCH=slc7_amd64_gcc10

            run_step() {{
                local step=$1
                local release=$2
                local cfg_args=$3

                # If output exists skip (useful for debugging)
                if [ -f "$tmpdir/${{step}}" ]; then
                    echo "${{step}} output file already exists, skipping."
                    return
                fi

                echo "${{step}} step"
                cd $releasedir/${{release}}/src
                eval `scramv1 runtime -sh`
                cd $tmpdir
                cmsRun $cfgdir/20UL18_${{step}}_cfg.py $cfg_args

                if [ ! -f "$tmpdir/${{step}}.root" ]; then
                    echo "${{step}} output file not found, exiting."
                    exit 1
                fi
            }}


            """)
    
    def add_step(self, step, arguments=[], release=None):
        if release is None:
            release = self.config[self.year][step]['release']

        self.run += textwrap.dedent(
            f"""
            if [ -f "$tmpdir/{step}.root" ]; then
                echo "${step} output file already exists, skipping."
                return
            fi

            echo "{step} step"
            cd {self.release_dir}/{release}/src
            eval `scramv1 runtime -sh`
            cd $tmpdir
            cmsRun {self.config_dir}/{self.year}_{step}_cfg.py {" ".join(arguments)}

            if [ ! -f "$tmpdir/${step}.root" ]; then
                echo "${step} output file not found, exiting."
                exit 1
            fi
            """)
                                    
    def add_arguments(self, arguments):
        self.arguments = arguments
        for i, arg in enumerate(arguments):
            self.run += f"{arg}=${i}\n"
    
