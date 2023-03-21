# README
See the INSTALL file to set up the tools. It is assumed that the TractFlowProc scripts are stored in ~/TractFlowProc and the workspace is ~/TractFlow_workspace.

## 1. Prepare data files
Create an input data folder (e.g. ~/TractFlow_workspace/input_data).
Place the data file for each subject (e.g. S1, S2, ...) into the
input_data folder.
The data structure is as follows
input_data  
&nbsp;&nbsp;├── S1  
&nbsp;&nbsp;│ ├── dwi.nii.gz  
&nbsp;&nbsp;│ ├── bval  
&nbsp;&nbsp;│ ├── bvec  
&nbsp;&nbsp;│ ├── rev_b0.nii.gz (optional)  
&nbsp;&nbsp;│ ├── aparc+aseg.nii.gz (optional)  
&nbsp;&nbsp;│ ├── wmparc.nii.gz (optional)  
&nbsp;&nbsp;│ └── t1.nii.gz  
        └── S2  
          ├── dwi.nii.gz  
          ├── bval  
          ├── bvec  
          ├── rev_b0.nii.gz (optional)  
          ├── aparc+aseg.nii.gz (optional)  
          ├── wmparc.nii.gz (optional)  
          └── t1.nii.gz  

dwi.nii.gz : DWI image file  
bval, bvec : b-value and b-vector files. b-vector must be of unit length.  
t1.nii.gz : T1 anatomical image file.  
rev_b0.nii.gz (optional) : Reverse phase encoding of b0 DWI images.
aparc+aseg.nii.gz (optional) : FreeSurfer aparc+aseg image file.
wmparc.nii.gz (optional) : FreeSurfer wmparc image file.

## 2. Run FreeSurfer (optional)
```
cd ~/TractFlowProc
./run_FreeSurfer ~/TractFlow_workspace/input_data
```
The processed files are stored in the folder ~/TractFlowProc/workspace/freesurfer (parent directory of input_data).

It will take a very long time to finish the process.
The aparc+aseg.nii.gz and wmparc.nii.gz of each subject are copied to the input_data folder.

## 3. Run the TractoFlow pipeline
https://tractoflow-documentation.readthedocs.io/en/latest/pipeline/steps.html
```
cd ~/TractFlowProc
./run_FreeSurfer ~/TractFlow_workspace/input_data --with_docker
```

* If the workspace is on a network share, the trac_flow pipeline will fail (possibly due to a symlink creation error).
Then add the `-copy_local' option to the run_FreeSurfer command, for example
```
./run_TractFlow ~/TractFlow_workspace/input_data --with_docker \
    --copy_local --workspace ~/TractFlowWork
```
In this example, the --copy_local option causes the input_data folder to be copied to ~/TractFlowWork/, which is specified by the --workspace option, and when the process is finished, the results and work folders are copied back to the workspace (parent directory of input_data).

This will take a very long time.
~/TractFlowWork can be removed after the process.

## 4. Run the freewater_flow pipeline
https://github.com/scilus/freewater_flow
```
cd ~/TractFlowProc
./run_FreewaterFlow ~/TractFlow_workspace/results
```
The 'results' folder of run_TractFlow should be given as an argument. The input files for freewater_flow are copied to 'fwflow_input' in ~/TractFlowProc/workspace (parent directory of the results folder).

* The '--copy_local' option allows you to work in the local workspace specified by the '--workplace' option. The results files will be copied to the ~/TractFlow_workspace/results folder.
```
# optional
cd ~/TractFlowProc
./run_FreewaterFlow ~/TractFlow_workspace/results \
    --copy_local --workspace ~/FWlowWork
```
~/FWlowWork can be removed after the process.
