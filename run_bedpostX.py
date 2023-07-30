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
import sys

import numpy as np
from tqdm import tqdm
import time
import ants
from ants_run import ants_registration

if '__file__' not in locals():
    __file__ = 'run_bedpostx.py'

script_dir = Path(__file__).resolve().parent
MNI_f = script_dir / 'MNI152_T1_1mm_brain.nii.gz'


# %% arrange_input_data =======================================================
def arrange_input_data(subj_root, work_dir, overwrite=False):
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
    sub = subj_root.name

    dst_dir = work_dir / sub
    if not dst_dir.is_dir():
        os.makedirs(dst_dir)

    # Copy files
    for dst_name, src_name in srcfiles.items():
        src_f = subj_root / src_name.format(sub)
        if not src_f.is_file() and dst_name in ('bvals', 'bvecs'):
            src_f = subj_root / \
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
        return -1

    # Check data
    cmd = f"bedpostx_datacheck {dst_dir}"
    try:
        subprocess.check_call(shlex.split(cmd), stdout=subprocess.PIPE)
    except Exception as e:
        print(e)
        return -1

    return 0


# %% standardize_to_MNI =======================================================
def standardize_to_MNI(bpx_sub_dir, overwrite=False):

    print('-' * 80)
    print('--- standardize to MNI ---')
    sys.stdout.flush()

    # Set source files
    sub = bpx_sub_dir.name.replace('.bedpostX', '')
    xfms_dir = (bpx_sub_dir / 'xfms')

    t1_f = bpx_sub_dir.parent / sub / 'T1_brain.nii.gz'
    standard2diff_ANTs_mat = xfms_dir / 'standard2diff_0GenericAffine.mat'
    standard2diff_ANTs_wrp = xfms_dir / 'standard2diff_1Warp.nii.gz'
    diff2standard_ANTs_wrp = xfms_dir / 'standard2diff_1InverseWarp.nii.gz'

    if not standard2diff_ANTs_mat.is_file() or \
            not standard2diff_ANTs_wrp.is_file() or overwrite:
        # Run ANTs registration: template_f -> t1

        ants_registration(t1_f, MNI_f, f"{xfms_dir}/standard2diff_",
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
        prog='run_bedpostx.py',
        description='Run FSL bedpostx to the TractFlow preprocessed DTI files')

    parser.add_argument('results_folder', help='TractFlow results folder')
    parser.add_argument('--gpu', action='store_true', help='Use GPU')
    parser.add_argument('--workplace', help='Local working place')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite')

    args = parser.parse_args()
    results_folder = Path(args.results_folder).resolve()
    assert results_folder.is_dir(), f"No directory at {results_folder}"
    gpu = args.gpu
    workplace = args.workplace
    if workplace is not None:
        workplace = Path(workplace).resolve()
    overwrite = args.overwrite

    '''DEBUG
    results_folder = Path.home() / \
        'MRI/TractFlow_workspace/DTI_AdolescentData/results'
    gpu = True
    workplace = None
    overwrite = False
    '''

    if workplace is None:
        tmp_workplace = True
        loc_work_dir = Path.home() / 'bedpostX_work'
        if loc_work_dir.is_dir():
            shutil.rmtree(loc_work_dir)
    else:
        tmp_workplace = False
        loc_work_dir = workplace

    if loc_work_dir.is_dir():
        shutil.rmtree(loc_work_dir)

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

    # --- Run process ------------------------------------------------------
    for subj_root in tqdm(sub_dirs, desc='Running the bedpostx process'):
        sub = subj_root.name

        # -- Chekc if the job is done --
        results_dir = work_dir / f"{sub}.bedpostX"
        last_f = results_dir / 'mean_fsumsamples.nii.gz'
        if last_f.is_file() and not overwrite:
            continue

        IsRun = work_dir.parent / f"IsRun_bedpostx_{sub}"
        if IsRun.is_file():
            continue

        with open(IsRun, 'w') as fd:
            fd.write(gethostname())
            fd.write(time.ctime())

        try:
            # -- Arrage input data diretory for bedpostx --
            ret = arrange_input_data(subj_root, loc_work_dir,
                                     overwrite=overwrite)
            if ret != 0:
                assert False, f"arrange_input_data for {sub} failed."

            # -- Run bedpostx --
            if gpu:
                cmd = f"bedpostx_gpu {sub}"
            else:
                cmd = f"bedpostx {sub}"
            subprocess.check_call(shlex.split(cmd), cwd=loc_work_dir)

            # -- Standardization to MNI for XTRACT --
            bpx_sub_dir = loc_work_dir / f"{sub}.bedpostX"
            standardize_to_MNI(bpx_sub_dir, overwrite=overwrite)

            # -- Copy back result files --
            cmd = f"rsync -rtuvz --copy-links --include='{sub}*'"
            cmd += f" --include='{sub}*/**' --exclude='*'"
            cmd += f" {loc_work_dir}/ {work_dir}/"
            subprocess.run(shlex.split(cmd))

        except Exception as e:
            print(e)

        finally:
            if (loc_work_dir / sub).is_dir():
                shutil.rmtree(loc_work_dir / sub)

            if IsRun.is_file():
                IsRun.unlink()

    # run standardize_to_MNI if it has not been done.
    for bpx_sub_dir in work_dir.glob('*.bedpostX'):
        wrp_f = bpx_sub_dir / 'xfms' / 'standard2diff.nii.gz'
        if not wrp_f.is_file():
            standardize_to_MNI(bpx_sub_dir, overwrite=overwrite)

    if tmp_workplace and loc_work_dir.is_dir():
        shutil.rmtree(loc_work_dir)
