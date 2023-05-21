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
import ants
from ants_run import ants_registration

if '__file__' not in locals():
    __file__ = 'run_bedpostx.py'

script_dir = Path(__file__).resolve().parent
MNI_f = script_dir / 'MNI152_T1_1mm_brain.nii.gz'


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
        'nodif_brain_mask.nii.gz': 'Extract_B0/{}__b0_mask_resampled.nii.gz',
        'T1_brain.nii.gz': 'Register_T1/{}__t1_warped.nii.gz',
        'DTI_AD.nii.gz': 'FW_Corrected_Metrics/{}__fw_corr_ad.nii.gz',
        'DTI_FA.nii.gz': 'FW_Corrected_Metrics/{}__fw_corr_fa.nii.gz',
        'DTI_GA.nii.gz': 'FW_Corrected_Metrics/{}__fw_corr_ga.nii.gz',
        'DTI_MD.nii.gz': 'FW_Corrected_Metrics/{}__fw_corr_md.nii.gz',
        'DTI_RD.nii.gz': 'FW_Corrected_Metrics/{}__fw_corr_rd.nii.gz',
    }

    # Link files
    in_dirs = []
    for src_root in tqdm(
            sub_dirs, desc=f'Copying data for bedpostx input to {work_dir}'):
        sub = src_root.name

        dst_dir = work_dir / sub
        if not dst_dir.is_dir():
            dst_dir.mkdir()

        # Copy files
        for dst_name, src_name in srcfiles.items():
            src_f = src_root / src_name.format(sub)
            if not src_f.is_file() and dst_name in ('bvals', 'bvecs'):
                src_f = src_root / \
                    src_name.format(sub).replace('_Topup', '')

            if not src_f.is_file():
                shutil.rmtree(dst_dir)
                break

            dest_f = dst_dir / dst_name
            if dest_f.is_file() or dest_f.is_symlink():
                dest_f.unlink()

            if dst_name == 'template2orig_0GenericAffine.mat':
                aff_tr = ants.read_transform(src_f)
                ants.write_transform(aff_tr, dest_f)
            else:
                dest_f.symlink_to(os.path.relpath(src_f, dst_dir))

            if '.nii.gz' in dst_name and 'Warp' not in dst_name:
                cmd = f'3drefit -view orig -space ORIG {dest_f}'
                subprocess.check_call(shlex.split(cmd))

        if not dst_dir.is_dir():
            continue

        # Check data
        cmd = f"bedpostx_datacheck {dst_dir}"
        try:
            subprocess.check_call(shlex.split(cmd), stdout=subprocess.PIPE)
        except Exception as e:
            print(e)
            continue

        in_dirs.append(dst_dir)

    return in_dirs


# %% standardize_to_MNI =======================================================
def standardize_to_MNI(bpx_sub_dirs, overwrite=False):

    for subdir in tqdm(bpx_sub_dirs, desc='Standardize to MNI'):
        # Set source files
        sub = subdir.name.replace('.bedpostX', '')
        xfms_dir = (subdir / 'xfms')

        t1_f = subdir.parent / sub / 'T1_brain.nii.gz'
        standard2diff_ANTs_mat = xfms_dir / 'standard2diff_0GenericAffine.mat'
        standard2diff_ANTs_wrp = xfms_dir / 'standard2diff_1Warp.nii.gz'
        diff2standard_ANTs_wrp = xfms_dir / 'standard2diff_1InverseWarp.nii.gz'

        if not standard2diff_ANTs_mat.is_file() or \
                not standard2diff_ANTs_wrp.is_file() or overwrite:
            # Run ANTs registration: template_f -> t1

            _ = ants_registration(t1_f, MNI_f, f"{xfms_dir}/standard2diff_",
                                  verbose=False)

            tx = ants.read_transform(standard2diff_ANTs_mat)
            ants.write_transform(tx, standard2diff_ANTs_mat)

        standard2diff_mat = xfms_dir / 'standard2diff.mat'
        if not standard2diff_mat.is_file() or overwrite:
            cmd = f"c3d_affine_tool -ref {t1_f}"
            cmd += f" -src {MNI_f} -itk {standard2diff_ANTs_mat}"
            cmd += f" -ras2fsl -o {standard2diff_mat}"
            subprocess.check_call(shlex.split(cmd))

        diff2standard_mat = xfms_dir / 'diff2standard.mat'
        if not diff2standard_mat.is_file() or overwrite:
            cmd = f"convert_xfm -omat {diff2standard_mat}"
            cmd += f" -inverse {standard2diff_mat}"
            subprocess.check_call(shlex.split(cmd))

        diff2standard_warp = xfms_dir / 'diff2standard_warp.nii.gz'
        if not diff2standard_warp.is_file() or overwrite:
            cmd = 'wb_command -convert-warpfield'
            cmd += f" -from-itk {diff2standard_ANTs_wrp}"
            cmd += f" -to-fnirt {diff2standard_warp} {t1_f}"
            subprocess.check_call(shlex.split(cmd))

        standard2diff_warp = xfms_dir / 'standard2diff_warp.nii.gz'
        if not standard2diff_warp.is_file() or overwrite:
            cmd = 'wb_command -convert-warpfield'
            cmd += f" -from-itk {standard2diff_ANTs_wrp}"
            cmd += f" -to-fnirt {standard2diff_warp} {t1_f}"
            subprocess.check_call(shlex.split(cmd))

        diff2standard = xfms_dir / 'diff2standard.nii.gz'
        if not diff2standard.is_file() or overwrite:
            cmd = f"convertwarp --ref={MNI_f}"
            cmd += f" --warp1={diff2standard_warp}"
            cmd += f" --postmat={diff2standard_mat}"
            cmd += f" --out={diff2standard}"
            subprocess.check_call(shlex.split(cmd))

        standard2diff = xfms_dir / 'standard2diff.nii.gz'
        if not standard2diff.is_file() or overwrite:
            cmd = f"convertwarp --ref={MNI_f}"
            cmd += f" --premat={standard2diff_mat}"
            cmd += f" --warp1={standard2diff_warp}"
            cmd += f" --out={standard2diff}"
            subprocess.check_call(shlex.split(cmd))


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
