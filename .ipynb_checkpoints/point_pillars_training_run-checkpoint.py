import os
import time
import tensorflow as tf
from glob import glob

from config import Parameters
from loss import PointPillarNetworkLoss
from network import build_point_pillar_graph
from processors import SimpleDataGenerator
from readers import KittiDataReader

DATA_ROOT = "../training_small"  # TODO make main arg

if __name__ == "__main__":

    params = Parameters()

    pillar_net = build_point_pillar_graph(params)

    loss = PointPillarNetworkLoss(params)

    optimizer = tf.keras.optimizers.Adam(lr=params.learning_rate, decay=params.decay_rate)

    pillar_net.compile(optimizer, loss=loss.losses())

    log_dir = "./logs"
    callbacks = [
        tf.keras.callbacks.TensorBoard(log_dir=log_dir),
        tf.keras.callbacks.ModelCheckpoint(filepath=os.path.join(log_dir, "model.h5"),
                                           monitor='loss', save_best_only=True),
        tf.keras.callbacks.LearningRateScheduler(
            lambda epoch, lr: lr * 0.8 if ((epoch % 15 == 0) and (epoch != 0)) else lr, verbose=True),
        tf.keras.callbacks.EarlyStopping(patience=20, monitor='loss'),
    ]

    data_reader = KittiDataReader()

    lidar_files = sorted(glob(os.path.join(DATA_ROOT, "velodyne", "*.bin")))
    label_files = sorted(glob(os.path.join(DATA_ROOT, "label_2", "*.txt")))
    calibration_files = sorted(glob(os.path.join(DATA_ROOT, "calib", "*.txt")))
    print(len(lidar_files), len(label_files), len(calibration_files))
    training_gen = SimpleDataGenerator(data_reader, params.batch_size, lidar_files, label_files, calibration_files)

    try:
        pillar_net.fit(training_gen,
                       steps_per_epoch=len(training_gen),
                       callbacks=callbacks,
                       use_multiprocessing=True,
                       epochs=int(params.total_training_epochs),
                       workers=6)
    except KeyboardInterrupt:
        model_str = "interrupted_%s.h5" % time.strftime("%Y%m%d-%H%M%S")
        pillar_net.save(os.path.join(log_dir, model_str))
        print("Interrupt. Saving output to %s" % os.path.join(os.getcwd(), log_dir[1:], model_str))