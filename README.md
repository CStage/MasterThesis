# MasterThesis

## Introduction
This repo contains all code related to machine learning activities in the Master Thesis: _Musical Impressions and Album Art: Investigating the Patterns_ by Philip Fisker (PFisk) and Christian Stage (CStage), MSc. Software Design students from the IT University of Copenhagen, supervised by Max Müller-Eberstein. The repo consists of two folders **IRM** and **Generation**. **IRM** contains two Python notebooks related to training of our image retrieval models and **Generation** contains a number of Python scripts related to training our generative models. The notebooks were run using GPUs from Google Colab whereas the scripts were run on the HPC at ITU. All code depend on access to hdf5-datasets that have been omitted from this repo due to size constraints. Therefore, the code is for reference only, and internal comments have not been omitted.

## Contents

### IRM
This folder contains two notebooks _NonSequential_ and _Sequential_. These contain setup and training for image retrieval models with non-sequential and sequential data respectively.

### Generation
This folder contains all scripts related to training our generative models. It consists of two subfolders **SVF** and **SVFGY** named after the type of input the containing models require. Explanations of these types of input are available in the thesis report. The contents of the filenames describe the anatomy of the model trained by the script. For each subfolder there is one file without extension called _MLP_. This is a pretrained Multi-Layer Perceptron state_dict that is used in some models to pre-encode input tensors before they are passed on to generative models.

- **MSE** -> MSELoss-based Generator
- **DCGAN** -> Deep Convolutional Generative Adversarial Network (DCGAN)
- **MDCGAN** -> Modified DCGAN (description of modifications is available in thesis report)
- **WGAN** -> Wasserstein GAN
  - **DC** -> Wasserstein GAN with a Deep Convolutional architecture
  - **LIN** -> Wasserstein GAN with a linear layer architecture
- **mlp** -> Input of model is pre-encoded by a pretrained Multi-Layer Perceptron (mlp) before training.


## Related work
As part of the thesis work we created an interactive [survey site](https://kagenet.vercel.app/). The associated code can be found in this [repo](https://github.com/PFisk/kagenet).

## Contact
Inquiries about the code and project can be sent to chrst@itu.dk or phfi@itu.dk
