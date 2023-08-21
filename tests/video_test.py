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
batch_size = 64
time_dist = 8
trsplit = (0.0, 0.7)
valsplit = (0.7, 0.85)
tesplit = (0.85, 1.0)

org_path = Path(r"C:\Users\SWQA\Desktop\STAJ\Metamorphose\Videos\1")
class_paths = [Path(r"class08_30_20"), Path(r"classsenay_1"), Path(r"class16_46_57")]

def ins_ind(string, char, index):
        return string[:index] + char + string[index:] 

def __data_gen(wtype, iclass, split):    
    imgs = []    
    lbls = []
    weights = []
    img_dist = []
    lbls = []
    weight_dist = []
    
    bcounter = 0
    
    seed = 0
    for c in wtype:
        seed += ord(c)
    
    np.random.seed(seed)
    shuffled = np.asarray(sorted(list(os.walk(org_path / class_paths[0] / "Train"))[0][2], key=lambda x: len(x)))
    shuffled = shuffled[int(len(shuffled) * split[0]):int(len(shuffled) * split[1])]
    # np.random.shuffle(shuffled)

    #unroll
    for p in shuffled[:time_dist]:        
        img = cv2.imread(str(org_path / iclass / wtype / p), cv2.IMREAD_COLOR)
        img = cv2.resize(img, input_shape[:-1])
        
        img_dist.append(img)


    if os.path.isfile(org_path / iclass / wtype / "Label" / shuffled[time_dist]):
        lbls.append([1, 1])
    elif os.path.isfile(org_path / iclass / wtype / "Label" / ins_ind(shuffled[time_dist], 'l', shuffled[time_dist].index('.'))):
        lbls.append([1, 0])
    elif os.path.isfile(org_path / iclass / wtype / "Label" / ins_ind(shuffled[time_dist], 'e', shuffled[time_dist].index('.'))):
        lbls.append([0, 1])
    else:
        lbls.append([0, 0])


    imgs.append(np.asarray(img_dist, dtype=np.uint8))    

    bcounter += 1

    for p in range(time_dist, len(shuffled) - 1):
        img_index = shuffled[p]
        lbl_index = shuffled[p + 1]

        img = cv2.imread(str(org_path / iclass / wtype / img_index), cv2.IMREAD_COLOR)
        img = cv2.resize(img, input_shape[:-1])

        img_dist.append(img)
        del img_dist[0]

        if os.path.isfile(org_path / iclass / wtype / "Label" / shuffled[time_dist]):
            lbls.append([1, 1])            
        elif os.path.isfile(org_path / iclass / wtype / "Label" / ins_ind(shuffled[time_dist], 'l', shuffled[time_dist].index('.'))):
            lbls.append([1, 0])            
        elif os.path.isfile(org_path / iclass / wtype / "Label" / ins_ind(shuffled[time_dist], 'e', shuffled[time_dist].index('.'))):
            lbls.append([0, 1])            
        else:
            lbls.append([0, 0])            

        imgs.append(np.asarray(img_dist, dtype=np.uint8))

        bcounter += 1

        if bcounter % batch_size == 0:
            bcounter = 0
            yield (np.asarray(imgs, dtype=np.uint8), np.asarray(lbls, dtype=np.float32))
            imgs = []
            lbls = []
            weights = []

def load_data():
    signature = (
        tf.TensorSpec(shape=(batch_size, time_dist, *input_shape), dtype=tf.uint8),
        tf.TensorSpec(shape=(batch_size, *(2,)), dtype=tf.float32),
        # tf.TensorSpec(shape=(batch_size, time_dist), dtype=tf.float32)
    )
    
    for iclass in class_paths:
        trdir_path = org_path / iclass / "Train"
        valdir_path = org_path / iclass / "Val"
        tedir_path = org_path / iclass / "Test"
        
        train_dataset = tf.data.Dataset.from_generator(
            lambda: __data_gen("Train", iclass, trsplit),
            output_signature=signature
        )

        val_dataset = tf.data.Dataset.from_generator(
            lambda: __data_gen("Train", iclass, valsplit),
            output_signature=signature
        )

        test_dataset = tf.data.Dataset.from_generator(
            lambda: __data_gen("Train", iclass, tesplit),
            output_signature=signature
        )
        
        return train_dataset, val_dataset, test_dataset
    
a, b, c = load_data()

aaa = __data_gen("Train", class_paths[0], trsplit)

with open('readmee.txt', 'w') as f:
    iindexi = 0
    for iii in aaa:
        f.write(str(iindexi) + '\n')
        f.write("-------------------\n")
        f.write(str(iii))
        f.write("\n-------------------\n")
        iindexi += 1