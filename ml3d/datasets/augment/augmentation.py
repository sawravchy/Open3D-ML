import numpy as np
import random


class SemsegAugmentation():
    """Class consisting different augmentation methods for Semantic Segmentation"""

    def __init__(self, cfg):
        self.cfg = cfg

    @staticmethod
    def normalize(data, cfg):
        if 'points' in cfg.keys():
            cfg_p = cfg['points']
            pc = data['point']
            if cfg_p.get('recentering', False):
                pc -= pc.mean(0)
            if cfg_p.get('method', 'linear') == 'linear':
                pc -= pc.mean(0)
                pc /= (pc.max(0) - pc.min(0)).max()

            data['point'] = pc

        if 'feat' in cfg.keys() and data['feat'] is not None:
            cfg_f = cfg['feat']
            feat = data['feat']
            if cfg_f.get('recentering', False):
                feat -= feat.mean(0)
            if cfg_f.get('method', 'linear') == 'linear':
                bias = cfg_f.get('bias', 0)
                scale = cfg_f.get('scale', 1)
                feat -= bias
                feat /= scale

            data['feat'] = feat

        return data

    @staticmethod
    def rotate(pc, cfg):
        # Initialize rotation matrix
        R = np.eye(pc.shape[1])

        method = cfg.get('method', None)

        if method == 'vertical':
            # Create random rotations
            theta = np.random.rand() * 2 * np.pi
            c, s = np.cos(theta), np.sin(theta)
            R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float32)

        elif method == 'all':

            # Choose two random angles for the first vector in polar coordinates
            theta = np.random.rand() * 2 * np.pi
            phi = (np.random.rand() - 0.5) * np.pi

            # Create the first vector in carthesian coordinates
            u = np.array([
                np.cos(theta) * np.cos(phi),
                np.sin(theta) * np.cos(phi),
                np.sin(phi)
            ])

            # Choose a random rotation angle
            alpha = np.random.rand() * 2 * np.pi

            # Create the rotation matrix with this vector and angle
            R = create_3D_rotations(np.reshape(u, (1, -1)),
                                    np.reshape(alpha, (1, -1)))[0]

        R = R.astype(np.float32)

        return np.matmul(pc, R)

    @staticmethod
    def scale(pc, cfg):

        # Choose random scales for each example
        scale_anisotropic = cfg.get('scale_anisotropic', False)
        min_s = cfg.get('min_s', 1.)
        max_s = cfg.get('max_s', 1.)

        if scale_anisotropic:
            scale = np.random.rand(pc.shape[1]) * (max_s - min_s) + min_s
        else:
            scale = np.random.rand() * (max_s - min_s) + min_s

        return pc * scale

    @staticmethod
    def noise(pc, cfg):
        noise_level = cfg.get('noise_level', 0.001)
        noise = (np.random.randn(pc.shape[0], pc.shape[1]) *
                 noise_level).astype(np.float32)

        return pc + noise

    def augment(self, data, cfg):
        if 'normalize' in cfg.keys():
            data = self.normalize(data, cfg['normalize'])

        if 'rotate' in cfg.keys():
            data['point'] = self.rotate(data['point'], cfg['rotate'])

        if 'scale' in cfg.keys():
            data['point'] = self.scale(data['point'], cfg['scale'])

        if 'noise' in cfg.keys():
            data['point'] = self.noise(data['point'], cfg['noise'])


class ObjdetAugmentation():
    """Class consisting different augmentation for Object Detection"""

    @staticmethod
    def PointShuffle(data):
        np.random.shuffle(data['point'])

        return data

    @staticmethod
    def ObjectRangeFilter(data, pcd_range):
        pcd_range = np.array(pcd_range)
        bev_range = pcd_range[[0, 1, 3, 4]]

        filtered_boxes = []
        for box in data['bbox_objs']:
            if in_range_bev(bev_range, box.to_xyzwhlr()):
                filtered_boxes.append(box)

        return {
            'point': data['point'],
            'bbox_objs': filtered_boxes,
            'calib': data['calib']
        }

    @staticmethod
    def ObjectSample(data, db_boxes_dict, sample_dict):
        rate = 1.0
        points = data['point']
        bboxes = data['bbox_objs']

        gt_labels_3d = [box.label_class for box in data['bbox_objs']]

        sampled_num_dict = {}

        for class_name in sample_dict.keys():
            max_sample_num = sample_dict[class_name]

            existing = np.sum([n == class_name for n in gt_labels_3d])
            sampled_num = int(max_sample_num - existing)
            sampled_num = np.round(rate * sampled_num).astype(np.int64)
            sampled_num_dict[class_name] = sampled_num

        sampled = []
        for class_name in sampled_num_dict.keys():
            sampled_num = sampled_num_dict[class_name]
            if sampled_num < 0:
                continue

            sampled_cls = sample_class(class_name, sampled_num, bboxes,
                                       db_boxes_dict[class_name])
            sampled += sampled_cls
            bboxes = bboxes + sampled_cls

        if len(sampled) != 0:
            sampled_points = np.concatenate(
                [box.points_inside_box for box in sampled], axis=0)
            points = remove_points_in_boxes(points, sampled)
            points = np.concatenate([sampled_points, points], axis=0)

        return {'point': points, 'bbox_objs': bboxes, 'calib': data['calib']}

    @staticmethod
    def ObjectNoise(input,
                    trans_std=[0.25, 0.25, 0.25],
                    rot_range=[-0.15707963267, 0.15707963267],
                    num_try=100):
        raise NotImplementedError
