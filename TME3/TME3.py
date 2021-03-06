import torch
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import pandas as pd
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from torch.utils.tensorboard import SummaryWriter


class MonDataset(Dataset):
    def __init__(self,nameCsv,nameLabel):
        data = pd.read_csv(nameCsv)
        data = data.sample(frac=1).reset_index(drop=True)
        self.all_data_target = torch.Tensor(data[nameLabel].values.astype(np.float64))
        self.all_data = torch.Tensor(data.drop(nameLabel, axis = 1).values.astype(np.float64))
        self.all_data = self.all_data/255

    def __getitem__(self,index):
        return self.all_data[index],self.all_data_target[index]

    def __len__(self):
        return len(self.all_data)

class AutoEncoder(nn.Module):
    def __init__(self,din,dred):
        super(AutoEncoder,self).__init__()
        self.W = torch.nn.Parameter(torch.Tensor(din,dred))
        self.b1 = torch.nn.Parameter(torch.Tensor(dred))
        self.b2 = torch.nn.Parameter(torch.Tensor(din))
        torch.nn.init.xavier_uniform(self.W)
        #torch.nn.init.xavier_uniform(self.b1)
        #torch.nn.init.xavier_uniform(self.b2)

    def encoder(self,x):
        #x = torch.matmul(x,self.W)
        x = F.linear(x,self.W.t(),self.b1)
        #x = x+self.b1
        x = F.relu(x)
        return x

    def decoder(self,x):
        #x = torch.matmul(x,self.W.t())
        #x = x+self.b2
        x = F.linear(x,self.W,self.b2)
        x = torch.sigmoid(x)
        return x

    def forward(self,x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x

class State:
    def __init__(self,model,optim):
        self.model=model
        self.optim=optim
        self.epoch,self.iteration=0,0


#permet de selectionner le gpu si disponible
device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(device)
savepath = my_file = Path("monModel.pkl")

if savepath.is_file():
    #on recommence depuis le modele sauvegarde
    with savepath.open("rb") as fp:
        state=torch.load(fp)
else:
    dimEntree = 784
    dimRed = 200
    learning_rate = 1e-6
    autoencoder=AutoEncoder(dimEntree,dimRed)
    autoencoder=autoencoder.to(device)
    optim = torch.optim.Adam(autoencoder.parameters(), lr=learning_rate)
    state=State(autoencoder,optim)


ITERATIONS = 20
BATCH_SIZE = 100

data_train = DataLoader(MonDataset("mnist_train.csv","label"), shuffle=True, batch_size=BATCH_SIZE)
data_test = DataLoader(MonDataset("mnist_train.csv","label"), shuffle=True, batch_size=BATCH_SIZE)

#Nombre d'étape de moyennation de l'erreur pour l'enregister dans tensorboard
n_moy = 10
writer = SummaryWriter("courbe_SGD")
loss_moyen = 0
it_for_loss = 0

mse = nn.MSELoss()


for epoch in range(state.epoch,ITERATIONS):
    for x,_ in data_train:
        state.optim.zero_grad()
        #On transfert les données sur GPU si disponible
        x = x.to(device)
        xhat=state.model(x)
        l=mse(xhat,x)
        l.backward(retain_graph=True)
        state.optim.step()
        loss_moyen+=l
        state.iteration+=1
        it_for_loss+=1
        if(it_for_loss%n_moy==0):
            loss_train = loss_moyen/n_moy
            writer.add_scalar('Loss_stochastique/train', loss_train, state.iteration)
            loss_moyen = 0

    with savepath.open("wb") as fp:
        state.epoch=epoch+1
        torch.save(state,fp)
