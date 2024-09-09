### Code: https://docs.habana.ai/en/latest/PyTorch/Getting_Started_with_PyTorch_and_Gaudi/Getting_Started_with_PyTorch.html

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torchvision
import torchvision.transforms as transforms
import os
import time
# Import Habana Torch Library
import habana_frameworks.torch.core as htcore
import numpy as np

class SimpleModel(nn.Module):
    def __init__(self):
        super(SimpleModel, self).__init__()

        self.fc1   = nn.Linear(784, 1024)
        self.fc2   = nn.Linear(1024, 512)
        self.fc3   = nn.Linear(512, 10)

    def forward(self, x):

        out = x.view(-1,28*28)
        out = F.relu(self.fc1(out))
        out = F.relu(self.fc2(out))
        out = self.fc3(out)

        return out

def train(net,criterion,optimizer,trainloader,device):

    net.train()
    train_loss = 0.0
    correct = 0
    total = 0

    for batch_idx, (data, targets) in enumerate(trainloader):

        data, targets = data.to(device), targets.to(device)

        optimizer.zero_grad()
        outputs = net(data)
        loss = criterion(outputs, targets)

        loss.backward()
        
        # API call to trigger execution
        htcore.mark_step()
        
        optimizer.step()

        # API call to trigger execution
        htcore.mark_step()

        train_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()

    train_loss = train_loss/(batch_idx+1)
    train_acc = 100.0*(correct/total)
    print("Training loss is {} and training accuracy is {}".format(train_loss,train_acc))

def test(net,criterion,testloader,device):

    net.eval()
    test_loss = 0
    correct = 0
    total = 0

    with torch.no_grad():

        for batch_idx, (data, targets) in enumerate(testloader):

            data, targets = data.to(device), targets.to(device)

            outputs = net(data)
            loss = criterion(outputs, targets)

            # API call to trigger execution
            htcore.mark_step()

            test_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

    test_loss = test_loss/(batch_idx+1)
    test_acc = 100.0*(correct/total)
    print("Testing loss is {} and testing accuracy is {}".format(test_loss,test_acc))

    return test_acc
    
def main():

    epochs = 20
    batch_size = 512
    lr = 0.01
    milestones = [10,15]
    load_path = './data'
    save_path = './checkpoints'

    if(not os.path.exists(save_path)):
        os.makedirs(save_path)
    
    # Target the Gaudi HPU device
    device = torch.device("hpu")
    
    # Data
    transform = transforms.Compose([
        transforms.ToTensor(),
    ])

    trainset = torchvision.datasets.MNIST(root=load_path, train=True,
                                            download=True, transform=transform)
    trainloader = torch.utils.data.DataLoader(trainset, batch_size=batch_size,
                                            shuffle=True, num_workers=2)
    testset = torchvision.datasets.MNIST(root=load_path, train=False,
                                        download=True, transform=transform)
    testloader = torch.utils.data.DataLoader(testset, batch_size=batch_size,
                                            shuffle=False, num_workers=2)

    net = SimpleModel()
    net.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=lr,
                        momentum=0.9, weight_decay=5e-4)
    scheduler = torch.optim.lr_scheduler.MultiStepLR(optimizer, milestones=milestones, gamma=0.1)

    time_list = []
    acc_list = []

    for epoch in range(1, epochs+1):
        print("=====================================================================")
        print("Epoch : {}".format(epoch))
        start_time = time.time()
        train(net,criterion,optimizer,trainloader,device)
        test_acc = test(net,criterion,testloader,device)
        end_time = time.time()
        print("Time :", end_time-start_time)
        torch.save(net.state_dict(), os.path.join(save_path,'epoch_{}.pth'.format(epoch)))

        time_list.append(end_time-start_time)
        acc_list.append(test_acc)
        
        scheduler.step()
    
    np.save('vision_time.npy', np.array(time_list))
    np.save('vision_acc.npy', np.array(acc_list))

if __name__ == '__main__':
    main()