import os
import sys
import subprocess

import json

preprocessing_dir = os.path.dirname(os.path.abspath(__file__))
top_dir = os.path.dirname(preprocessing_dir)

# Initialize directories
tools_dir = f"{top_dir}/preprocessing/tools"
release_base = f"{tools_dir}/releases"
config_dir = f"{tools_dir}/configs"
for d in [tools_dir, release_base, config_dir]:
    if not os.path.exists(d):
        os.makedirs(d)

def try_command(cmd, fail_message=None, exit=True):
    try:
        output = subprocess.check_call(cmd, shell=True)
        return f"Exit code: {output}"
    except:
        if fail_message:
            print(fail_message)
        else:
            print(f"Failed to run command: {cmd}")

        if exit:
            sys.exit(1)
        else:
            return False

def ensure_dataTools():
    # Check if config directory exists in parent
    _dir = f"{top_dir}/data_tools"
    if not os.path.exists(_dir):
        # Checkout the config repository
        os.system(f"git clone https://github.com/atownse2/DataTools.git {_dir}")

def ensure_genproductions():
    # Checkout genproductions
    print("Setting up genproductions")
    genproductions_dir = f"{tools_dir}/genproductions"
    if not os.path.exists(genproductions_dir):
        os.system(f"git clone https://github.com/atownse2/genproductions.git {genproductions_dir}")

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

def ensure_cmssw(release):
    if not os.path.exists(f"{release_base}/{release}"):
        print(f"Setting up {release}")
        try_command(f"""
            cd {release_base}
            scram p CMSSW {release}
            cd {release}/src
            eval `scram runtime -sh`
            scram b"""
        )

era_map = {
    "2018": "20UL18",
} # For now, will want to standardize this later

def ensure_configs(eras):
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
            ensure_cmssw(release)
            
            # Create config file
            if not "cmsDriver" in prod_config: continue
            config_file = f"{config_dir}/{era}_{prod_name}_cfg.py"
            if not os.path.exists(config_file):
                print(f"Creating config file for {prod_name}")             
                input_prod = prod_config["input"]
                infile = f"{input_prod}-0000.root"
                outfile = f"{prod_name}-0000.root"

                cmsDriver_cmd = prod_config["cmsDriver"]
                cmsDriver_cmd = cmsDriver_cmd.replace("file:step-1.root", f"file:{infile}").replace("step0.root", outfile)
                cmsDriver_cmd += f" --python_filename {config_file}"
                if "--no_exec" not in cmsDriver_cmd: cmsDriver_cmd += " --no_exec"
                try_command(f"""
                    cd {release_base}/{release}/src
                    eval `scram runtime -sh`
                    {cmsDriver_cmd}
                    scram b"""
                )

def ensure_MLPhotons():
    # Checkout MLPhotons
    print("Setting up MLPhotons")
    MLPhotons_dir = f"{tools_dir}/MLPhotons"
    if not os.path.exists(MLPhotons_dir):
        os.makedirs(MLPhotons_dir)
        try_command(f"""
            cd {MLPhotons_dir}
            cmsrel CMSSW_10_6_19_patch2
        """)

        try_command(f"""
            cd {MLPhotons_dir}/CMSSW_10_6_19_patch2/src
            git clone https://github.com/atownse2/MLPhotons.git .
            eval `scram runtime -sh`
            scram b
            """)

if __name__ == "__main__":
    ensure_dataTools()