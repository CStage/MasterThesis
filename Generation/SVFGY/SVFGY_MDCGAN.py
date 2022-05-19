# -*- coding: utf-8 -*-
"""GAN(G).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ixFBKXfum2k6uieCbeaMEx74pgRyGO4N

# Mount drive
"""

"""# Imports"""
import torch
from torch.utils.data import Dataset, DataLoader
from torch import nn, optim
import torch.nn.functional as F
from torch.autograd.variable import Variable
from torchvision import transforms
import random
import numpy as np
import h5py
import matplotlib.pyplot as plt
from datetime import datetime
import os
import sys
import csv
csv.field_size_limit(sys.maxsize)

transform = transforms.Compose(
    [transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])

batch_size = 128

image_size = 64

nc = 3

nz = 122

ngf = 64

ndf = 64

lr = 0.0002

beta1 = 0.5


"""# Dataset"""
# Current version used for testing the set up
class FiskeSet_test(Dataset):
    def __init__(self, anchors, positives, seed, amount, transform=None):
        random.seed(seed)
        if amount <= 1:
            raise Exception("Amount of samples must be greater than 1 or negatives cannot be fetched.")

        self.anchors = anchors
        self.positives = positives
        self.transform = transform
        self.amount = amount

    def __len__(self):
        return self.amount

    def __getitem__(self, idx):
        anchor = self.anchors[idx]
        positive = self.positives[idx]

        if self.transform:
            positive = self.transform(positive)

        return anchor, positive


# Generic version used for the entire dataset (once ready)

class FiskeSet(Dataset):
    def __init__(self, anchors, positives, seed, transform=None):
        random.seed(seed)

        self.anchors = anchors
        self.positives = positives
        self.transform = transform

    def __len__(self):
        return len(self.positives)

    def __getitem__(self, idx):
        anchor = self.anchors[idx]
        positive = self.positives[idx]

        if self.transform:
            positive = self.transform(positive)

        return anchor, positive

class KaGenerator(nn.Module):
    def __init__(self):
        super(KaGenerator, self).__init__()
        self.main = nn.Sequential(
            # input is Z, going into a convolution
            nn.ConvTranspose2d( nz, ngf * 8, 4, 1, 0, bias=False),
            nn.BatchNorm2d(ngf * 8),
            nn.ReLU(True),
            # state size. (ngf*8) x 4 x 4
            nn.ConvTranspose2d(ngf * 8, ngf * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf * 4),
            nn.ReLU(True),
            # state size. (ngf*4) x 8 x 8
            nn.ConvTranspose2d( ngf * 4, ngf * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf * 2),
            nn.ReLU(True),
            # state size. (ngf*2) x 16 x 16
            nn.ConvTranspose2d( ngf * 2, ngf, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf),
            nn.ReLU(True),
            # state size. (ngf) x 32 x 32
            nn.ConvTranspose2d( ngf, nc, 4, 2, 1, bias=False),
            nn.Tanh()
            # state size. (nc) x 64 x 64
        )

    def forward(self, input):
        return self.main(input)


class Fiskriminator(nn.Module):
    def __init__(self):
        super(Fiskriminator, self).__init__()
        self.main = nn.Sequential(
            # input is (nc) x 64 x 64
            nn.Conv2d(nc, ndf, 4, 2, 1, bias=False),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf) x 32 x 32
            nn.Conv2d(ndf, ndf * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 2),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*2) x 16 x 16
            nn.Conv2d(ndf * 2, ndf * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 4),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*4) x 8 x 8
            nn.Conv2d(ndf * 4, ndf * 8, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 8),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*8) x 4 x 4
            nn.Conv2d(ndf * 8, 1, 4, 1, 0, bias=False),
            nn.Sigmoid()
        )

    def forward(self, input):
        return self.main(input)

def images_to_vectors(images):
    return images.view(images.size(0), (4096*3))

def vectors_to_images(vectors):
    return vectors.view(vectors.size(0), 3, 64, 64)

def show_img(rgb_matrix):
  img = rgb_matrix.permute(1, 2, 0)
  img = img.cpu().detach().numpy()
  img = np.array(img)
  plt.imshow(img)
  plt.show()

def weights_init(m):
  classname = m.__class__.__name__
  if classname.find('Conv') != -1:
    nn.init.normal_(m.weight.data, 0.0, 0.02)
  elif classname.find('BatchNorm') != -1:
    nn.init.normal_(m.weight.data, 1.0, 0.02)
    nn.init.constant_(m.bias.data, 0)

def generate_genres_tensor(genres_vectors):
    """
    Takes a bunch of vectors (numpy arrays) of genre-names and creates one-hot vectors
    based on them. The resulting tensor can be concatenated to anchors using .cat.
    SHOULD BE WORKING, but maybe some quick testing is in order ;)
    """
    genres_master = ["Blues", "Classical", "Electronic", "Folk World & Country", "Funk / Soul", "Hip Hop", "Jazz",
                     "Latin",
                     "Pop", "Reggae", "Rock"]
    genres_tensor = []
    for idx, genres in enumerate(genres_vectors):
        list_vector = []
        if "Folk" in genres:
            genres = genres.replace("Folk, World,", "Folk World")
        genres = genres.split(", ")
        for i, g in enumerate(genres_master):
            if g in genres:
                list_vector.append(1)
            else:
                list_vector.append(0)
        genres_tensor.append(torch.tensor(list_vector))
    genres_tensor = torch.stack(tuple(genres_tensor))
    return genres_tensor


# One hot encoding for years.
def generate_years_tensor(years_vectors):
    years_master = list(range(100))

    years_tensor = []
    for idx, year in enumerate(years_vectors):
        list_vector = []
        for y in years_master:
            if (int(year[-2:]) == int(y)):
                list_vector.append(1)
            else:
                list_vector.append(0)
        years_tensor.append(torch.tensor(list_vector))
    years_tensor = torch.stack(tuple(years_tensor))
    return years_tensor


def data_normalization(data):
    minimum = np.amin(data)
    maximum = np.amax(data)
    for i in range(len(data)):
        data[i] = (data[i] - minimum) / (maximum - minimum)

    return torch.tensor(data)


def create_dataset(path, input_attributes, seed, amount=None, debug=False):
    h = h5py.File(path)

    svd_attributes = list(h["Single Value Data"].attrs["column_names"])
    # print(svd_attributes)
    # print(h["Metadata"].attrs["column_names"])
    md_attributes = list(h["Metadata"].attrs["column_names"])

    svd_idx_list = []
    tensor_lyf = []
    if debug:
        random.seed(seed)
        rands = random.sample(range(h["Single Value Data"].shape[0]), amount)
        rands.sort()
        images = h["Images"][rands]
        for att in input_attributes:
            if "Genres" == att:
                genres_vectors = h["Metadata"].asstr()[rands, md_attributes.index("Genres")]
                genres_tensor = generate_genres_tensor(genres_vectors)
                tensor_lyf.append(genres_tensor)
                # anchors = torch.cat((anchors, genres_tensor), dim=1)
            elif "Year" == att:
                years_vectors = h["Metadata"].asstr()[rands, md_attributes.index("Year")]
                years_tensor = generate_years_tensor(years_vectors)
                tensor_lyf.append(years_tensor)
                # anchors = torch.cat((anchors, years_tensor), dim=1)
            elif "_norm" in att:
                clean_att = att.replace("_norm", "")
                idx = svd_attributes.index(clean_att)
                att_vectors = h["Single Value Data"][rands, idx]
                att_tensor = data_normalization(att_vectors)
                att_tensor = att_tensor[:, None]
                tensor_lyf.append(att_tensor)
                # anchors = torch.cat((anchors, att_tensor), dim=1)
            else:
                svd_idx_list.append(svd_attributes.index(att))
        for svd in svd_idx_list:
            addition_tensor = h["Single Value Data"][rands, svd]
            addition_tensor = addition_tensor[:, None]
            tensor_lyf.append(torch.tensor(addition_tensor))
        anchors = torch.cat(tuple(tensor_lyf), dim=1)
        print("Anchors SHAPE:", anchors.shape)
        dataset = FiskeSet_test(anchors, images, seed, amount, transform)

    else:
        images = h["Images"]
        for att in input_attributes:
            if "Genres" == att:
                genres_vectors = h["Metadata"].asstr()[:, md_attributes.index("Genres")]
                genres_tensor = generate_genres_tensor(genres_vectors)
                tensor_lyf.append(genres_tensor)
            elif "Year" == att:
                years_vectors = h["Metadata"].asstr()[:, md_attributes.index("Year")]
                years_tensor = generate_years_tensor(years_vectors)
                tensor_lyf.append(years_tensor)
            elif "_norm" in att:
                clean_att = att.replace("_norm", "")
                idx = svd_attributes.index(clean_att)
                att_vectors = h["Single Value Data"][:, idx]
                att_tensor = data_normalization(att_vectors)
                att_tensor = att_tensor[:, None]
                tensor_lyf.append(att_tensor)
            else:
                svd_idx_list.append(svd_attributes.index(att))
        for svd in svd_idx_list:
            addition_tensor = h["Single Value Data"][:, svd]
            addition_tensor = addition_tensor[:, None]
            tensor_lyf.append(torch.tensor(addition_tensor))
        anchors = torch.cat(tuple(tensor_lyf), dim=1)
        print("Anchors SHAPE:", anchors.shape)

        dataset = FiskeSet(anchors, images, seed, transform)
        # print("Hello?", genres_tensor.shape, anchors.shape)

    return dataset

"""# Paths"""
#Put name here!
base_path = "/home/data_shares/fiskkagedata/"
checkpoint_path = rf"{base_path}/ML_models/checkpoints/"
train_path = rf"{base_path}Train.hdf5"
#train_path = r"C:\Users\cstag\Downloads\Dev.hdf5"
dev_path = rf"{base_path}Dev.hdf5"
csv_path = rf"{base_path}csv_data/"
image_path = rf"{base_path}Images"
seq_lengths_path = rf"{base_path}seq_lengths.hdf5"

if __name__ == '__main__':
    """# Global settings"""
    batch_size = 128
    seed = 42
    epochs = 500

    input_attributes =  ["energy", "danceability", "speechiness", "acousticness", "instrumentalness",
     "liveness", "valence", "Year", "Genres", "tempo_norm", "loudness_norm", "key_norm",
     "mode"]

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    print(device)

    """# Data loader"""
    print("Creating train set")
    train_set = create_dataset(train_path, input_attributes, seed)
    print("Creating data loader")
    trainloader = DataLoader(train_set, shuffle = True, num_workers=2, batch_size=batch_size)


    #Version 2
    #Generated images are greyscale, but true images  are RGB, requires n_out=4096
    print("Set up generator")
    Gnet = KaGenerator().to(device)
    Gnet.apply(weights_init)

    Dnet = Fiskriminator().to(device)
    Dnet.apply(weights_init)

    criterion = nn.BCELoss()


    real_label = 1
    fake_label = 0

    params = list(Gnet.parameters())
    optimizerD = optim.Adam(Dnet.parameters(), lr=lr, betas=(beta1, 0.999))
    optimizerG = optim.Adam(params, lr=lr, betas=(beta1, 0.999))

    enable_checkpoints = True

    print(f"With enable_checkpoints={enable_checkpoints}")
    if enable_checkpoints:
      time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      folder_path = checkpoint_path + "/WGAN_" + str(time)
      os.mkdir(folder_path)
      os.mkdir(folder_path + "/KaGenerator")
      os.mkdir(folder_path + "/Fiskriminator")
      h = h5py.File(f"{folder_path}/GANImages.hdf5", "a")
      h.close()


      with open(folder_path + r"/model_settings.txt", "w") as current_settings:
        current_settings.write(f"ATTRIBUTES: {input_attributes} \nSEED: {seed} \nBATCH SIZE: {batch_size}")

      with open(folder_path + r"/Gnet_epoch_losses.csv", "w", encoding="UTF8", newline="") as epoch_losses:
        writer = csv.writer(epoch_losses, delimiter=";")
        writer.writerow(["EPOCH", "LOSS PER SAMPLE"])

      with open(folder_path + r"/Dnet_epoch_losses.csv", "w", encoding="UTF8", newline="") as epoch_losses:
        writer = csv.writer(epoch_losses, delimiter=";")
        writer.writerow(["EPOCH", "LOSS PER SAMPLE"])

    for epoch in range(epochs):
        for i, (anchors, positives) in enumerate(trainloader):

            ############################
            # (1) Update D network: maximize log(D(x)) + log(1 - D(G(z)))
            ###########################
            ## Train with all-real batch
            Dnet.zero_grad()
            # Format batch
            real_cpu = positives.to(device)
            b_size = real_cpu.size(0)
            label = torch.full((b_size,), real_label, dtype=torch.float, device=device)
            # Forward pass real batch through D
            output = Dnet(real_cpu).view(-1)
            # Calculate loss on all-real batch
            errD_real = torch.mean(output)
            # Calculate gradients for D in backward pass
            D_x = output.mean().item()

            """OUR SETUP"""
            ## Train with all-fake batch
            # Generate batch of latent vectors
            anchors = anchors[:, :, None, None].float().to(device)
            # Generate fake image batch with G
            fake = Gnet(anchors)

            """TUTORIAL SETUP"""
            # noise = torch.randn(b_size, nz, 1, 1, device=device)
            # # Generate fake image batch with G
            # fake = Gnet(noise)

            label.fill_(fake_label)
            # Classify all fake batch with D
            output = Dnet(fake.detach()).view(-1)
            # Calculate D's loss on the all-fake batch
            errD_fake = torch.mean(output)
            # Calculate the gradients for this batch, accumulated (summed) with previous gradients
            D_G_z1 = output.mean().item()
            # Compute error of D as sum over the fake and the real batches
            errD = -(errD_real - errD_fake)
            errD.backward()
            # Update D
            optimizerD.step()
            for p in Dnet.parameters():
                p.data.clamp_(-0.01, 0.01)

            ############################
            # (2) Update G network: maximize log(D(G(z)))
            ###########################
            Gnet.zero_grad()
            label.fill_(real_label)  # fake labels are real for generator cost
            # Since we just updated D, perform another forward pass of all-fake batch through D
            output = Dnet(fake).view(-1)
            # Calculate G's loss based on this output
            errG = -torch.mean(output)
            # Calculate gradients for G
            errG.backward()
            D_G_z2 = output.mean().item()
            # Update G
            optimizerG.step()

            # Output training stats
            if i % 50 == 0:
                print('[%d/%d][%d/%d]\tLoss_D: %.4f\tLoss_G: %.4f\tD(x): %.4f\tD(G(z)): %.4f / %.4f'
                      % (epoch, epochs, i, len(trainloader),
                         errD.item(), errG.item(), D_x, D_G_z1, D_G_z2))

            # Save Losses for plotting later
        if enable_checkpoints:
            torch.save(Gnet.state_dict(), f"{folder_path}/KaGenerator/KaGenerator_epoch_{epoch}")
            torch.save(Dnet.state_dict(), f"{folder_path}/Fiskriminator/Fiskriminator_epoch_{epoch}")
            sample_loader = DataLoader(train_set, 64, False, num_workers=2)
            ancs, poss = next(iter(sample_loader))
            ancs = ancs.float().to(device)
            ancs = ancs[:, :, None, None]
            fake = Gnet(ancs).detach().cpu()
            fake = vectors_to_images(fake)
            fake = fake[None, :, :, :, :]
            h = h5py.File(f"{folder_path}/GANImages.hdf5", "a")
            if "RGBMats" not in h:
                h.create_dataset("RGBMats", data=fake, shape=(1, 64, 3, 64, 64), maxshape=(None, 64, 3, 64, 64))
            else:
                past_size = h["RGBMats"].shape[0]
                h["RGBMats"].resize(past_size + 1, 0)
                h["RGBMats"][past_size] = fake
            with open(folder_path + r"/Gnet_epoch_losses.csv", "a", encoding="UTF8", newline="") as epoch_losses:
              writer = csv.writer(epoch_losses, delimiter=";")
              writer.writerow([epoch, errG.item()])
            with open(folder_path + r"/Dnet_epoch_losses.csv", "a", encoding="UTF8", newline="") as epoch_losses:
              writer = csv.writer(epoch_losses, delimiter=";")
              writer.writerow([epoch, errD.item()])
            h.close()
    # devloader = DataLoader(dev_set, batch_size=1, shuffle=False, num_workers=2)