"""
An implement of ResNet on cifar10 dataset.
"""

from keras.datasets import  cifar10
from keras.preprocessing.image import ImageDataGenerator
from keras.utils import np_utils
from keras.callbacks import ReduceLROnPlateau, CSVLogger,EarlyStopping,TensorBoard,ModelCheckpoint

import numpy as np
import resnet

# Reduce learning rate.
lr_reducer = ReduceLROnPlateau(factor=np.sqrt(0.1),cooldown=0,patience=5,min_lr=0.5e-6)
early_stopper = EarlyStopping(min_delta=0.001,patience=10)
csv_logger = CSVLogger('resnet18_cifar10.csv')

batch_size = 32
nb_classes = 10
nb_epoch = 100
data_augmentation = True

#input image dimensions
image_rows, image_cols = 32,32
image_channels = 3

# Load data
(X_train,Y_train),(X_test,Y_test)=cifar10.load_data()

# Convert label to one-hot
Y_train = np_utils.to_categorical(Y_train,nb_classes)
Y_test=np_utils.to_categorical(Y_test,nb_classes)

X_train=X_train.astype('float32')
X_test=X_test.astype('float32')

# Centerilize and Normalize
mean_image = np.mean(X_train,axis=0)
X_train = X_train-mean_image
X_test =X_test - mean_image
X_train/=128.
X_test/=128.

model = resnet.ResNetBuilder.build_resnet_18((image_channels,image_rows,image_cols),nb_classes)
model.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'])

# Use tensorboard
tbCallBack=TensorBoard(log_dir='./logs',write_grads=True,write_graph=True,write_images=True)


if not data_augmentation:
    print("Not using data augmentation.")
    model.fit(X_train,Y_train,batch_size=batch_size,nb_epoch=nb_epoch,
              validation_data=(X_test,Y_test),
              shuffle=True,
              callbacks=[lr_reducer, early_stopper, csv_logger,tbCallBack])

else:
    print("Using real-time data augmentation.")
    # This will do prepocessing and realtime data augmentation.
    datagen = ImageDataGenerator(
        featurewise_center=False, # set input mean to 0 over the dataset
        samplewise_center=False, #set each sample mean to 0
        featurewise_std_normalization=False, #devide inputs by std of the dataset
        samplewise_std_normalization=False, #devide each input by its std
        zca_whitening=False, # apply ZCA whitening
        rotation_range=0,   #randomly rotate images in the range(degrees, 0 to 180)
        width_shift_range=0.1, # randomly shift images horizontally (fraction of total width)
        height_shift_range=0.1, # randomly shift images vertically (fraction of total height)
        horizontal_flip=True, # randomly flip images
        vertical_flip=False) #radomly flip images

    # Compute quantities required for featurewise normalization
    # (std, mean, and principal components if ZCA whitening is applied).
    datagen.fit(X_train)

    # Fit the model on the batches generated by datagen.flow().
    model.fit_generator(datagen.flow(X_train,Y_train,batch_size=batch_size),
                        steps_per_epoch=X_train.shape[0]//batch_size, # // means Round down
                        validation_data=(X_test, Y_test),
                        epochs=nb_epoch, verbose=1, max_q_size=100,
                        callbacks=[lr_reducer, early_stopper, csv_logger,tbCallBack])

















