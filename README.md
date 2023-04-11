# README
See the [INSTALL](INSTALL.md) file to set up the environment. These instructions assume that the TractFlowProc scripts are stored in ~/TractFlowProc and the workspace is ~/TractFlow_workspace.

## 1. Prepare data files
Create an input data folder (e.g. ~/TractFlow_workspace/input_data).  
Place the data file for each subject (e.g. S1, S2, ...) into the input_data folder.  
The data structure is as follows:  
input_data  
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
**You can skip this step.** Only if the T1 image contrast is not good enough to segment tissue and you need to use Atlas Based Segmentation (ABS) in Tractflow, you should perform this process.  

The fiber tracking process uses the white matter (WM), gray matter (GM), and cerebrospinal fluid (CSF) maps to compute the tracking maps and the seeding mask. These masks are extracted by default with 'fast' in FSL for t1.nii.gz, but you can also use a FreeSurfer segmentation, i.e. aparc+aseg and wmparc, with the --ABS option in tractflow.  

The script run_FreeSurfer.py processes t1.nii.gz in the input_data folder to create aparc+aseg.nii.gz and wmparc.nii.gz.
```
cd ~/TractFlowProc
nohup ./run_FreeSurfer.py ~/TractFlow_workspace/input_data > nohup_FS.out &
```
The process will take a very long time (almost a day for one subject, depending on the CPU). Multiple subjects are processed in parallel, and the number of simultaneous processes is '(number of CPU cores)//2'.  
The files processed by FreeSurfer are stored in the folder ~/TractFlow_workspace/freesurfer.  
Each subject's aparc+aseg.nii.gz and wmparc.nii.gz are created in the input_data folder.  

## 3. Run the TractoFlow pipeline
https://tractoflow-documentation.readthedocs.io/en/latest/pipeline/steps.html
```
cd ~/TractFlowProc
nohup ./run_TractFlow.py ~/TractFlow_workspace/input_data --with_docker --fully_reproducible > nohup_tf.out &
```
The command returns immediately, and the process runs in the background.  
The process takes a very long time: > 10h for one subject. Multiple subjects are processed in parallel.  

* Add '--ABS' option to run TractoFlow-ABS (See [2](#2-run-freesurfer-optional)).  

## 4. Run the freewater_flow pipeline
https://github.com/scilus/freewater_flow
```
conda activate tractflow
cd ~/TractFlowProc
nohup ./run_FreewaterFlow.py ~/TractFlow_workspace/results > nohup_fwf.out &
```
The 'results' folder of run_TractFlow.py should be passed as an argument. The input files for freewater_flow are created in 'fwflow_input' in ~/TractFlow_workspace (parent directory of the results folder).  
Working directory, '~/TractFlow_workspace/fwflow_work', will also be made.

The command returns immediately, and the process runs in the background.  
The process takes a very long time: > 10h for one subject. Multiple subjects are processed in parallel.  

## 5. Result files
Result files are saved in the ~/TractFlow_workspace/results/*subject* folders.  

- DTI_Metrics/  
    The axial diffusivity (ad), fractional anisotropy (fa), geodesic anisotropy (ga) [[Batchelor et al., 2005](https://onlinelibrary.wiley.com/doi/10.1002/mrm.20334)], mean diffusivity (md), radial diffusivity (rd), tensor, tensor norm [[Kindlmann et al., 2007](https://ieeexplore.ieee.org/abstract/document/4359059)], tensor eigenvalues, tensor eigenvectors, tensor mode, and color-FA are made.

- FODF_Metrics/  
    The metrics of fiber orientation distribution function (fODF) computed are the total and maximum Apparent Fiber Density (AFD) [[Raffelt et al., 2012]()], the Number of Fiber Orientation (NuFO) [[Dell’Acqua et al., 2013]()] and principal fODFs orientations (up to 5 per voxel).

- Local_Tracking/ 
    *subject*__local_tracking_prob_wm_seeding_wm_mask_seed_0.trk 

# 6. Standardize DTI and fODF metrics
