'''Train ImageNet with PyTorch.

e.g.
    python3 imagenet.py --netName=PreActResNet18 --imagenet=1000 --bs=512
'''
from __future__ import print_function

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.backends.cudnn as cudnn

import torchvision
import torchvision.transforms as transforms

import os
import argparse

from imagenetLoad import ImageNetDownSample
from models import *
from utils import *

os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1,2,3"
parser = argparse.ArgumentParser(description='PyTorch Imagenet32 Training')
parser.add_argument('--lr', default=0.1, type=float, help='learning rate')
parser.add_argument('--resume', '-r',default=False, action='store_true', help='resume from checkpoint')
parser.add_argument('--netName', default='PreActResNet18', type=str, help='choosing network')
parser.add_argument('--bs', default=512, type=int, help='batch size')
parser.add_argument('--es', default=300, type=int, help='epoch size')
parser.add_argument('--imagenet', default=1000, type=int, help='dataset classes number')
parser.add_argument('--datapath', default='/home/xm0036/Datasets/ImageNet32', type=str, help='dataset path')
args = parser.parse_args()


device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(device)
best_acc = 0  # best test accuracy
start_epoch = 0  # start from epoch 0 or last checkpoint epoch


# Data
print('==> Preparing data..')
transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
])


trainset = ImageNetDownSample(root=args.datapath, train=True, transform=transform_train)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=args.bs, shuffle=True, num_workers=4)

testset = ImageNetDownSample(root=args.datapath, train=False, transform=transform_test)
testloader = torch.utils.data.DataLoader(testset, batch_size=args.bs, shuffle=False, num_workers=4)


# Model
print('==> Building model..')
# More models are avaliable in models folder
if args.netName=='PreActResNet18': net = PreActResNet18(num_classes=args.imagenet)
elif args.netName=='SEResNet18': net = SEResNet18(num_classes=args.imagenet)
elif args.netName=='SEResNet34': net = SEResNet34(num_classes=args.imagenet)
elif args.netName=='PSEResNet18': net = PSEResNet18(num_classes=args.imagenet)
elif args.netName=='SPPSEResNet18': net = SPPSEResNet18(num_classes=args.imagenet)
elif args.netName=='PSPPSEResNet18': net = PSPPSEResNet18(num_classes=args.imagenet)
else:
    args.netName = PreActResNet18
    net = PreActResNet18()
    print("\n=====NOTICING:=======\n")
    print("=====Not a valid netName, using default PreActResNet18=====\n\n")

para_numbers = count_parameters(net)
print("Total parameters number is: "+ str(para_numbers))

net = net.to(device)

if device == 'cuda':
    net = torch.nn.DataParallel(net)
    cudnn.benchmark = True

if args.resume:
    # Load checkpoint.
    print('==> Resuming from checkpoint..')
    assert os.path.isdir('checkpoint'), 'Error: no checkpoint directory found!'
    checkpoint_path = './checkpoint/ckpt_imagenet32_'+args.netName+'.t7'
    checkpoint = torch.load(checkpoint_path)
    net.load_state_dict(checkpoint['net'])
    best_acc = checkpoint['acc']
    print("BEST_ACCURACY: "+str(best_acc))
    start_epoch = checkpoint['epoch']

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(net.parameters(), lr=args.lr, momentum=0.9, weight_decay=5e-4)


# Training
def train(epoch):
    adjust_learning_rate(optimizer, epoch, args.lr)
    print('\nEpoch: %d   Learning rate: %f' % (epoch, optimizer.param_groups[0]['lr']))
    print("\nAllocated GPU memory:", torch.cuda.memory_allocated())
    net.train()
    train_loss = 0
    correct = 0
    total = 0



    for batch_idx, (inputs, targets) in enumerate(trainloader):
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = net(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()

        progress_bar(batch_idx, len(trainloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)'
            % (train_loss/(batch_idx+1), 100.*correct/total, correct, total))

    file_path='records/imagenet32_' +args.netName+'_train.txt'
    record_str=str(epoch)+'\t'+"%.3f"%(train_loss/(batch_idx+1))+'\t'+"%.3f"%(100.*correct/total)+'\n'
    write_record(file_path,record_str)


def test(epoch):
    global best_acc
    net.eval()
    test_loss = 0
    correct = 0
    total = 0
    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(testloader):
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = net(inputs)
            loss = criterion(outputs, targets)

            test_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

            progress_bar(batch_idx, len(testloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)'
                % (test_loss/(batch_idx+1), 100.*correct/total, correct, total))

    file_path = 'records/imagenet32_' +args.netName+ '_test.txt'
    record_str = str(epoch) + '\t' + "%.3f" % (test_loss / (batch_idx + 1)) + '\t' + "%.3f" % (
                100. * correct / total) + '\n'
    write_record(file_path, record_str)

    # Save checkpoint.
    acc = 100.*correct/total
    if acc > best_acc:
        print('Saving..')
        state = {
            'net': net.state_dict(),
            'acc': acc,
            'epoch': epoch,
        }
        if not os.path.isdir('checkpoint'):
            os.mkdir('checkpoint')
        save_path = './checkpoint/ckpt_imagenet32_' + args.netName + '.t7'
        torch.save(state, save_path)
        best_acc = acc


for epoch in range(start_epoch, start_epoch+args.es):
    train(epoch)
    test(epoch)


# write statistics to files
statis_path = 'records/STATS_'+args.netName+'.txt'
if not os.path.exists(statis_path):
    # os.makedirs(statis_path)
    os.system(r"touch {}".format(statis_path))
f = open(statis_path, 'w')
statis_str="============\nDivces:"+device+"\n"
statis_str+='\n===========\nargs:\n'
statis_str+=args.__str__()
statis_str+='\n==================\n'
statis_str+="BEST_accuracy: "+str(best_acc)
statis_str+='\n==================\n'
statis_str+="Total parameters: "+str(para_numbers)
f.write(statis_str)
f.close()