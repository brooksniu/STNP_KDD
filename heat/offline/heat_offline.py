#!/usr/bin/env python
# coding: utf-8

# In[1]:


#!/usr/bin/env python
# coding: utf-8

# In[24]:


import numpy as np
from numpy.random import binomial
import torch
import matplotlib as mpl
import matplotlib.pyplot as plt
# %matplotlib inline
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (RBF, Matern, RationalQuadratic,
                                              ExpSineSquared, DotProduct,
                                              ConstantKernel)
import torch.nn as nn
from sklearn import preprocessing
from scipy.stats import multivariate_normal


# In[25]:


device = torch.device("cuda:0")
seed = 31
torch.manual_seed(seed)
np.random.seed(seed)
# device


# In[26]:


large = 25; med = 19; small = 12
params = {'axes.titlesize': large,
          'legend.fontsize': 20,
          'figure.figsize': (27, 8),
          'axes.labelsize': med,
          'xtick.labelsize': med,
          'ytick.labelsize': med,
          'figure.titlesize': med}
plt.rcParams.update(params)


# # Load Data:

# In[27]:


x_all = np.load("../data/x_train.npy")
x_val = np.load("../data/x_val.npy")
x_test = np.load("../data/x_test.npy")
y_all = np.load("../data/y_train.npy").reshape(384,32,1,32)
y_val = np.load("../data/y_val.npy").reshape(64,32,1,32)
y_test = np.load("../data/y_test.npy").reshape(64,32,1,32)
y_all = y_all[:,::8,...]
y_val = y_val[:,::8,...]
y_test = y_test[:,::8,...]
initial = np.load("../data/initial_pic.npy").reshape(1,32)
# print(y_test)


# In[2]:


scale_mean_y = np.mean(y_all)
scale_std_y = np.std(y_all)

y_all = (y_all - scale_mean_y)/scale_std_y 
y_val = (y_val - scale_mean_y)/scale_std_y 
y_test = (y_test - scale_mean_y)/scale_std_y 

# y_all = np.insert(y_all, 0, initial, axis = 1)
# y_val = np.insert(y_val, 0, initial, axis = 1)
# y_test = np.insert(y_test, 0, initial, axis = 1)


# In[33]:


print(y_all.shape)
print(y_val.shape)
print(y_test.shape)
print(scale_mean_y)
print(scale_std_y)


# In[73]:


from datetime import datetime
# In[28]:


# print(x_all)


# In[29]:


# print(np.array(y_all).shape)
# for elem in y_all:
#     for sim in elem:
#         draw(sim[0], sim[1])


# In[30]:


# # replace beta_epsilon_all with fkAB to initiate the mask!
# mask_init = np.zeros(len(x_all))
# mask_init[:8] = 1

# np.random.shuffle(mask_init)
# x_train_init = x_all[mask_init.astype('bool')]
# print(x_train_init)

# # use the selected fkAB values to select their corresponding data
# y_train_init = np.array(y_all)[mask_init.astype('bool')]
# # selected_y.shape[2]*selected_y.shape[3]*selected_y.shape[4] : 50 * 2 * 30 * 30
# # each data point for y with the timestamp info included: 2(A and B) ,(32 , 32) <- pixels 
# print(x_train_init.shape, y_train_init.shape)
# print(mask_init)


# # CNP

# In[31]:


#reference: https://chrisorm.github.io/NGP.html
class REncoder(torch.nn.Module):
    """Encodes inputs of the form (x_i,y_i) into representations, r_i."""
    
    def __init__(self, in_dim, out_dim, init_func = torch.nn.init.normal_):
        super(REncoder, self).__init__()
        self.l1_size = 64 #16
        self.l2_size = 32 #8
        self.l3_size = 16 #DNE
        
        self.l1 = torch.nn.Linear(in_dim, self.l1_size)
        self.l2 = torch.nn.Linear(self.l1_size, self.l2_size)
        self.l3 = torch.nn.Linear(self.l2_size, self.l3_size)
        self.l4 = torch.nn.Linear(self.l3_size, out_dim)
        self.a1 = torch.nn.Sigmoid()
        self.a2 = torch.nn.Sigmoid()
        self.a3 = torch.nn.Sigmoid()
        
        if init_func is not None:
            init_func(self.l1.weight)
            init_func(self.l2.weight)
            init_func(self.l3.weight)
            init_func(self.l4.weight)
        
    def forward(self, inputs):
        return self.l4(self.a3(self.l3(self.a2(self.l2(self.a1(self.l1(inputs)))))))

class ZEncoder(torch.nn.Module):
    """Takes an r representation and produces the mean & standard deviation of the 
    normally distributed function encoding, z."""
    def __init__(self, in_dim, out_dim, init_func=torch.nn.init.normal_):
        super(ZEncoder, self).__init__()
        self.m1_size = out_dim
        self.logvar1_size = out_dim
        
        self.m1 = torch.nn.Linear(in_dim, self.m1_size)
        self.logvar1 = torch.nn.Linear(in_dim, self.m1_size)

        if init_func is not None:
            init_func(self.m1.weight)
            init_func(self.logvar1.weight)
        
    def forward(self, inputs):
        

        return self.m1(inputs), self.logvar1(inputs)

"""Original Decoder implementation without convolutional layer"""
# class Decoder(torch.nn.Module):
#     """
#     Takes the x star points, along with a 'function encoding', z, and makes predictions.
#     """
#     def __init__(self, in_dim, out_dim, init_func=torch.nn.init.normal_):
#         super(Decoder, self).__init__()
#         self.l1_size = 16 #8
#         self.l2_size = 32 #16
#         self.l3_size = 64 #DNE
        
#         self.l1 = torch.nn.Linear(in_dim, self.l1_size)
#         self.l2 = torch.nn.Linear(self.l1_size, self.l2_size)
#         self.l3 = torch.nn.Linear(self.l2_size, self.l3_size)
#         self.l4 = torch.nn.Linear(self.l3_size, out_dim)
        
#         if init_func is not None:
#             init_func(self.l1.weight)
#             init_func(self.l2.weight)
#             init_func(self.l3.weight)
#             init_func(self.l4.weight)
        
#         self.a1 = torch.nn.Sigmoid()
#         self.a2 = torch.nn.Sigmoid()
#         self.a3 = torch.nn.Sigmoid()
        
#     def forward(self, x_pred, z):
#         """x_pred: No. of data points, by x_dim
#         z: No. of samples, by z_dim
#         """
#         zs_reshaped = z.unsqueeze(-1).expand(z.shape[0], x_pred.shape[0]).transpose(0,1)
#         xpred_reshaped = x_pred
        
#         xz = torch.cat([xpred_reshaped, zs_reshaped], dim=1)

#         return self.l4(self.a3(self.l3(self.a2(self.l2(self.a1(self.l1(xz))))).squeeze(-1)))

def MAE(pred, target):
#     print(target.unsqueeze(2).shape)
    pred = pred*scale_std_y + scale_mean_y
    target = target*scale_std_y + scale_mean_y
    loss = torch.abs(pred-target.unsqueeze(2))
    return loss.mean()


# In[32]:


conv_outDim = 64
init_channels = 4
image_channels_in_encoder = 2
image_channels_in_decoder = 1
kernel_size = 3
lstm_hidden_size = 64
decoder_init = torch.from_numpy(initial).float().to(device)

class ConvEncoder(nn.Module):
    def __init__(self, image_channels):
        super().__init__()
        self.conv1 = nn.Sequential(
            #input_shape = (2,32)
            nn.Conv1d(in_channels=image_channels, out_channels=init_channels, kernel_size = kernel_size,stride = 2),
            nn.ReLU(),
#             nn.MaxPool2d(kernel_size = 2)
        )
        self.conv2 = nn.Sequential(
            nn.Conv1d(in_channels=init_channels, out_channels=init_channels*2, kernel_size = kernel_size,stride = 2),
            nn.ReLU(),
#             nn.Dropout(p = .2),
#             nn.MaxPool2d(kernel_size = 2)
        )
        self.conv3 = nn.Sequential(
            nn.Conv1d(in_channels=init_channels*2, out_channels=init_channels*4, kernel_size = kernel_size,stride = 2),
            nn.ReLU(),
#             nn.MaxPool2d(kernel_size = 2)
        )
        self.conv4 = nn.Sequential(
            nn.Conv1d(in_channels=init_channels*4, out_channels=init_channels*8, kernel_size = kernel_size,stride = 2),
            nn.ReLU(),
#             nn.MaxPool2d(kernel_size = 2)
        )
        self.output = nn.Sequential(
            #start pushing back
#             nn.Linear(256, 128),
#             nn.ReLU(),
#             nn.Dropout(p = .2),
            nn.Linear(32, conv_outDim)
        )
        
    def forward(self, x):
        #x.to(torch.float32)
#         print("input shape: ", x.shape)
        #(2,30,30)
        x = self.conv1(x)
       #print(x.shape)
        #(64,124,252)
        x = self.conv2(x)
        #print(x.shape)
        #(64,21,42)
        x = self.conv3(x)
        x = self.conv4(x)
#         print("x before reshape", x.shape)
        if (x.ndim == 2):
            x = x.view(x.size(0))
        else:
            x = x.view(x.size(0), -1)
#         print("x after reshape: ", x.shape)
        output = self.output(x)
#         print("shape of encoder output: ", output.shape)
        
        return output


# In[33]:


class ConvDecoder(nn.Module):
    def __init__(self, in_dim, out_dim) :
        super().__init__()
        self.input = nn.Sequential(
            #start pushing back
            nn.Linear(in_dim, conv_outDim),
            nn.ReLU()
        )
        self.conv1 = nn.Sequential(
            nn.ConvTranspose1d(in_channels=conv_outDim, out_channels=init_channels*8, kernel_size = kernel_size,stride = 2),
            nn.ReLU()
#             nn.MaxPool2d(kernel_size = 2)
        )
        self.conv2 = nn.Sequential(
            nn.ConvTranspose1d(in_channels=init_channels*8, out_channels=init_channels*4, kernel_size = kernel_size,stride = 2),
            nn.ReLU()
#             nn.Dropout(p = .2),
#             nn.MaxPool2d(kernel_size = 3)
        )
        self.conv3 = nn.Sequential(
            nn.ConvTranspose1d(in_channels=init_channels*4, out_channels=init_channels*2, kernel_size = kernel_size,stride = 2),
            nn.ReLU()
#             nn.MaxPool2d(kernel_size = 3)
        )
        self.conv4 = nn.Sequential(
            nn.ConvTranspose1d(in_channels=init_channels*2, out_channels=image_channels_in_decoder, kernel_size = kernel_size,stride = 2, output_padding = 1),
            nn.ReLU()
#             nn.MaxPool2d(kernel_size = 3)
        )

        
    def forward(self, x_pred):
        """x_pred: No. of data points, by x_dim
        z: No. of samples, by z_dim
        """
#         zs_reshaped = z.unsqueeze(-1).expand(z.shape[0], x_pred.shape[0]).transpose(0,1)
#         xpred_reshaped = x_pred
#         print("zs shape: ", zs_reshaped.shape)
#         print("xpred shape: ", xpred_reshaped.shape)
        
#         xz = torch.cat([xpred_reshaped, zs_reshaped], dim=1)
        x = self.input(x_pred)
        x = x.view(-1, conv_outDim, 1)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        output = self.conv4(x)
#         print("predicted image shape", output.shape)
        
        return output


# In[34]:


class DCRNNModel(nn.Module):
    def __init__(self, x_dim, y_dim, r_dim, z_dim, init_func=torch.nn.init.normal_):
        super().__init__()
        self.conv_encoder = ConvEncoder(image_channels_in_encoder)
        self.conv_encoder_in_decoder = ConvEncoder(image_channels_in_decoder)
        self.deconv = ConvDecoder(lstm_hidden_size, y_dim) # (x*, z) -> y*
#         self.lstm_linear = nn.Sequential(
# #             nn.Linear(conv_outDim, conv_reduction_dim+x_dim)
#             nn.Linear(lstm_hidden_size, r_dim),
#             nn.Sigmoid(),
#             nn.Linear(r_dim, r_dim)
#         )
        self.encoder_lstm = nn.LSTM(input_size = conv_outDim+x_dim, hidden_size = lstm_hidden_size, num_layers = 1, batch_first=True)
        self.decoder_lstm = nn.LSTM(input_size = conv_outDim+x_dim+z_dim, hidden_size = lstm_hidden_size, num_layers = 1, batch_first=True)
#         self.repr_encoder = REncoder(x_dim+conv_outDim, r_dim) # (x,y)->r
        self.z_encoder = ZEncoder(lstm_hidden_size, z_dim) # r-> mu, logvar
        self.z_mu_all = 0
        self.z_logvar_all = 0
        self.z_mu_context = 0
        self.z_logvar_context = 0
        self.zs = 0
        self.zdim = z_dim
        self.xdim = x_dim
        self.y_init = decoder_init
#         self.reduce_dm_decoder = nn.Linear(conv_outDim, conv_reduction_dim)
#         self.reduce_dm_encoder = nn.Linear(conv_outDim, conv_reduction_dim)
        
    # stack x0...xt-1 and x1...xt (seq_len-1, 2,32,32) -> (seq_len-1, 4 ,32,32)
    def stack_y(self, y):
#         print("shape of y:", y.shape)
        # x0 -> xt-1
        seq1 = np.insert(y.cpu(), 0, initial, axis = 0)[:-1].to(device)
#         print("y before stacking: ", seq1.shape)
        # x1 -> xt
        seq3 = torch.cat((seq1, y), 1)
#         print("y after stacking: ", seq3.shape)
        return seq3
    
    def data_to_z_params(self, x, y):
        """Helper to batch together some steps of the process."""
        rs_all = None
        for i,theta_seq in enumerate(y):
#             print("shape of data: ", y.shape)
            y_stacked = self.stack_y(theta_seq)
#             print(y_stacked.shape)
            y_conv_c = self.conv_encoder(y_stacked)
            encode_hidden_state = None
#             print(y_conv_c.shape)
    #         print("shape of y after conv layer: ", y_conv_c.shape)
            # corresponding theta to current y: x[i]
            xy = torch.cat([y_conv_c, x[i].repeat(len(y_stacked)).reshape(-1,x_dim)], dim=1)
#             print("shape of xy: ", xy.shape)
            rs , encode_hidden_state = self.encoder_lstm(xy, encode_hidden_state)
#             self.lstm_linear(rs)
            rs = rs.unsqueeze(0)
#             print("shape of rs: ", rs.shape)
            if rs_all is None:
                rs_all = rs
            else:
                rs_all = torch.vstack((rs_all, rs))
            
#         print("shape of rs_all: ", rs_all.shape)
        r_agg = rs_all.mean(dim=0) # Average over samples
#         print("shape of r_agg: ", r_agg.shape)
        return self.z_encoder(r_agg) # Get mean and variance for q(z|...)
    
    def sample_z(self, mu, logvar,n=1):
        """Reparameterisation trick."""
        if n == 1:
            eps = torch.autograd.Variable(logvar.data.new(z_dim).normal_()).to(device)
        else:
            eps = torch.autograd.Variable(logvar.data.new(n,z_dim).normal_()).to(device)
        
        # std = torch.exp(0.5 * logvar)
        std = 0.1+ 0.9*torch.sigmoid(logvar)
#         print(mu + std * eps)
        return mu + std * eps

    def KLD_gaussian(self):
        """Analytical KLD between 2 Gaussians."""
        mu_q, logvar_q, mu_p, logvar_p = self.z_mu_all, self.z_logvar_all, self.z_mu_context, self.z_logvar_context

        std_q = 0.1+ 0.9*torch.sigmoid(logvar_q)
        std_p = 0.1+ 0.9*torch.sigmoid(logvar_p)
        p = torch.distributions.Normal(mu_p, std_p)
        q = torch.distributions.Normal(mu_q, std_q)
        return torch.distributions.kl_divergence(q, p).sum()
    
    # decoder for the model, need zs(array of [[mean], [var]], length is seq_length)
    def decoder(self, theta, z_mu, z_log, seq_len=4, prev_pred = None):
        # initialize prev_pred
        # if not training, get a initial pic!
        if (prev_pred is None):
            prev_pred = self.y_init
       
        outputs = None
        encoded_states = None
        deconv_encoder_hidden_state = None
#         theta_encoded = self.theta_fc_in_decoder(theta)
#         print("shape of z_mu: ", z_mu.shape)


        
        for i in range(seq_len):
            # encode image to hidden (r)
            convEncoded = self.conv_encoder_in_decoder(prev_pred)
            # conv_outDim -> 1, 4
#             convEncoded = self.reduce_dm_decoder(convEncoded)
    #         print(theta.shape)

            # append theta to every timestamp
            tempTensor = torch.empty(conv_outDim+x_dim+z_dim).to(device)
            tempTensor[:conv_outDim] = convEncoded
#             get the z sample in corresponding timestamp
            tempTensor[conv_outDim:-x_dim] = self.sample_z(z_mu[i], z_log[i])
            tempTensor[-x_dim:] = theta
            
            if encoded_states is None:
                encoded_states = tempTensor
                convEncoded = torch.unsqueeze(tempTensor, 0)
            else:
                encoded_states = torch.vstack((encoded_states, tempTensor))
                convEncoded = encoded_states            
        
#             print(convEncoded.shape)
            # 4+z_dim+x_dim


            output, deconv_encoder_hidden_state = self.decoder_lstm(convEncoded, deconv_encoder_hidden_state)
    #             output = self.fc_conv_de_to_hidden(output[-1])
            # end of convlstm in decoder
    #         print("shape of output: ", output.shape)



            #start of deconv
    #             output = self.fc_deconv_de_to_hidden(output)
            # final image predicted
            outputs = self.deconv(output)
            outputs = outputs.unsqueeze(1)            
            # update prev_pred to the prediction
            prev_pred = outputs[-1]
#             print("outputs shape: ", outputs.shape)
    #         outputs.append(output)
    #         outputs = torch.stack(outputs, dim=0)
    #         print("shape of final output: ", output.shape)
            
        return outputs
        

    def forward(self, x_t, x_c, y_c, x_ct, y_ct):
        """
        """

        self.z_mu_all, self.z_logvar_all = self.data_to_z_params(x_ct, y_ct)
        self.z_mu_context, self.z_logvar_context = self.data_to_z_params(x_c, y_c)
#         print("shape of z_mu_all: ", self.z_mu_all.shape)
        outputs = []
        for target in x_t:
            output = self.decoder(target, self.z_mu_all, self.z_logvar_all)
            outputs.append(output)
        outputs = torch.stack(outputs, dim=0)
#         self.zs = self.sample_z(self.z_mu_all, self.z_logvar_all)
#         print("shape of zs: ", self.zs.shape)
        return outputs
    


# In[35]:


# all good, no additional modification needed
def random_split_context_target(x,y, n_context):
    """Helper function to split randomly into context and target"""
    ind = np.arange(x.shape[0])
    mask = np.random.choice(ind, size=n_context, replace=False)
    return x[mask], y[mask], np.delete(x, mask, axis=0), np.delete(y, mask, axis=0)

def sample_z(mu, logvar,n=1):
    """Reparameterisation trick."""
    if n == 1:
        eps = torch.autograd.Variable(logvar.data.new(z_dim).normal_())
    else:
        eps = torch.autograd.Variable(logvar.data.new(n,z_dim).normal_())
    
    std = 0.1+ 0.9*torch.sigmoid(logvar)
#     print(mu + std * eps)
    return mu + std * eps

def data_to_z_params(x, y, calc_score = False):
    """Helper to batch together some steps of the process."""
    rs_all = None
    for i,theta_seq in enumerate(y):
        if calc_score:
            theta_seq = torch.cat([decoder_init, theta_seq])
        y_stacked = dcrnn.stack_y(theta_seq)
        y_conv_c = dcrnn.conv_encoder(y_stacked)
        encode_hidden_state = None
#             print(y_conv_c.shape)
#         print("shape of y after conv layer: ", y_conv_c.shape)
        # corresponding theta to current y: x[i]
        xy = torch.cat([y_conv_c, x[i].repeat(len(y_stacked)).reshape(-1,x_dim)], dim=1)
#             print("shape of xy: ", xy.shape)
        rs , encode_hidden_state = dcrnn.encoder_lstm(xy, encode_hidden_state)
#             self.lstm_linear(rs)
        rs = rs.unsqueeze(0)
#             print("shape of rs: ", rs.shape)
        if rs_all is None:
            rs_all = rs
        else:
            rs_all = torch.vstack((rs_all, rs))

#         print("shape of rs_all: ", rs_all.shape)
    r_agg = rs_all.mean(dim=0) # Average over samples
#         print("shape of r_agg: ", r_agg.shape)
    return dcrnn.z_encoder(r_agg) # Get mean and variance for q(z|...)

def test(x_train, y_train, x_test):
    with torch.no_grad():
        z_mu, z_logvar = data_to_z_params(x_train.to(device),y_train.to(device))
      
        output_list = None
        for i in range (len(x_test)):
        #           zsamples = sample_z(z_mu, z_logvar) 
            output = dcrnn.decoder(x_test[i:i+1].to(device), z_mu, z_logvar).cpu().unsqueeze(0)
            if output_list is None:
                output_list = output.detach()
            else:
                output_list = torch.vstack((output_list, output.detach()))
    
    return output_list.numpy()


# In[36]:


def train(n_epochs, x_train, y_train, x_val, y_val, x_test, y_test, n_display=500, patience = 5000): #7000, 1000
    train_losses = []
    mae_losses = []
    kld_losses = []
    val_losses = []
    test_losses = []

    means_test = []
    stds_test = []
    min_loss = 0. # for early stopping
    wait = 0
    min_loss = float('inf')
    dcrnn.train()
    
    for t in range(n_epochs): 
        opt.zero_grad()
        #Generate data and process
        x_context, y_context, x_target, y_target = random_split_context_target(
                                x_train, y_train, int(len(y_train)*0.2)) #0.25, 0.5, 0.05,0.015, 0.01
#         print(x_context.shape, y_context.shape, x_target.shape, y_target.shape)    

        # for overfitting use val as context, for actual training, use code above to split context!
#         x_context = x_train
#         y_context = y_train
#         x_target  = x_train
#         y_target  = y_train

        x_c = torch.from_numpy(x_context).float().to(device)
        x_t = torch.from_numpy(x_target).float().to(device)
        y_c = torch.from_numpy(y_context).float().to(device)
        y_t = torch.from_numpy(y_target).float().to(device)

        x_ct = torch.cat([x_c, x_t], dim=0).float().to(device)
        y_ct = torch.cat([y_c, y_t], dim=0).float().to(device)

        y_pred = dcrnn(x_t, x_c, y_c, x_ct, y_ct)
        
#         print("shape of y_pred: ", y_pred.shape)
#         print("shape of y_t: ", y_t.shape)

        train_loss = MAE(y_pred, y_t) + dcrnn.KLD_gaussian()
        mae_loss = MAE(y_pred, y_t) / scale_std_y
        kld_loss = dcrnn.KLD_gaussian()
        
        train_loss.backward()
        torch.nn.utils.clip_grad_norm_(dcrnn.parameters(), 5) #10
        opt.step()
        
        #val loss
        y_val_pred = test(torch.from_numpy(x_train).float(),torch.from_numpy(y_train).float(),
                      torch.from_numpy(x_val).float())
#         print("shape of y_val_pred: ", y_val_pred.shape)
#         print("shape of y_val: ", y_val.shape)
        val_loss = MAE(torch.from_numpy(y_val_pred).float(),torch.from_numpy(y_val).float()) 
        #test loss
        y_test_pred = test(torch.from_numpy(x_train).float(),torch.from_numpy(y_train).float(),
                      torch.from_numpy(x_test).float())
        test_loss = MAE(torch.from_numpy(y_test_pred).float(),torch.from_numpy(y_test).float()) 

        if t % n_display ==0:
            print('train loss:', train_loss.item(), 'mae:', mae_loss.item(), 'kld:', kld_loss.item(), flush=True)
            print('val loss:', val_loss.item(), 'test loss:', test_loss.item(), flush=True)
            
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print("Current Time =", current_time, flush=True)
            
            ypred_allset.append(y_pred)
#             print(y_train)

        if t % (n_display/10) ==0:
            train_losses.append(train_loss.item())
            val_losses.append(val_loss.item())
            test_losses.append(test_loss.item())
#             mae_losses.append(mae_loss.item())
#             kld_losses.append(kld_loss.item())
        
#         if train_loss.item() < 10:
#             return train_losses, val_losses, test_losses, dcrnn.z_mu_all, dcrnn.z_logvar_all
        
#         #early stopping
        if val_loss < min_loss:
            wait = 0
            min_loss = val_loss
            
        elif val_loss >= min_loss:
            wait += 1
            if wait == patience:
                print('Early stopping at epoch: %d' % t)
                return train_losses, val_losses, test_losses, dcrnn.z_mu_all, dcrnn.z_logvar_all
        
    return train_losses, val_losses, test_losses, dcrnn.z_mu_all, dcrnn.z_logvar_all


# In[74]:


r_dim = 64
z_dim = 64 #8
x_dim = 3 #
y_dim = 1
# N = 100000 #population

ypred_allset = []
ypred_testset = []
mae_allset = []
maemetrix_allset = []
mae_testset = []
score_set = []
mask_set = []

#number of parameters
dcrnn = DCRNNModel(x_dim, y_dim, r_dim, z_dim).to(device)
opt = torch.optim.Adam(dcrnn.parameters(), 1e-3) #1e-3
pytorch_total_params = sum(p.numel() for p in dcrnn.parameters() if p.requires_grad)
print(pytorch_total_params)


# In[75]:


dcrnn.train()
train_losses, val_losses, test_losses, z_mu, z_logvar = train(10000,x_all,y_all,x_val, y_val, x_test, y_test,500, 1500) #20000, 5000


# In[11]:


np.save("./stnp_train_losses_%d" % seed,train_losses)
np.save("./stnp_val_losses_%d" % seed,val_losses)
np.save("./stnp_test_losses_%d" % seed,test_losses)
torch.save(dcrnn.state_dict(), "./stnp_offline_%d.pt" % seed)
print("training done, all results saved")


# In[ ]:




