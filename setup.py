import os
import sys

top_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(top_dir)

# Check if config directory exists in parent
config_dir = f"{top_dir}/config"
if not os.path.exists(config_dir):
    # Checkout the config repository
    os.system(f"git clone https://github.com/atownse2/DataConfig.git {config_dir}")

# Initialize tools
tools_dir = f"{top_dir}/tools"
if not os.path.exists(tools_dir):
    os.makedirs(tools_dir)

# Checkout genproductions
genproductions_dir = f"{tools_dir}/genproductions"
if not os.path.exists(genproductions_dir):
    os.system(f"git clone https://github.com/atownse2/genproductions.git {genproductions_dir}")

# Get CMSSW releases
release_dir = f"{top_dir}/tools/releases"
if not os.path.exists(release_dir):
    os.makedirs(release_dir)

os.chdir(release_dir)
os.system(f"./{top_dir}/scripts/setup_cmssw.sh")

# TODO: Add configs too

