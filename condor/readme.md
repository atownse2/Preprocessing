To test signal generation do:
```bash
python generate_signal.py -t
```

This will choose one point in the specified mass grid, generate a gridpack for the process (if not already existing) and process 10 events all the way to the specified output format.

The arguments for this script can be listed with:
```bash
python generate_signal.py -h
```

Notable arguments include:
- `-t` for testing
- `-n` for number of events
- `-f` for output format
- `-o` for output directory (default is Vast)
- `--m_m` for specifying a single BKK and Radion mass
- `--m_moe` for specifying a single BKK mass and Radion mass/energy ratio
- `-c` for submitting to Condor
