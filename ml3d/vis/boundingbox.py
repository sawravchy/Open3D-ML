import numpy as np
import open3d as o3d


class BoundingBox3D:
    """Class that defines an axially-oriented bounding box."""

    next_id = 1

    def __init__(self,
                 center,
                 front,
                 up,
                 left,
                 size,
                 label_class,
                 confidence,
                 meta=None,
                 show_class=False,
                 show_confidence=False,
                 show_meta=None,
                 identifier=None,
                 arrow_length=1.0):
        """Creates a bounding box. Front, up, left define the axis of the box
        and must be normalized and mutually orthogonal.

        Args:

        center (ArrayLike[3]): (x, y, z) that defines the center of the box
        front (ArrayLike[3]): normalized (i, j, k) that defines the front (Y)
            direction of the box
        up (ArrayLike[3]): normalized (i, j, k) that defines the up (Z)
            direction of the box
        left (ArrayLike[3]): normalized (i, j, k) that defines the left (X)
            direction of the box
        size (ArrayLike[3]): (width, height, depth) that defines the size of the box, as
            measured from edge to edge
        label_class (int): integer specifying the classification label. If an LUT is
            specified in create_lines() this will be used to determine the color
            of the box.
        confidence (float): confidence level of the box
        meta (str): a user-defined string (optional)
        show_class (bool, optional): displays the class label in text near the box
        show_confidence (bool, optional): displays the confidence value in text
            near the box
        show_meta (bool, optional): displays the meta string in text near the
            box
        identifier (int, optional): a unique integer that defines the id for the
            box (will be generated if not provided)
        arrow_length (float, optional): the length of the arrow in the
            front_direct. Set to zero to disable the arrow
        """
        assert (len(center) == 3)
        assert (len(front) == 3)
        assert (len(up) == 3)
        assert (len(left) == 3)
        assert (len(size) == 3)

        self.center = np.array(center, dtype="float32")
        self.front = np.array(front, dtype="float32")
        self.up = np.array(up, dtype="float32")
        self.left = np.array(left, dtype="float32")
        self.size = size
        self.label_class = label_class
        self.confidence = confidence
        self.meta = meta
        self.show_class = show_class
        self.show_confidence = show_confidence
        self.show_meta = show_meta
        if identifier is not None:
            self.identifier = identifier
        else:
            self.identifier = "box:" + str(BoundingBox3D.next_id)
            BoundingBox3D.next_id += 1
        self.arrow_length = arrow_length

    def __repr__(self):
        s = str(self.identifier) + " (class=" + str(
            self.label_class) + ", conf=" + str(self.confidence)
        if self.meta is not None:
            s = s + ", meta=" + str(self.meta)
        s = s + ")"
        return s

    def transform(self, transform):
        """
        Transform BoundingBox3D into another reference frame
        Args:
            transform ((4,4) array): Homogenous transform to apply on the right.
        Returns:
            self: Transformed BoundingBox3D
        """
        self.center = self.center @ transform[:3, :3] + transform[3, :3]
        self.front = self.front @ transform[:3, :3]
        self.up = self.up @ transform[:3, :3]
        self.left = self.left @ transform[:3, :3]

        return self

    def inside(self, points):
        """
        Return indices of points inside the BoundingBox3D
        Args:
            points ((N,3) array): list of points
        Returns: Indices of `points` inside the BoundingBox3D
        """
        obb = o3d.geometry.OrientedBoundingBox(
            self.center,
            np.vstack((self.left, self.front, self.up)).T, self.size)
        return obb.get_point_indices_within_bounding_box(
            o3d.utility.Vector3dVector(points))

    @staticmethod
    def create_lines(boxes, lut=None):
        """Creates and returns an open3d.geometry.LineSet that can be used to
        render the boxes.

        boxes: the list of bounding boxes
        lut: a ml3d.vis.LabelLUT that is used to look up the color based on the
            label_class argument of the BoundingBox3D constructor. If not
            provided, a color of 50% grey will be used. (optional)
        """
        nverts = 14
        nlines = 17
        points = np.zeros((nverts * len(boxes), 3), dtype="float32")
        indices = np.zeros((nlines * len(boxes), 2), dtype="int32")
        colors = np.zeros((nlines * len(boxes), 3), dtype="float32")

        for i in range(0, len(boxes)):
            box = boxes[i]
            pidx = nverts * i
            x = 0.5 * box.size[0] * box.left
            y = 0.5 * box.size[1] * box.up
            z = 0.5 * box.size[2] * box.front
            arrow_tip = box.center + z + box.arrow_length * box.front
            arrow_mid = box.center + z + 0.60 * box.arrow_length * box.front
            head_length = 0.3 * box.arrow_length
            # It seems to be substantially faster to assign directly for the
            # points, as opposed to points[pidx:pidx+nverts] = np.stack((...))
            points[pidx] = box.center + x + y + z
            points[pidx + 1] = box.center - x + y + z
            points[pidx + 2] = box.center - x + y - z
            points[pidx + 3] = box.center + x + y - z
            points[pidx + 4] = box.center + x - y + z
            points[pidx + 5] = box.center - x - y + z
            points[pidx + 6] = box.center - x - y - z
            points[pidx + 7] = box.center + x - y - z
            points[pidx + 8] = box.center + z
            points[pidx + 9] = arrow_tip
            points[pidx + 10] = arrow_mid + head_length * box.up
            points[pidx + 11] = arrow_mid - head_length * box.up
            points[pidx + 12] = arrow_mid + head_length * box.left
            points[pidx + 13] = arrow_mid - head_length * box.left

        # It is faster to break the indices and colors into their own loop.
        for i in range(0, len(boxes)):
            box = boxes[i]
            pidx = nverts * i
            idx = nlines * i
            indices[idx:idx +
                    nlines] = ((pidx, pidx + 1), (pidx + 1, pidx + 2),
                               (pidx + 2, pidx + 3), (pidx + 3, pidx),
                               (pidx + 4, pidx + 5), (pidx + 5, pidx + 6),
                               (pidx + 6, pidx + 7), (pidx + 7, pidx + 4),
                               (pidx + 0, pidx + 4), (pidx + 1, pidx + 5),
                               (pidx + 2, pidx + 6), (pidx + 3, pidx + 7),
                               (pidx + 8, pidx + 9), (pidx + 9, pidx + 10),
                               (pidx + 9, pidx + 11), (pidx + 9,
                                                       pidx + 12), (pidx + 9,
                                                                    pidx + 13))

            if lut is not None:
                label = lut.labels[box.label_class]
                c = (label.color[0], label.color[1], label.color[2])
            else:
                c = (0.5, 0.5, 0.5)

            colors[idx:idx +
                   nlines] = c  # copies c to each element in the range

        lines = o3d.geometry.LineSet()
        lines.points = o3d.utility.Vector3dVector(points)
        lines.lines = o3d.utility.Vector2iVector(indices)
        lines.colors = o3d.utility.Vector3dVector(colors)

        return lines

    @staticmethod
    def create_trimesh(boxes, lut=None):
        """
        Create triangular mesh from BoundingBox3D for display with the
        Tensorboard mesh plugin.

        Args:
            boxes (List[BoundingBox3D]): Bounding boxes to be displayed.
            lut (LabelLUT, optional): Lookup table to assign colors to each box.

        Returns:
            points (array(8*N,3)): Box corners.
            colors (array(8*N,3)): Colors for each corner.
            faces (array(12*N,3)): Point indices defining triangular faces.
        """
        nverts = 8
        nfaces = 12
        points = np.empty((nverts * len(boxes), 3), dtype="float32")
        faces = np.empty((nfaces * len(boxes), 3), dtype="int32")
        colors = np.empty((nverts * len(boxes), 3), dtype="uint8")

        for i, box in enumerate(boxes):
            pidx = nverts * i
            x = 0.5 * box.size[0] * box.left
            y = 0.5 * box.size[1] * box.up
            z = 0.5 * box.size[2] * box.front
            # It seems to be substantially faster to assign directly for the
            # points, as opposed to points[pidx:pidx+nverts] = np.stack((...))
            points[pidx] = box.center + x + y + z
            points[pidx + 1] = box.center - x + y + z
            points[pidx + 2] = box.center - x + y - z
            points[pidx + 3] = box.center + x + y - z
            points[pidx + 4] = box.center + x - y + z
            points[pidx + 5] = box.center - x - y + z
            points[pidx + 6] = box.center - x - y - z
            points[pidx + 7] = box.center + x - y - z

        # It is faster to break the indices and colors into their own loop.
        for i, box in enumerate(boxes):
            pidx = nverts * i
            idx = nfaces * i
            faces[idx:idx + nfaces] = (
                (pidx, pidx + 1, pidx + 2),
                (pidx + 2, pidx + 3, pidx),  # + y
                (pidx + 4, pidx + 5, pidx + 6),
                (pidx + 6, pidx + 7, pidx + 4),  # - y
                (pidx, pidx + 1, pidx + 5),
                (pidx + 5, pidx + 4, pidx),  # + z
                (pidx + 2, pidx + 3, pidx + 7),
                (pidx + 7, pidx + 6, pidx + 2),  # - z
                (pidx, pidx + 3, pidx + 7),
                (pidx + 7, pidx + 4, pidx),  # + x
                (pidx + 1, pidx + 2, pidx + 6),
                (pidx + 6, pidx + 5, pidx + 1))  # - x

            if lut is not None:
                label = lut.labels[box.label_class]
                c = (255 * label.color[0], 255 * label.color[1],
                     255 * label.color[2])
            else:
                c = (128, 128, 128)

            colors[pidx:pidx +
                   nverts] = c  # copies c to each element in the range

        return points, colors, faces
