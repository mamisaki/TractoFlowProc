#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: mmisaki@laureateinstitute.org
"""


# %% import ===================================================================
from pathlib import Path
import multiprocessing
from collections import OrderedDict
import time
import sys
import datetime
import os
import subprocess


# %% run_multi ================================================================
def run_multi(job_kwargs, job_func, num_proc=0, no_return=False):
    # --- Initialize ----------------------------------------------------------
    if num_proc is None:
        num_proc = int(multiprocessing.cpu_count())
    elif num_proc == 0:
        num_proc = int(multiprocessing.cpu_count() // 2)
    elif num_proc < 1:
        num_proc = int(multiprocessing.cpu_count() / 2 * num_proc)

    if num_proc > len(job_kwargs):
        num_proc = len(job_kwargs)

    # Create processor pool
    mp_pool = multiprocessing.Pool(processes=num_proc)

    # Initialize result buffer
    proc_ret = OrderedDict()

    # --- Submit jobs ---------------------------------------------------------
    st = time.time()
    print(f"Started at {time.ctime(st)}.")
    sys.stdout.flush()

    num_allJobs = len(job_kwargs)
    for job_i in range(num_allJobs):
        # Submit job
        proc_kwargs = job_kwargs[job_i]
        proc_ret[job_i] = mp_pool.apply_async(job_func, kwds=proc_kwargs)

    print(f"Processing {len(proc_ret)} jobs with {num_proc} processes.")
    sys.stdout.flush()

    # Close processor pool (no more jobs)
    mp_pool.close()

    if not no_return:
        # --- Wait and read the results ---------------------------------------
        missed_jobs = []
        proc_res = [None] * num_allJobs
        for job_i, pr in proc_ret.items():
            if pr is None:
                continue

            if job_i == 0:
                while not pr.ready():
                    pr.wait(1)

                wait_t = (time.time() - st) * 1.5
            elif not pr.ready():
                pr.wait(wait_t)

            if not pr.ready():
                missed_jobs.append(job_i)
                continue

            try:
                assert pr.successful() and pr.get() is not None
                proc_res[job_i] = pr.get()

            except Exception:
                continue

        mp_pool.terminate()

        # --- Recover missed results ------------------------------------------
        if len(missed_jobs):
            # Retry failed jobs
            for job_i in missed_jobs:
                pr = proc_ret[job_i]
                if pr.ready() and pr.successful() and pr.get() is not None:
                    proc_res[job_i] = pr.get()
                else:
                    print(f'Rerun job {job_i}')
                    sys.stdout.flush()
                    proc_kwargs = job_kwargs[job_i]
                    proc_res[job_i] = job_func(**proc_kwargs)

    else:
        # Wait for the jobs finished
        mp_pool.join()
        proc_res = None

    # --- End message ---------------------------------------------------------
    etstr = str(datetime.timedelta(seconds=time.time()-st)).split('.')[0]
    print('done (took %s)' % etstr)
    sys.stdout.flush()

    return proc_res


# %% _exec_cmd_shell ==========================================================
def _exec_cmd_shell(jobcmd, jobname, log):
    ret = []
    try:
        if log:
            log_dir = Path('swarmlog')
            if not log_dir.is_dir():
                log_dir.mkdir()

            # Redirect stdout to file
            stdout_fame = log_dir / f"{jobname}_{os.getpid()}_swarm.o"
            fdsto = open(stdout_fame, 'w')

            # Redirect stderr to file
            stderr_fame = log_dir / f"{jobname}_{os.getpid()}_swarm.e"
            fdste = open(stderr_fame, 'w')

            ret = subprocess.check_call(jobcmd, stdout=fdsto,
                                        stderr=fdste, shell=True,
                                        executable='/bin/bash')
        else:
            ret = subprocess.check_output(jobcmd, shell=True,
                                          executable='/bin/bash')

        return ret

    except Exception as e:
        print(f"Error {jobcmd}: {e}")
        return -1


# %% run_multi_shell ==========================================================
def run_multi_shell(scmds, jobNames=[], Nr_proc=0, log=True):
    # Set jobNames
    if len(jobNames) < len(scmds):
        jobNames += map(str, range(len(jobNames)+1, len(scmds)+1))

    # Set number of proceccors
    if Nr_proc < 0:
        Nr_proc = max(int(multiprocessing.cpu_count()//2)+Nr_proc, 1)
    elif Nr_proc > 0 and Nr_proc < 1:
        Nr_proc = max(int(multiprocessing.cpu_count()//2 * Nr_proc), 1)

    if Nr_proc == 0 or Nr_proc > multiprocessing.cpu_count():
        Nr_proc = int(multiprocessing.cpu_count()//2)

    if len(scmds) < Nr_proc:
        Nr_proc = len(scmds)

    # Create processor pool
    pool = multiprocessing.Pool(processes=Nr_proc)

    # Submit jobs to processor pool
    pret = []
    for jn in range(len(scmds)):
        print(f"Submit job {jobNames[jn]}")
        sys.stdout.flush()
        pret.append(pool.apply_async(_exec_cmd_shell,
                                     (scmds[jn], jobNames[jn], log)))

    # Close processor pool (no more jobs)
    pool.close()

    # Print message
    if len(scmds) == 1:
        print(f"{len(scmds)} job is submitted")
    else:
        print(f"{len(scmds)} jobs are submitted ", end='')
        if Nr_proc == 1:
            print("(Each job is executed sequentially))")
        else:
            print(f"({Nr_proc} jobs are executed in parallel)")

    sys.stdout.flush()

    # Wait for finish
    pool.join()

    ret = []
    for pr in pret:
        ret.append(pr.get())

    return ret
