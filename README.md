# README
See the [INSTALL](INSTALL.md) file to set up the environment. These instructions assume that the TractFlowProc scripts are stored in ~/TractFlowProc and the workspace is ~/TractFlow_workspace.

***The command must be run in the 'tractflow' conda environment. See [INSTALL](INSTALL.md) to set up the environment.***

## 1. Prepare data files
Create an input data folder (e.g., ~/TractFlow_workspace/input).  
Place the data file for each subject (e.g. S1, S2, ...) into the input folder.  
The data structure is as follows  
input  
&nbsp;&nbsp;├── S1  
&nbsp;&nbsp;│ ├── dwi.nii.gz  
&nbsp;&nbsp;│ ├── bval  
&nbsp;&nbsp;│ ├── bvec  
&nbsp;&nbsp;│ ├── rev_b0.nii.gz (optional)  
&nbsp;&nbsp;│ ├── aparc+aseg.nii.gz (optional)  
&nbsp;&nbsp;│ ├── wmparc.nii.gz (optional)  
&nbsp;&nbsp;│ └── t1.nii.gz  
&nbsp;&nbsp;└── S2  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── dwi.nii.gz  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── bval  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── bvec  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── rev_b0.nii.gz (optional)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── aparc+aseg.nii.gz (optional)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── wmparc.nii.gz (optional)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── t1.nii.gz  

dwi.nii.gz: DWI image file.  
bval, bvec: b-value and b-vector files. b-vector must be of unit length.  
t1.nii.gz: T1 anatomical image file.  
rev_b0.nii.gz (optional): Reverse phase encoding of b0 DWI images.  
aparc+aseg.nii.gz (optional): FreeSurfer aparc+aseg image file.  
wmparc.nii.gz (optional): FreeSurfer wmparc image file.  

## 2. Run FreeSurfer (optional)
**You can skip this step.** Only if the T1 image contrast is not good enough to segment tissue and you need to use Atlas Based Segmentation (ABS) in Tractflow should you perform this process.  

The fiber tracking process uses the white matter (WM), gray matter (GM), and cerebrospinal fluid (CSF) masks to define the tracking area and seeding mask. These masks are extracted by default with the 'fast' command in FSL for t1.nii.gz, but you can also use a FreeSurfer segmentation, i.e. aparc+aseg and wmparc, with the --ABS option in tractflow.  

The script run_FreeSurfer.py processes t1.nii.gz in the input folder to create aparc+aseg.nii.gz and wmparc.nii.gz.  

#### Usage
run_FreeSurfer.py [-h] [--overwrite] input_folder  
e.g,  
```
cd ~/TractFlowProc
nohup ./run_FreeSurfer.py ~/TractFlow_workspace/input > nohup_FS.out &
```
The script will skip subjects with 'aparc+aseg.mgz' and 'wmparc.nii.gz' files unless the --overwrite option is set.  

The process will take a very long time (almost half a day for one subject, depending on the CPU). Multiple subjects can be processed in parallel, and the number of simultaneous processes is calculated as '(number of CPU cores)//2'.  
The files processed by FreeSurfer are stored in the folder ~/TractFlow_workspace/freesurfer.  

The files aparc+aseg.nii.gz and wmparc.nii.gz of each subject are created in the input folder.

## 3. TractoFlow pipeline
The run_TractFlow.pyscript runs the TractFlow pipeline.

#### Usage
run_TractFlow.py [-h] [--fully_reproducible] [--ABS] [--workplace WORKPLACE] [--num_proc NUM_PROC] [--processes PROCESSES] [--overwrite] input
e.g,  
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_TractFlow.py ~/TractFlow_workspace/input --with_docker --fully_reproducible > nohup_tf.out &
```
* Add '--ABS' option to run TractoFlow-ABS (See [2](#2-run-freesurfer-optional)). 

The command returns immediately and the process runs in the background.  
The process takes a long time: >10h for one subject. Multiple subjects can be processed in parallel, depending on the number of CPU cores.  

The script will skip subjects with a 'PFT_Tracking/*__pft_tracking_prob_wm_seed_0.trk' file in the results directory unless the --overwrite option is set.  

The script copies the input files to ~/tractflow_work, processes them in that directory, and rsyncs the results to the original location (some processes fail on a network drive).  

See https://tractoflow-documentation.readthedocs.io/en/latest/pipeline/steps.html for processing details.  

## 4. freewater_flow pipeline
The script run_FreewaterFlow.py runs the FreeWater pipeline, including FW-corrected DTI metrics estimation.  
https://github.com/scilus/freewater_flow

#### Usage
run_FreewaterFlow.py [-h] [--workplace WORKPLACE] [--num_proc NUM_PROC] [--overwrite] tf_results_folder  
e.g.,  
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_FreewaterFlow.py ~/TractFlow_workspace/results > nohup_fwf.out &
```
The command returns immediately and the process runs in the background.  
The process takes a very long time: > 3h for one subject. Multiple subjects are processed in parallel as far as memory allows (20G/subject required).  

The script will skip subjects with a 'FW_Corrected_Metrics/*__fw_corr_tensor.nii.gz' file in the results directory unless the --overwrite option is set.  

The result files are saved in the 'FW_Corrected_Metrics' folder in the results/*subject* folder.  

## 5. Standardize DTI and fODF metrics
The run_warp2template.py script normalizes the DTI and fDOF metric files to the MNI152 template space.  

#### Usage
run_warp2template.py [-h] [--overwrite] results_folder
e.g,  
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_warp2template.py ~/TractFlow_workspace/results > nohup_wrp.out &
```

The result files are saved in the 'Standardize_*' folders in the results/*subject* folder.  

The script will skip subjects with standardized DTI and fDOF metric files in the results directory unless the --overwrite option is set.  

## 6. FDT processing
Perform probabilistic fiber tracking analysis with [FSL FDT tools](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FDT/UserGuide), including [BEDPOSTX](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FDT/UserGuide#BEDPOSTX), [XTRACT](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/XTRACT), and [PROBTRACKX](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FDT/UserGuide#PROBTRACKX_-_probabilistic_tracking_with_crossing_fibres). 

### BEDPOSTX
The run_bedpostx.py runs the bedpostx command on the freewater corrected DTI images.  

#### Usage
run_bedpostx.py [-h] [--gpu] [--overwrite] results_folder
e.g,  
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_bedpostX.py --gpu ~/TractFlow_workspace/results > nohup_bpx.out &
```
The results will be stored in '~/TractFlow_workspace/FDT/*subject*.bedpostX' folder.  

The script will skip subjects with the file '{sub}.bedpostX/mean_fsumsamples.nii.gz" in the FDT results directory unless the --overwrite option is set.  

### XTRACT
[XTRACT](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/XTRACT) (cross-species tractography) can be used to automatically extract a set of carefully dissected tracts in humans (neonates and adults) and macaques. It can also be used to define one's own tractography protocols where all the user needs to do is to define a set of masks in standard space (e.g. MNI152).  

The run_XTRACT.py runs the bedpostx command on the freewater corrected DTI images.  

#### Usage
run_XTRACT.py [-h] [--gpu] [--overwrite] FDT_folder  
e.g,  
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_XTRACT.py --gpu ~/TractFlow_workspace/FDT > nohup_xtract.out &
```

### PROBTRACKX
[PROBTRACKX](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FDT/UserGuide#PROBTRACKX_-_probabilistic_tracking_with_crossing_fibres) produces sample streamlines, by starting from some seed and then iterate between (1) drawing an orientation from the voxel-wise bedpostX distributions, (2) taking a step in this direction, and (3) checking for any termination criteria. These sample streamlines can then be used to build up a histogram of how many streamlines visited each voxel or the number of streamlines connecting specific brain regions. This streamline distribution can be thought of as the posterior distribution on the streamline location or the connectivity distribution.  

The run_PROBTACKX.py script runs 'probtrackx2' to generate a streamline distribution from a seed mask. The seed mask should be defined in the template (MNI152) space. Multiple seeds can be implemented in one file by using different values. The mask filename should be specified with the '--seed_template' option.   

Seed names for each index value can be provided with a csv file of the same name with the suffix '.csv'. For example, the name file for the 'SeedROI.nii.gz' is 'SeedROI.csv'. The csv file must be located in the same directory as the mask image file.  

A sample seed ROI image and its name file are provided as SeedROI.nii.gz and SeedROI.csv in this repository (i.e., ~/TractflowProc/). This file defines the centromedial amygdala (CMA), basolateral amygdala (BLA), superficial amygdala (SFA), and nucleus accumbens (NACC) regions bilaterally.  

#### Usage
run_PROBTRACKX.py [-h] [--gpu] --seed_template SEED_TEMPLATE [--overwrite] FDT_folder  
e.g,  
To run the commands below, you need to prepare the SeedROI.nii.gz file in ~/TractFlow_workspace. The csv file containing the ROI names must be placed in the same directory as the mask image file.
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_PROBTACKX.py --gpu --seed_template ~/TractFlow_workspace/SeedROI.nii.gz ~/TractFlow_workspace/FDT > nohup_probtrackx.out &
```

## 6. Collecting result files into a single folder
The script collect_all_results.py copies all standardized result files to one place, [workplace]/All_results/[sub].

#### Usage
usage: collect_all_results.py [-h] [--overwrite] workplace  
e.g,  
```
conda activate tractflow
cd ~/TractFlowProc
./collect_all_results.py ~/TractFlow_workspace
```

The result files are stored in, for example, ~/TractFlow_workspace/All_results/*subject* folders.  
Each subject folder contains following files.
- Freewater corrected DTI metrics  
    \*\_fw_corr_fa_\* : fractional anisotropy  
    \*\_fw_corr_md_\* : mean diffusivity  
    \*\_fw_corr_rd_\* : radial diffusivity
    \*\_fw_corr_ad_\* : axial diffusivity  
    \*\_fw_corr_ga_\* : geodesic anisotropy [[Batchelor et al., 2005](https://onlinelibrary.wiley.com/doi/10.1002/mrm.20334)]

- XTRACT  
    \*\_FDT_xtract_stats.csv : XTRACT output statistics

- PROBTRACKX  
    \*\_[ROI_NAME]_fdt_paths_prob_standard.nii.gz : Probabilistic tractography map for the ROI seed.

- Freewater uncorrected metrcts  
    DTI metrics : The axial diffusivity (ad), fractional anisotropy (fa), geodesic anisotropy (ga) [Batchelor et al., 2005], mean diffusivity (md), radial diffusivity (rd)
    
    FODF metrics : The fiber orientation distribution function (fODF) metrics including the total and maximum Apparent Fiber Density (AFD) [Raffelt et al., 2012], the Number of Fiber Orientation (NuFO) [Dell’Acqua et al., 2013] and principal fODFs orientations (up to 5 per voxel).
