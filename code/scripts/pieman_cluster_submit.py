#!/usr/bin/python

# create a bunch of job scripts
from config import config
from subprocess import call
import numpy as np
import os
import socket
import getpass
import datetime as dt


# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======

try:
    os.stat(config['resultsdir'])
except:
    os.makedirs(config['resultsdir'])

# each job command should be formatted as a string
job_script = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pieman_cluster.py')


cond_type = ['intact', 'paragraph', 'word', 'rest']

# options for reps: integer
levels =  str('10')

# options for reps: integer
reps =  str('10')

# options for reps: cfuns
cfuns =  [str('isfc'), str('wisfc')]

# options for reps: rfuns
rfuns =  [str('eigenvector_centrality'), str('pagerank_centrality'), str('strength')]
#rfuns =  [str('pagerank_centrality')]

# options for widths: integer
widths = [str(5), str(10), str(20)]

# options for weight functions: laplace, gaussian, mexican hat, delta
weights = ['laplace', 'gaussian', 'delta', 'mexican_hat']


# options for debug: True or False
debug = str('True')

param_grid = [(c, r, wi, we) for c in cfuns for r in rfuns for wi in widths for we in weights]



job_commands = list(np.array([list(map(lambda x: x[0]+" "+str(x[1])+" "+levels+" "+reps+
                                                 " "+e[0]+" "+e[1]+" "+e[2]+" "+e[3]+" "+debug,
                                       zip([job_script]*len(cond_type), cond_type)))
                              for i, e in enumerate(param_grid)]).flat)

# job_names should specify the file name of each script (as a list, of the same length as job_commands)
job_names = list(np.array([list(map(lambda x: os.path.basename(os.path.splitext(x)[0])+'_'+levels+'_'+reps+'_'
                                              +e[0]+'_'+e[1]+'_'+e[2]+'_'+e[3]+'_'+debug+'.sh', cond_type))
                           for i, e in enumerate(param_grid)]).flat)


# ====== MODIFY ONLY THE CODE BETWEEN THESE LINES ======

assert(len(job_commands) == len(job_names))


# job_command is referenced in the run_job.sh script
# noinspection PyBroadException,PyUnusedLocal
def create_job(name, job_command):
    # noinspection PyUnusedLocal,PyShadowingNames
    def create_helper(s, job_command):
        x = [i for i, char in enumerate(s) if char == '<']
        y = [i for i, char in enumerate(s) if char == '>']
        if len(x) == 0:
            return s

        q = ''
        index = 0
        for i in range(len(x)):
            q += s[index:x[i]]
            unpacked = eval(s[x[i]+1:y[i]])
            q += str(unpacked)
            index = y[i]+1
        return q

    # create script directory if it doesn't already exist
    try:
        os.stat(config['scriptdir'])
    except:
        os.makedirs(config['scriptdir'])

    template_fd = open(config['template'], 'r')
    job_fname = os.path.join(config['scriptdir'], name)
    new_fd = open(job_fname, 'w+')

    while True:
        next_line = template_fd.readline()
        if len(next_line) == 0:
            break
        new_fd.writelines(create_helper(next_line, job_command))
    template_fd.close()
    new_fd.close()
    return job_fname


# noinspection PyBroadException
def lock(lockfile):
    try:
        os.stat(lockfile)
        return False
    except:
        fd = open(lockfile, 'w')
        fd.writelines('LOCK CREATE TIME: ' + str(dt.datetime.now()) + '\n')
        fd.writelines('HOST: ' + socket.gethostname() + '\n')
        fd.writelines('USER: ' + getpass.getuser() + '\n')
        fd.writelines('\n-----\nCONFIG\n-----\n')
        for k in config.keys():
            fd.writelines(k.upper() + ': ' + str(config[k]) + '\n')
        fd.close()
        return True


# noinspection PyBroadException
def release(lockfile):
    try:
        os.stat(lockfile)
        os.remove(lockfile)
        return True
    except:
        return False


script_dir = config['scriptdir']
lock_dir = config['lockdir']
lock_dir_exists = False
# noinspection PyBroadException
try:
    os.stat(lock_dir)
    lock_dir_exists = True
except:
    os.makedirs(lock_dir)

# noinspection PyBroadException
try:
    os.stat(config['startdir'])
except:
    os.makedirs(config['startdir'])

locks = list()
for n, c in zip(job_names, job_commands):
    # if the submission script crashes before all jobs are submitted, the lockfile system ensures that only
    # not-yet-submitted jobs will be submitted the next time this script runs
    next_lockfile = os.path.join(lock_dir, n+'.LOCK')
    locks.append(next_lockfile)
    if not os.path.isfile(os.path.join(script_dir, n)):
        if lock(next_lockfile):
            next_job = create_job(n, c)

            if (socket.gethostname() == 'discovery.hpcc.dartmouth.edu') or (socket.gethostname() == 'ndoli.hpcc.dartmouth.edu'):
                submit_command = 'echo "[SUBMITTING JOB: ' + next_job + ']"; qsub'
            else:
                submit_command = 'echo "[RUNNING JOB: ' + next_job + ']"; sh'

            call(submit_command + " " + next_job, shell=True)

# all jobs have been submitted; release all locks
for l in locks:
    release(l)
if not lock_dir_exists:  # remove lock directory if it was created here
    os.rmdir(lock_dir)
