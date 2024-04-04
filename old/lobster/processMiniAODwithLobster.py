
from lobster import cmssw
from lobster.core import AdvancedOptions, Category, Config, Dataset, ParentDataset, StorageConfiguration, Workflow

import yaml

import datetime
version = datetime.datetime.now().strftime('%Y%m%d_%H%M')

dTypes = ['signal']

top_dir = "/afs/crc.nd.edu/user/a/atownse2/Public/RSTriPhoton"

input_format = "MiniAODv2"
output_format = "MLNanoAODv9"

samples_path = '{}/samples.yml'.format(top_dir)
with open(samples_path, 'r') as f:
    samples = yaml.safe_load(f)

datasets = {}
idataset = 0
for dType in dTypes:
    for name, info in samples[dType]['datasets'].items():
        if idataset > 1:
            continue
        info['dType'] = dType
        datasets.update({name: info})
        idataset += 1


storage = StorageConfiguration(
    output=[
        "file:///project01/ndcms/atownse2/RSTriPhoton/test/lobster_" + version,
    ]
)

processing = Category(
    name='processing',
    cores=1,
    runtime=900,
    memory=1000
)

workflows = []
for name, info in datasets.items():
    print("Adding dataset: ", name, " to workflows")
    das_dataset = info[input_format].split(':')[1]

    if info['dType'] == 'data':
        run_config = 'Prod_MLNanoAODv9_data.py'
    else:
        run_config = 'Prod_MLNanoAODv9_mc.py'

    MLNano = Workflow(
        label='{}_{}'.format(name.replace('-','_'), output_format),
        dataset=cmssw.Dataset(
            dataset=das_dataset,
            events_per_task=50000,
            file_based=True,
        ),
        command='cmsRun {}'.format(run_config),
        sandbox=cmssw.Sandbox(release='~/Public/MLDiphotons/MLNanoAODv9/CMSSW_10_6_19_patch2'),
        merge_size='3.5G',
        category=processing,
        outputs=['output.root']
    )
    workflows.append(MLNano)

config = Config(
    workdir='/project01/ndcms/atownse2/RSTriPhoton/lobster/lobster_test_' + version,
    plotdir='~/www/lobster/test_' + version,
    storage=storage,
    workflows=workflows,
    advanced=AdvancedOptions(
        bad_exit_codes=[127, 160],
        log_level=1,
        dashboard=False,
        #wq_port=[9123,9129]
    )
)
