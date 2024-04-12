To set up standalone do
```bash
# Create a parent directory
mkdir RSTriphoton
cd RSTriphoton

# Clone the repository to preprocessing
git clone https://github.com/atownse2/Preprocessing.git preprocessing

# Setup data_tools
python3 preprocessing/setup.py
```

Scripts for generating signal and processing MiniAODv2 with HTCondor are located in `preprocessing/condor` with a `readme.md` for instructions on how to run.

Note: You need to be on earth to run these scripts without condor/lobster (lobster not working currently).