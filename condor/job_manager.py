import os
import time

# import htcondor
import signal

import textwrap

# find . -type d -exec fs setacl {} nd_campus rlidw \;

USER=os.environ['USER']
condordir = f'/scratch365/{USER}/RSTriPhoton/condor'

condor_dirs = ['submit', 'log', 'err', 'out']
for d in condor_dirs:
    if not os.path.isdir(f'{condordir}/{d}'):
        os.makedirs(f'{condordir}/{d}')

def submit_condor(executable, job_name, arguments=None):
    '''Submit a job to condor'''
    
    if not os.path.isfile(executable):
        # Create a dummy executable
        exec_file = f'{condordir}/submit/{job_name}.sh'
        with open(f, 'w') as f:
            f.write(f'#!/bin/bash\n{executable}')
        os.system(f'chmod +x {exec_file}')
        executable = exec_file

    if isinstance(arguments, list):
        arg_string = "\n            ".join(arguments)
        submit = textwrap.dedent(
            f'''\
            executable = {executable}
            output = {condordir}/out/{job_name}_$(Process).out
            error = {condordir}/err/{job_name}_$(Process).err
            log = {condordir}/log/{job_name}_$(Process).log
            request_cpus = 1
            request_memory = 128MB
            request_disk = 128MB
            queue arguments from (
                {arg_string}
            )
            ''')
    else:
        submit = textwrap.dedent(
            f'''\
            executable = {executable}
            arguments = {arguments}
            output = {condordir}/out/{job_name}.out
            error = {condordir}/err/{job_name}.err
            log = {condordir}/log/{job_name}.log
            request_cpus = 1
            request_memory = 128MB
            request_disk = 128MB
            queue
            ''')

    submit_file = f'{condordir}/submit/{job_name}.submit'
    with open(submit_file, 'w') as f:
        f.write(submit)
    
    os.system(f'condor_submit {submit_file}')


# condor_status = ['', 'IDLE', 'RUNNING', 'REMOVED', 'COMPLETED', 'HELD', 'TRANSFERRING_OUTPUT', 'SUSPENDED']




# class Job:
#     def __init__(self, executable, arguments, job_name, callback=None):
#         self.executable = executable
#         self.arguments = arguments
#         self.job_name = job_name
#         self.callback = callback
#         self.submissions = 0
#         self.condor = False

#         self.t_start = None
#         self.t_end = None
#         self.completed = False
    
#     @property
#     def status(self):
#         '''Check if the job is completed'''
#         if self.submissions == 0:
#             return "UNSUBMITTED"
#         if not self.condor: # Interactive jobs are always completed or failed
#             if self.submit_result == 0:
#                 return "COMPLETED"
#             else:
#                 return "Failed with exit code: " + str(self.submit_result)

#         # Condor jobs
#         schedd = htcondor.Schedd()
#         job_status = schedd.query(
#             constraint=f'ClusterId == {self.submit_result.cluster()}',
#             projection=['JobStatus']
#         )
#         if not job_status:
#             return "COMPLETED"
#         return condor_status[job_status[0]["JobStatus"]]
    
#     def run(self, condor):
#         '''Run the job'''
#         self.t_start = time.time()

#         if condor:
#             self.condor = True
#             self.submit_result = submit_condor(self.executable, self.arguments, self.job_name)
#         else:
#             self.submit_result = submit_interactive(self.executable, self.arguments)
#             self.t_end = time.time()
#             self.completed = True
        
#         self.submissions += 1

#     def clean_up(self):
#         self.t_end = time.time()
#         self.completed = True
        
#         if self.condor and self.submissions>0:
#             schedd = htcondor.Schedd()
#             schedd.act(htcondor.JobAction.Remove, f'ClusterId == {self.submit_result.cluster()}')

#         if self.callback:
#             self.callback(self.arguments)


# class Manager:
#     def __init__(self, verbose=False, workers_per_cycle=15):
#         self.jobs = []
#         self.verbose = verbose
#         self.t_start = time.time()

#         self.default_sleep_time = 10
#         self.workers_per_cycle = workers_per_cycle

#     def add_job(self, executable, arguments, job_name, callback=None):
#         if self.verbose: 
#             print(f"Adding job with name : {job_name}, executable : {executable}, arguments : {arguments}")
#         self.jobs.append(Job(executable, arguments, job_name, callback=callback))

#     @property
#     def sleep_time(self):
#         return self.default_sleep_time
    
#     def run(self, condor, nworkers=1, test=False):
#         try:
#             self._run(condor, nworkers, test)
#         except KeyboardInterrupt:
#             print("Caught keyboard interrupt, cleaning up")
#             self.remove_jobs()
#             raise KeyboardInterrupt

#     def _run(self, condor, nworkers=1, test=False):
#         '''Run all jobs'''

#         jobs_to_run = self.jobs
#         if test:
#             if condor:
#                 max_jobs = min(2*nworkers, len(jobs_to_run))
#             else:
#                 max_jobs = 1
#             jobs_to_run = jobs_to_run[:max_jobs]

#         print(f"Running {len(jobs_to_run)} jobs with {nworkers} workers")
#         n_completed = 0
#         while len(jobs_to_run) > 0:
#             n_running = 0
#             n_started = 0
#             for job in jobs_to_run[:]:
#                 if n_running >= nworkers: break
#                 if n_started >= self.workers_per_cycle: break

#                 job_status = job.status
#                 if self.verbose: print(f"Job {job.job_name} status: {job_status}")

#                 if job_status == "UNSUBMITTED":
#                     job.run(condor)
#                     n_running += 1
#                     n_started += 1
#                 elif job_status == "COMPLETED":
#                     print(f"Job {job.job_name} completed")
#                     job.clean_up()
#                     jobs_to_run.remove(job)
#                     n_completed += 1
#                 elif job.status == "RUNNING" or job.status == "IDLE":
#                     n_running += 1
#                 else:
#                     print(f"Removing {job.job_name} with status {job_status}")
#                     jobs_to_run.remove(job)
#                     job.clean_up()

#             time.sleep(self.sleep_time)
        
#         print(f"Completed {n_completed} jobs")
#         self.clean_up()

#     def clean_up(self):
#         pass

#     def remove_jobs(self):
#         print("Removing all jobs")
#         for job in self.jobs:
#             schedd = htcondor.Schedd()
#             if job.condor:
#                 print(f"Removing job with name : {job.job_name}")
#                 schedd.act(htcondor.JobAction.Remove, f'ClusterId == {job.submit_result.cluster()}')
        

# def check_condor_dir():
#     if not os.path.isdir(condordir):
#         os.makedirs(condordir)
#         os.makedirs(f'{condordir}/out')
#         os.makedirs(f'{condordir}/err')
#         os.makedirs(f'{condordir}/log')

# def submit_condor(executable, arguments, job_name):
#     '''Submit a job to condor'''
#     check_condor_dir()
#     make_events = htcondor.Submit({
#         "executable": executable,
#         "arguments": arguments,
#         "output": f"{condordir}/out/{job_name}.out",
#         "error" : f"{condordir}/err/{job_name}.err",
#         "log"   : f"{condordir}/log/{job_name}.log",              
#         "request_cpus": "1",
#         "request_memory": "128MB",
#         "request_disk": "128MB",
#     })
#     print(f"Submitting job with name : {job_name}")
#     schedd = htcondor.Schedd()
#     return schedd.submit(make_events)

# def submit_interactive(executable, arguments):
#     command = f'{executable} {arguments}'
#     return os.system(command)