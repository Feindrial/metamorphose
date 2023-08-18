import numpy as np
import tensorflow as tf
import keras
from keras import layers
from tensorflow.keras import datasets, layers, models
from keras.layers import GlobalAveragePooling2D
from keras.layers import Dense
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2
from tensorflow.keras.applications import MobileNetV3Small
import os
from pathlib import Path
from imutils import paths
import cv2
from matplotlib import pyplot as plt

input_shape =  (224, 224, 3)
batch_size = 32
time_dist = 10

org_path = Path(r"C:\Users\SWQA\Desktop\STAJ\Metamorphose\Videos\1")
class_paths = [Path(r"class08_30_20"), Path(r"classsenay_1"), Path(r"class16_46_57")]

def __data_gen(wtype, iclass):
    imgs = []    
    lbls = []
    img_dist = []
    lbl_dist = []
    
    bcounter = 0
    tcounter = 0
    
    seed = 0
    for c in wtype:
        seed += ord(c)
    
    np.random.seed(seed)
    shuffled = np.asarray(list(os.walk(org_path / iclass / wtype))[0][2])
    # np.random.shuffle(shuffled)
    for p in shuffled:
        img = cv2.imread(str(org_path / iclass / wtype / p), cv2.IMREAD_COLOR)
        img = cv2.resize(img, input_shape[:-1])
        
        img_dist.append(img)
        
        if os.path.isfile(org_path / iclass / wtype / "Label" / p):
            lbl_dist.append([1])
        else:
            lbl_dist.append([0])

        tcounter += 1

        if tcounter % time_dist == 0:
            tcounter = 0
            bcounter += 1
            imgs.append(np.asarray(img_dist, dtype=np.uint8))
            lbls.append(np.asarray(lbl_dist, dtype=np.uint8))
            img_dist = []
            lbl_dist = []
            if bcounter % batch_size == 0:
                bcounter = 0
                yield (np.asarray(imgs, dtype=np.uint8), np.asarray(lbls, dtype=np.uint8))
                imgs = []
                lbls = []
    

        
    if bcounter != 0:
        yield (np.asarray(imgs, dtype=np.uint8), np.asarray(lbls, dtype=np.uint8))

def load_data():
    signature = (tf.TensorSpec(shape=(batch_size, time_dist, *input_shape), dtype=tf.uint8),
                 tf.TensorSpec(shape=(batch_size, time_dist, 1), dtype=tf.uint8))
    
    for iclass in class_paths:
        trdir_path = org_path / iclass / "Train"
        valdir_path = org_path / iclass / "Val"
        tedir_path = org_path / iclass / "Test"
        
        train_dataset = tf.data.Dataset.from_generator(
            lambda: __data_gen("Train", iclass),
            output_signature=signature
        )

        val_dataset = tf.data.Dataset.from_generator(
            lambda: __data_gen("Val", iclass),
            output_signature=signature
        )

        test_dataset = tf.data.Dataset.from_generator(
            lambda: __data_gen("Test", iclass),
            output_signature=signature
        )
        
        return train_dataset, val_dataset, test_dataset
    
a, b, c = load_data()

for asd in a:
    print(type(asd))
    print(asd)
    break