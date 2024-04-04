import os
import sys

preprocessing_dir = os.path.dirname(os.path.abspath(__file__))
top_dir = os.path.dirname(preprocessing_dir)

# Check if config directory exists in parent
config_dir = f"{top_dir}/config"
if not os.path.exists(config_dir):
    # Checkout the config repository
    os.system(f"git clone https://github.com/atownse2/DataConfig.git {config_dir}")

# Initialize tools
tools_dir = f"{top_dir}/preprocessing/tools"
if not os.path.exists(tools_dir):
    os.makedirs(tools_dir)

# Checkout genproductions
genproductions_dir = f"{tools_dir}/genproductions"
if not os.path.exists(genproductions_dir):
    os.system(f"git clone https://github.com/atownse2/genproductions.git {genproductions_dir}")

# Set up CMSSW releases and configs
release_dir = f"{tools_dir}/releases"
if not os.path.exists(release_dir):
    os.makedirs(release_dir)

config_dir = f"{tools_dir}/configs"
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

import subprocess
def try_command(cmd, fail_message=None, exit=True):
    try:
        output = subprocess.check_call(cmd, shell=True)
        return f"Exit code: {output}"
    except subprocess.CalledProcessError:
        if fail_message:
            print(fail_message)
        else:
            print(f"Failed to run command: {cmd}")

        if exit:
            sys.exit(1)
        else:
            return False

def proxy_init():
    # Initialize proxy
    print("Check if proxy exists")
    proxy_exists = try_command("voms-proxy-info", exit=False, fail_message="No valid proxy found")
    if not proxy_exists:
        print("Initialize proxy")
        try_command(
            "voms-proxy-init -voms cms",
            "Failed to initialize proxy \n" +
            "For help see: https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookStartingGrid#ObtainingCert"
        )

def setup_prod(eras):
    import json

    proxy_init()

    config_file = f"{preprocessing_dir}/production_config.json"
    with open(config_file, "r") as f:
        config = json.load(f)

    for era in eras:
        if era not in config:
            print(f"No configuration found for {era}")
            continue

        for prod_name, prod_config in config[era].items():

            # Set up CMSSW release
            release = prod_config["release"]
            if not os.path.exists(f"{release_dir}/{release}"):
                print(f"Setting up {release}")
                try_command(f"""
                    cd {release_dir}
                    scram p CMSSW {release}
                    cd {release}/src
                    eval `scram runtime -sh`
                    scram b"""
                )
            
            # Create config file
            if not "cmsDriver" in prod_config: continue
            config_file = f"{config_dir}/{era}_{prod_name}_cfg.py"
            if not os.path.exists(config_file):
                print(f"Creating config file for {prod_name}")             
                input_prod = prod_config["input"]
                infile = f"{input_prod}-0000.root"
                outfile = f"{prod_name}-0000.root"

                cmsDriver_cmd = prod_config["cmsDriver"]
                cmsDriver_cmd = cmsDriver_cmd.replace("file:step-1.root", f"file:{infile}").replace("step-0.root", outfile)
                cmsDriver_cmd += f" --python_filename {config_file}"
                if "--no_exec" not in cmsDriver_cmd: cmsDriver_cmd += " --no_exec"
                try_command(f"""
                    cd {release_dir}/{release}/src
                    eval `scram runtime -sh`
                    {cmsDriver_cmd}
                    scram b"""
                )

eras = ["20UL18"]
setup_prod(eras)



