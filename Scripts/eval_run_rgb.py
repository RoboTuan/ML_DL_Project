from __future__ import print_function, division
from ML_DL_Project.Scripts.objectAttentionModelConvLSTM import *
from ML_DL_Project.Scripts.spatial_transforms import (Compose, ToTensor, CenterCrop, Scale, Normalize, MultiScaleCornerCrop,
                                RandomHorizontalFlip)
from ML_DL_Project.Scripts.makeDatasetRGB import *
from ML_DL_Project.Scripts.convLSTMmodel import *
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import argparse
import sys

def main_run(dataset, model_state_dict, dataset_dir, seqLen, memSize, attention):

    if dataset == 'gtea61':
        num_classes = 61
    elif dataset == 'gtea71':
        num_classes = 71
    elif dataset == 'gtea_gaze':
        num_classes = 44
    elif dataset == 'egtea':
        num_classes = 106
    else:
        print('Dataset not found')
        sys.exit()

    DEVICE = "cuda"

    mean=[0.485, 0.456, 0.406]
    std=[0.229, 0.224, 0.225]

    normalize = Normalize(mean=mean, std=std)
    spatial_transform = Compose([Scale(256), CenterCrop(224), ToTensor(), normalize])

    vid_seq_test = makeDataset(dataset_dir,
                               spatial_transform=spatial_transform,
                               seqLen=seqLen, fmt='.png')
    actions =vid_seq_test.__getLabel__()

    test_loader = torch.utils.data.DataLoader(vid_seq_test, batch_size=1,
                            shuffle=False, num_workers=2, pin_memory=True)
    if attention==True:

      model = attentionModel(num_classes=num_classes, mem_size=memSize)
    else:

      model= clstm_Model(num_classes=num_classes, mem_size=memSize)
    
    
    model.load_state_dict(torch.load(model_state_dict))

    for params in model.parameters():
        params.requires_grad = False

    model.train(False)
    model.cuda()
    test_samples = vid_seq_test.__len__()
    print('Number of samples = {}'.format(test_samples))
    print('Evaluating...')
    numCorr = 0
    true_labels = []
    predicted_labels = []
    #Controllare se lasciarla così o togliere il contatore chiave
    with torch.no_grad():
        for j, (inputs, targets) in enumerate(test_loader):
            inputVariable = inputs.permute(1, 0, 2, 3, 4).to(DEVICE)
            output_label, _ = model(inputVariable)
            _, predicted = torch.max(output_label.data, 1)
            numCorr += (predicted == targets.to(DEVICE)).sum()
            true_labels.append(targets)
            #.cpu() because confusion matrix is from scikit-learn
            predicted_labels.append(predicted.cpu())
            
    test_accuracy = (numCorr / test_samples) * 100
    print('Test Accuracy = {}%'.format(test_accuracy))     

    # ebug
    print(true_labels)
    print(predicted_labels)





    cnf_matrix = confusion_matrix(true_labels, predicted_labels).astype(float)
    cnf_matrix_normalized = cnf_matrix / cnf_matrix.sum(axis=1)[:, np.newaxis]


    #ticks = np.linspace(0, 60, num=61)
    ticks = [str(action + str(i) ) for i, action in enumerate(actions)]
    plt.figure(figsize=(20,20))
    plt.imshow(cnf_matrix_normalized, interpolation='none', cmap='binary')
    plt.colorbar()
    plt.xticks(np.arange(num_classes),labels = set(ticks), fontsize=10, rotation = 90)
    plt.yticks(np.arange(num_classes),labels = set(ticks), fontsize=10)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.grid(True)
    plt.clim(0, 1)
    plt.savefig(dataset + '-rgb.jpg', bbox_inches='tight')
    plt.show()

def __main__(argv=None):
    parser = argparse.ArgumentParser(prog='myprogram', description='Foo')
    parser.add_argument('--dataset', type=str, default='gtea61', help='Dataset')
    parser.add_argument('--datasetDir', type=str, default='./dataset/gtea_warped_flow_61/split2/test',
                        help='Dataset directory')
    parser.add_argument('--modelStateDict', type=str, default='./models/gtea61/best_model_state_dict_rgb_split2.pth',
                        help='Model path')
    parser.add_argument('--seqLen', type=int, default=25, help='Length of sequence')
    parser.add_argument('--memSize', type=int, default=512, help='ConvLSTM hidden state size')
    parser.add_argument('--attention', type=bool, default=True, help='Choose between model with or without spatial attention')

    #args = parser.parse_args()
    args, _ = parser.parse_known_args(argv)
    
    dataset = args.dataset
    model_state_dict = args.modelStateDict
    dataset_dir = args.datasetDir
    seqLen = args.seqLen
    memSize = args.memSize
    attention=args.attention

    main_run(dataset, model_state_dict, dataset_dir, seqLen, memSize, attention)
#__main__()
