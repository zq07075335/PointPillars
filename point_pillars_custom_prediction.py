import os
from glob import glob
import numpy as np
import tensorflow as tf
# from processors import SimpleDataGenerator
# from custom_processors import CustomDataGenerator, AnalyseCustomDataGenerator
from point_pillars_custom_processors_v2 import CustomDataGenerator, AnalyseCustomDataGenerator
from inference_utils_v2 import generate_bboxes_from_pred, GroundTruthGenerator
from inference_utils_v2 import focal_loss_checker, rotational_nms, generate_bboxes_from_pred_and_np_array
from readers import KittiDataReader
from config_v2 import Parameters
from network import build_point_pillar_graph


from point_viz.converter import PointvizConverter

DATA_ROOT = "/media/data3/tjtanaa/kitti_dataset/"
MODEL_ROOT = "./logs_Car_Pedestrian_Custom_Dataset_No_Early_Stopping_wo_Aug_wo_val"

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"


def limit_period(val, offset=0.5, period=np.pi):
    return val - np.floor(val / period + offset) * period

if __name__ == "__main__":

    params = Parameters()
    pillar_net = build_point_pillar_graph(params)
    pillar_net.load_weights(os.path.join(MODEL_ROOT, "model.h5"))
    pillar_net.summary()

    exit()
    # save_viz_path = "/home/tan/tjtanaa/PointPillars/visualization/custom_prediction_multiprocessing"
    save_viz_path = os.path.join("/home/tan/tjtanaa/PointPillars/visualization", MODEL_ROOT.split('/')[-1])
    # Initialize and setup output directory.
    Converter = PointvizConverter(save_viz_path)



        


    gt_database_dir = os.path.join(DATA_ROOT, "gt_database")

    # validation_gen = AnalyseCustomDataGenerator(batch_size=params.batch_size,root_dir = DATA_ROOT,
    #                 npoints=20000, split='train',   classes=list(params.classes_map.keys()), 
    #                 random_select=True, gt_database_dir=None, aug_hard_ratio=0.7)

    validation_gen = AnalyseCustomDataGenerator(batch_size=params.batch_size,  root_dir=DATA_ROOT, 
            npoints=20000, split='val',random_select=False,  classes=list(params.classes_map.keys()))
    # validation_gen = AnalyseCustomDataGenerator(batch_size=params.batch_size,  root_dir=DATA_ROOT, 
    #         npoints=20000, split='val',random_select=False,  classes=list(params.classes_map.keys()))

    for batch_idx in range(0,20):
        [pillars, voxels], [occupancy_, position_, size_, angle_, heading_, classification_], [pts_input, gt_boxes3d, sample] = validation_gen[batch_idx]

        occupancy, position, size, angle, heading, classification = pillar_net.predict([pillars, voxels])

        # angle = limit_period(angle, offset=0.5, period=2*np.pi)


        # occupancy[:,:,:,:2] = 0

        # print(occupancy.shape)
        # exit()

        set_boxes, confidences = [], []
        loop_range = occupancy_.shape[0] if len(occupancy_.shape) == 4 else 1
        for i in range(loop_range):
            set_box, predicted_boxes3d = generate_bboxes_from_pred_and_np_array(occupancy[i], position[i], size[i], angle[i], 
                                                            heading[i],
                                                            classification[i], params.anchor_dims, occ_threshold=0.5)


            _, decoded_gt_boxes3d = generate_bboxes_from_pred_and_np_array(occupancy_[i], position_[i], size_[i], angle_[i], 
                                                            heading_[i],
                                                            classification_[i], params.anchor_dims, occ_threshold=0.4)

            # gt_boxes3d_ = gt_boxes3d[i]
            gt_boxes3d_ = decoded_gt_boxes3d

            # print(gt_boxes3d_.shape)
            gt_bbox_params = np.stack([gt_boxes3d_[:,3], gt_boxes3d_[:,5], gt_boxes3d_[:,4],
                        gt_boxes3d_[:,1], gt_boxes3d_[:,2] , 
                        gt_boxes3d_[:,0],
                        gt_boxes3d_[:,6]], axis=1)


            gt_bbox_params_list = gt_bbox_params.tolist()
            # gt_bbox_params_list = []
            for k in range(len(gt_bbox_params_list)):
                msg = "%.5f, %s, %.5f"%(decoded_gt_boxes3d[k,9], params.map_classes[int(decoded_gt_boxes3d[k,8])], decoded_gt_boxes3d[k,6])
                # msg = "%.5f, %.5f"%(gt_bbox_params_list[k][3],gt_bbox_params_list[k][5])
                gt_bbox_params_list[k].append("Green")
                # gt_bbox_params_list[k].append("1.0")
                gt_bbox_params_list[k].append(msg)

            if len(set_box) > 0:
                predicted_boxes3d_ = predicted_boxes3d
                # bbox_params = validation_gen.convert_predictions_into_point_viz_format(predicted_boxes3d[:,[1, 2, 0, 5, 3, 4, 6 ]])

                print("batch_idx: ", batch_idx * params.batch_size + i, " has ", predicted_boxes3d_.shape, "predictions")
                # print(predicted_boxes3d_)
                # print(size[i])

                bbox_params = np.stack([predicted_boxes3d_[:,3], predicted_boxes3d_[:,5], predicted_boxes3d_[:,4],
                            predicted_boxes3d_[:,1], predicted_boxes3d_[:,2] , 
                            predicted_boxes3d_[:,0],
                            predicted_boxes3d_[:,6]], axis=1)


                bbox_params_list = bbox_params.tolist()
                # bbox_labels_conf = [str(predicted_boxes3d[k,9]) for k in range(predicted_boxes3d.shape[0])]
                for k in range(predicted_boxes3d.shape[0]):
                    msg = "%.5f, %s, %.5f"%(predicted_boxes3d[k,9],params.map_classes[int(predicted_boxes3d[k,8])], predicted_boxes3d[k,6])
                    bbox_params_list[k].append("Magenta")
                    bbox_params_list[k].append(msg)
                    # bbox_params_list[k].append(str(predicted_boxes3d[k,9]) + "=" + params.map_classes[int(predicted_boxes3d[k,8])])
                    gt_bbox_params_list.append(bbox_params_list[k])

            coor = pts_input[i][:,[1,2,0]]
            # coor[:,1] *= -1
            Converter.compile("val_custom_sample_{}".format(batch_idx * params.batch_size+i), coors=coor, intensity=pts_input[i][:,3],
                            bbox_params=gt_bbox_params_list)

        #     set_boxes.append(set_box)
        #     # set_boxes.append(generate_bboxes_from_pred(occupancy, position, size, angle, heading,
        #     #                                         classification, params.anchor_dims, occ_threshold=0.1))
        #     # confidences.append([float(boxes.conf) for boxes in set_boxes[-1]])
        
        # sum_bboxes = 0
        # for h in range(len(set_boxes)):
        #     sum_bboxes += len(set_boxes[h])

        # print('Batch ', str(batch_idx) ,': Box predictions with occupancy > occ_thr: ', sum_bboxes)
        # print('Scene 1: Box predictions with occupancy > occ_thr: ', len(set_boxes[0]))
        # exit()
        # print(set_boxes[-1])

        # # NMS
        # nms_boxes = rotational_nms(set_boxes, confidences, occ_threshold=0.7, nms_iou_thr=0.5)

        # print('Scene 1: Boxes after NMS with iou_thr: ', len(nms_boxes[0]))

    # # Do all the further operations on predicted_boxes array, which contains the predicted bounding boxes
    # gt_gen = GroundTruthGenerator(data_reader, label_files, calibration_files, network_format=False)
    # gt_gen0 = GroundTruthGenerator(data_reader, label_files, calibration_files, network_format=True)
    # for seq_boxes, gt_label, gt0 in zip(nms_boxes, gt_gen, gt_gen0):
    #     print("---------- New Scenario ---------- ")
    #     focal_loss_checker(gt0[0], occupancy[0], n_occs=-1)
    #     print("---------- ------------ ---------- ")
    #     for gt in gt_label:
    #         print(gt)
    #     for pred in seq_boxes:
    #         print(pred)
