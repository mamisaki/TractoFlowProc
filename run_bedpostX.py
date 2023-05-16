#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" run bedpostx
https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FDT/UserGuide
"""

# %% import ===================================================================
import argparse
from pathlib import Path
import os
import shlex
import subprocess
import shutil
from socket import gethostname
import numpy as np
from tqdm import tqdm
import time

from mproc import run_multi_shell

if '__file__' not in locals():
    __file__ = 'run_bedpostx.py'

script_dir = Path(__file__).resolve().parent
MNI_f = script_dir / 'MNI152_T1_2mm_brain.nii.gz'


# %% arrange_input_data =======================================================
def arrange_input_data(sub_dirs, work_dir, overwrite=False):
    """
    Arrange input data for bedpostx
    """

    # Set processed files
    srcfiles = {
        'bvals': 'Eddy_Topup/{}__bval_eddy',
        'bvecs': 'Eddy_Topup/{}__dwi_eddy_corrected.bvec',
        'data.nii.gz': 'Compute_FreeWater/{}__dwi_fw_corrected.nii.gz',
        'nodif_brain.nii.gz': 'Extract_B0/{}__b0_resampled.nii.gz',
        'nodif_brain_mask.nii.gz': 'Extract_B0/{}__b0_mask_resampled.nii.gz',
        'T1.nii.gz': 'Resample_T1/{}__t1_resampled.nii.gz',
        'T1_brain.nii.gz': 'Bet_T1/{}__t1_bet.nii.gz'
    }

    # Link files
    in_dirs = []
    for src_root in tqdm(
            sub_dirs, desc=f'Copying data for bedpostx input to {work_dir}'):
        sub = src_root.name

        sub_input = work_dir / sub
        if not sub_input.is_dir():
            sub_input.mkdir()

        # Copy files
        for dst_name, src_name in srcfiles.items():
            src_f = src_root / src_name.format(sub)
            if not src_f.is_file() and dst_name in ('bvals', 'bvecs'):
                src_f = src_root / \
                    src_name.format(sub).replace('_Topup', '')

            if not src_f.is_file():
                shutil.rmtree(sub_input)
                break

            dest_f = sub_input / dst_name
            if dest_f.is_file() or dest_f.is_symlink():
                dest_f.unlink()
            dest_f.symlink_to(os.path.relpath(src_f, sub_input))

        if not sub_input.is_dir():
            continue

        # Check data
        cmd = f"bedpostx_datacheck {sub_input}"
        try:
            subprocess.check_call(shlex.split(cmd), stdout=subprocess.PIPE)
        except Exception as e:
            print(e)
            continue

        in_dirs.append(sub_input)

    return in_dirs


# %% standardize_to_MNI =======================================================
def standardize_to_MNI(bpx_sub_dirs, overwrite=False):

    cmd_lines = {
        '{xfms_dir}/diff2str.mat':
            'flirt -in {nodif_brain} -ref {T1_brain}'
            ' -omat {xfms_dir}/diff2str.mat -searchrx -180 180'
            ' -searchry -180 180 -searchrz -180 180 -dof 6 -cost corratio',
        '{xfms_dir}/str2diff.mat':
            'convert_xfm -omat {xfms_dir}/str2diff.mat'
            ' -inverse {xfms_dir}/diff2str.mat',
        '{xfms_dir}/str2standard.mat':
            'flirt -in {T1_brain} -ref {MNI} -omat {xfms_dir}/str2standard.mat'
            ' -searchrx -180 180 -searchry -180 180 -searchrz -180 180 -dof 12'
            ' -cost corratio',
        '{xfms_dir}/standard2str.mat':
            'convert_xfm -omat {xfms_dir}/standard2str.mat'
            ' -inverse {xfms_dir}/str2standard.mat',
        '{xfms_dir}/diff2standard.mat':
            'convert_xfm -omat {xfms_dir}/diff2standard.mat'
            ' -concat {xfms_dir}/str2standard.mat {xfms_dir}/diff2str.mat',
        '{xfms_dir}/standard2diff.mat':
            'convert_xfm -omat {xfms_dir}/standard2diff.mat'
            ' -inverse {xfms_dir}/diff2standard.mat',
        '{xfms_dir}/str2standard_warp.nii.gz':
            'fnirt --in={T1} --aff={xfms_dir}/str2standard.mat'
            ' --cout={xfms_dir}/str2standard_warp --config=T1_2_MNI152_2mm',
        '{xfms_dir}/standard2str_warp.nii.gz':
            'invwarp -w {xfms_dir}/str2standard_warp'
            ' -o {xfms_dir}/standard2str_warp -r {T1_brain}',
        '{xfms_dir}/diff2standard_warp.nii.gz':
            'convertwarp -o {xfms_dir}/diff2standard_warp -r {MNI}'
            ' -m {xfms_dir}/diff2str.mat -w {xfms_dir}/str2standard_warp',
        '{xfms_dir}/standard2diff_warp.nii.gz':
            'convertwarp -o {xfms_dir}/standard2diff_warp'
            ' -r {nodif_brain_mask} -w {xfms_dir}/standard2str_warp'
            ' --postmat={xfms_dir}/str2diff.mat'
    }

    Cmds = []
    JobNames = []
    for subdir in bpx_sub_dirs:
        # Set source files
        wd = subdir.parent
        sub = subdir.name.replace('.bedpostX', '')
        params = {
            'xfms_dir': (subdir / 'xfms').relative_to(wd),
            'MNI': MNI_f,
            'nodif_brain': Path(sub) / 'nodif_brain.nii.gz',
            'nodif_brain_mask': Path(sub) / 'nodif_brain_mask.nii.gz',
            'T1_brain': Path(sub) / 'T1_brain.nii.gz',
            'T1': Path(sub) / 'T1.nii.gz'
        }

        # Check source files
        srcfs = np.array([wd / ff for ff in params.values()])
        fexist = np.array([ff.is_dir() or ff.is_file() for ff in srcfs])
        f_notfound = srcfs[~fexist]
        if len(f_notfound):
            print("Not found {f_notfound}")
            continue

        cmd_chain = []
        for dst, cmdtmp in cmd_lines.items():
            dst_f = dst.format(**params)
            if (wd / dst_f).is_file() and not overwrite:
                continue

            cmd = cmdtmp.format(**params)
            cmd_chain.append(cmd)

        if len(cmd_chain):
            cmd_chain = [f'cd {wd}'] + cmd_chain
            cmd = ' && '.join(cmd_chain)
            Cmds.append(cmd)
            JobNames.append(f"Stabdadize_{sub}")

    if len(Cmds):
        run_multi_shell(Cmds, JobNames)


# %% __main__ =================================================================
if __name__ == '__main__':
    # Read arguments
    parser = argparse.ArgumentParser(
        prog='run_bedpostx',
        description='Run FSL bedpostx to the TractFlow preprocessed DTI files')

    parser.add_argument('results_folder', help='TractFlow results folder')
    parser.add_argument('--gpu', action='store_true', help='Use GPU')
    parser.add_argument('--stdize', action='store_true',
                        help='Standardize to MNI for XTRACT')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    results_folder = Path(args.results_folder).resolve()
    assert results_folder.is_dir(), f"No directory at {results_folder}"
    gpu = args.gpu
    stdize = args.stdize
    overwrite = args.overwrite

    '''DEBUG
    results_folder = Path.home() / \
        'MRI/TractFlow_workspace/DTI_AdolescentData/results'
    overwrite = False
    '''

    # --- Get input data ------------------------------------------------------
    sub_dirs = [sub_dir for sub_dir in results_folder.glob('*')
                if sub_dir.is_dir() and
                sub_dir.name not in ('Readme', 'Compute_Kernel')]

    work_dir = results_folder.parent / 'FDT'
    if not work_dir.is_dir():
        work_dir.mkdir()

    # Check if the job is done
    done_subj = []
    for sub_dir in sub_dirs:
        sub = sub_dir.name
        results_dir = work_dir / f"{sub}.bedpostX"
        last_f = results_dir / 'mean_fsumsamples.nii.gz'
        if last_f.is_file() and not overwrite:
            done_subj.append(sub_dir)
    sub_dirs = np.setdiff1d(sub_dirs, done_subj)

    # Arrage input data diretory for bedpostx
    input_dirs = arrange_input_data(sub_dirs, work_dir, overwrite=overwrite)

    # --- run bedpostx ----------------------------------------------------
    loc_work_dir = Path.home() / 'bedpostX_work'
    if loc_work_dir.is_dir():
        shutil.rmtree(loc_work_dir)

    if gpu:
        for sub_input_dir in tqdm(input_dirs, desc='bedpostX'):
            sub = sub_input_dir.name
            # Chekc if the job is done.
            results_dir = work_dir / f"{sub}.bedpostX"
            last_f = results_dir / 'mean_fsumsamples.nii.gz'
            if last_f.is_file() and not overwrite:
                continue

            # Chekc if the job is running.
            IsRun = work_dir / f'IsRun_{sub}'
            if IsRun.is_file():
                continue
            with open(IsRun, 'w') as fd:
                print(gethostname(), file=fd)
                print(time.ctime(), file=fd)

            try:
                # Copy data to local
                if not loc_work_dir.is_dir():
                    loc_work_dir.mkdir()

                # FSL imcp command does not work on NFS?
                cmd = "rsync -auvz --copy-links"
                cmd += f" {sub_input_dir} {loc_work_dir}/"
                subprocess.check_call(shlex.split(cmd))

                # Run
                cmd = f"bedpostx_gpu {sub}"
                subprocess.check_call(shlex.split(cmd), cwd=loc_work_dir)

                # Copy results
                loc_res_dir = loc_work_dir / f"{sub}.bedpostX"
                cmd = "rsync -auvz --copy-links"
                cmd += f" {loc_res_dir} {work_dir}/"
                subprocess.check_call(shlex.split(cmd))

                shutil.rmtree(loc_work_dir / sub)
                shutil.rmtree(loc_res_dir)

            except Exception:
                pass

            finally:
                if IsRun.is_file():
                    IsRun.unlink()

    else:
        # Copy data to local
        # (FSL imcp command does not work on NFS?)
        cmd = "rsync -auvz --copy-links --exclude='*.bedpostX'"
        cmd += f" {work_dir}/ {loc_work_dir}/"
        subprocess.check_call(shlex.split(cmd))

        Cmds = []
        JobNames = []
        for sub_input_dir in input_dirs:
            in_dir = loc_work_dir / sub_input_dir.name
            res_dir = loc_work_dir / (sub_input_dir.name + '.bedpostX')
            cmd = f"bedpostx {sub_input_dir}"
            Cmds.append(cmd)
            JobNames.apprnd(f"bedpostx_{sub_input_dir.name}")

        run_multi_shell(Cmds, JobNames)

    # --- Copy data from local ------------------------------------------------
    if loc_work_dir.is_dir():
        cmd = "rsync -auvz --copy-links --include='*.bedpostX'"
        cmd += " --include='*.bedpostX/**' --exclude='*'"
        cmd += f" {loc_work_dir}/ {work_dir}/"
        try:
            subprocess.check_call(shlex.split(cmd))
            shutil.rmtree(loc_work_dir)
        except Exception:
            pass

    # --- Standardization to MNI for XTRACT -----------------------------------
    if stdize:
        bpx_sub_dirs = [sub_dir for sub_dir in work_dir.glob('*.bedpostX')
                        if sub_dir.is_dir()]
        standardize_to_MNI(bpx_sub_dirs, overwrite=overwrite)
