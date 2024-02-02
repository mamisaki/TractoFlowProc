
# INSTALL

## Install miniconda
See https://conda.io/projects/conda/en/latest/user-guide/install/index.html

## Install git
See https://git-scm.com/book/en/v2/Getting-Started-Installing-Git

## Install FreeSurfer
https://surfer.nmr.mgh.harvard.edu/fswiki/DownloadAndInstall

## Install R
https://cran.r-project.org/bin/linux/ubuntu/

## Install AFNI
https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/background_install/install_instructs/index.html

## Install FSL
https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FslInstallation  


## Download scilpy git repositories
```
cd
git clone https://github.com/scilus/scilpy.git
```

## Create tractoflow conda environment
```
conda create -n tractoflow python=3.10 pip hdf5=1.12 cython psutil mkl pyyaml scikit-image seaborn conda-forge::singularity toml tornado typing-extensions -c anaconda -c conda-forge
conda activate tractoflow
cd ~/scilpy
pip install antspyx smriprep niworkflows fmriprep
```

## Download nextflow
```
cd ~/bin
wget https://github.com/nextflow-io/nextflow/releases/download/v21.10.6/nextflow && chmod +x nextflow
rm -rf ~/.nextflow
sudo apt install default-jre
```

## Download TractoFlow and freewater_flow
https://tractoflow-documentation.readthedocs.io/en/latest/installation/install.html

```
nextflow pull scilus/tractoflow
cd
git clone https://github.com/scilus/freewater_flow
```

## Install c3d and connectome workbench for converting ANTs' warp to FSL
Download c3d-1.0.0-Linux-x86_64.tar.gz from http://www.nitrc.org/frs/downloadlink.php/7073 into ~/Downloads  
```
cd
tar zxvf Downloads/c3d-1.0.0-Linux-x86_64.tar.gz
cd bin
ln -sf ~/c3d-1.0.0-Linux-x86_64/bin/c3d_affine_tool ./

sudo apt install connectome-workbench
```

## Install TractoFlowProc scripts
```
cd
git clone https://github.com/mamisaki/TractoFlowProc
```

Isntall container
```
cd TractoFlowProc
docker pull scilus/scilus:1.5.0
singularity build scilus_1.5.0.sif docker://scilus/scilus:1.5.0
```
* Singurality container build by different Singurality version may not work. if "ERROR  : Unknown image format/type' happens, you need to rebuid the container.