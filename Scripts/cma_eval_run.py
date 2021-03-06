from __future__ import print_function, division
from ML_DL_Project.Scripts.spatial_transforms import (Compose, ToTensor, CenterCrop, Scale, Normalize, MultiScaleCornerCrop,
                                RandomHorizontalFlip)
from torch.autograd import Variable
from ML_DL_Project.Scripts.cmaModel import *
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
from ML_DL_Project.Scripts.cma_makeDatasetTwoStream import * 
import argparse

def main_run(dataset, model_state_dict, dataset_dir, stackSize, seqLen, memSize):

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

    testBatchSize = 1
    spatial_transform = Compose([Scale(256), CenterCrop(224), ToTensor(), normalize])

    vid_seq_test = cma_makeDataset2Stream(dataset_dir,spatial_transform=spatial_transform,
                                sequence=True, numSeg=1, stackSize=stackSize, fmt='.png', seqLen=seqLen,phase='Test')

    test_loader = torch.utils.data.DataLoader(vid_seq_test, batch_size=testBatchSize,
                            shuffle=False, num_workers=2, pin_memory=True)
    
    actions =vid_seq_test.__getLabel__()

    model = crossAttentionModel(stackSize=5, memSize=512, num_classes=num_classes)
    model.load_state_dict(torch.load(model_state_dict))


    for params in model.parameters():
        params.requires_grad = False

    model.train(False)
    model.cuda()

    test_samples = vid_seq_test.__len__()
    print('Number of samples = {}'.format(test_samples))
    print('Evaluating...')
    numCorrTwoStream = 0

    predicted_labels = []
    true_labels = []
    with torch.no_grad():
      for j, (inputFlow, inputFrame, targets) in enumerate(test_loader):
          inputVariableFrame = inputFrame.permute(1, 0, 2, 3, 4).to(DEVICE)
          inputVariableFlow = inputFlow.permute(1, 0, 2, 3, 4).to(DEVICE)
          output_label = model(inputVariableFlow, inputVariableFrame)
          _, predictedTwoStream = torch.max(output_label.data, 1)
          numCorrTwoStream += (predictedTwoStream == targets.to(DEVICE)).sum()
          predicted_labels.append(predictedTwoStream.cpu())
          true_labels.append(targets)
    test_accuracyTwoStream = (numCorrTwoStream / test_samples) * 100

    cnf_matrix = confusion_matrix(true_labels, predicted_labels).astype(float)
    cnf_matrix_normalized = cnf_matrix / cnf_matrix.sum(axis=1)[:, np.newaxis]

    print('Accuracy {:.02f}%'.format(test_accuracyTwoStream))

    ticks = [str(action + str(i) ) for i, action in enumerate(actions)]
    plt.figure(figsize=(20,20))
    plt.imshow(cnf_matrix_normalized, interpolation='none', cmap='Greens')
    plt.colorbar()
    plt.xticks(np.arange(num_classes),labels = set(ticks), fontsize=10, rotation = 90)
    plt.yticks(np.arange(num_classes),labels = set(ticks), fontsize=10)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.grid(True)
    plt.clim(0, 1)
    plt.savefig(dataset + '-twoStreamJoint.jpg', bbox_inches='tight')
    plt.show()

def __main__(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='gtea61', help='Dataset')
    parser.add_argument('--datasetDir', type=str, default='./dataset/gtea_warped_flow_61/split2/test',
                        help='Dataset directory')
    parser.add_argument('--modelStateDict', type=str, default='./models/gtea61/best_model_state_dict_twoStream_split2.pth',
                        help='Model path')
    parser.add_argument('--seqLen', type=int, default=25, help='Length of sequence')
    parser.add_argument('--stackSize', type=int, default=5, help='Number of optical flow images in input')
    parser.add_argument('--memSize', type=int, default=512, help='ConvLSTM hidden state size')

    #args = parser.parse_args()
    args, _ = parser.parse_known_args(argv)
    
    dataset = args.dataset
    model_state_dict = args.modelStateDict
    dataset_dir = args.datasetDir
    seqLen = args.seqLen
    stackSize = args.stackSize
    memSize = args.memSize


    main_run(dataset, model_state_dict, dataset_dir, stackSize, seqLen, memSize)
#__main__()
