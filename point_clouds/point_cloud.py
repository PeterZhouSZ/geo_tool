'''
Created on December 8, 2016

@author: Panos Achlioptas
@contact: pachlioptas @ gmail.com
@copyright: You are free to use, change, or redistribute this code in any way you want for non-commercial purposes.
'''


import copy
import cPickle
import warnings
import numpy as np

try:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
except:
    warnings.warn('Pyplot library is not working correctly. Some graphics utilities will be disabled.')


from .. in_out import soup as io
from .. utils import linalg_utils as utils
from .. fundamentals import Cuboid

l2_norm = utils.l2_norm


class Point_Cloud(object):
    '''
    A class representing a 3D Point Cloud.
    Dependencies:
        1. plyfile 0.4: PLY file reader/writer. DOI: https://pypi.python.org/pypi/plyfile
    '''
    def __init__(self, points=None, ply_file=None):
        '''
        Constructor
        '''
        if ply_file is not None:
            self.points = io.load_ply(ply_file)
        else:
            self.points = points

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, value):
        self._points = value
        self.num_points = len(self._points)

    def __str__(self):
        return 'Point Cloud with %d points.' % (self.num_points)

    def save(self, file_out):
        with open(file_out, "w") as f_out:
            cPickle.dump(self, f_out)

    def copy(self):
        return copy.deepcopy(self)

    def permute_points(self, permutation):
        if len(permutation) != 3 or not np.all(np.equal(sorted(permutation), np.array([0, 1, 2]))):
            raise ValueError()
        self.points = self.points[:, permutation]
        return self

    def sample(self, n_samples, replacement=False):
        if n_samples > self.num_points:
            replacement = True
        rindex = np.random.choice(self.num_points, n_samples, replace=replacement)
        return Point_Cloud(points=self.points[rindex, :])

    def bounding_box(self):
        return Cuboid.bounding_box_of_3d_points(self.points)

    def center_in_unit_sphere(self):
        self.points = Point_Cloud.center_points_in_unit_sphere(self.points)
        return self

    def plot(self, show=True, in_u_sphere=False, *args, **kwargs):
        x = self.points[:, 0]
        y = self.points[:, 1]
        z = self.points[:, 2]
        return Point_Cloud.plot_3d_point_cloud(x, y, z, show=show, in_u_sphere=in_u_sphere, *args, **kwargs)

    def barycenter(self):
        n_points = self.points.shape[0]
        return np.sum(self.points, axis=0) / n_points

    def lex_sort(self, axis=-1):
        '''Sorts the list storing the points of the Point_Cloud in a lexicographical order.
        See numpy.lexsort
        '''
        lex_indices = np.lexsort(self.points.T, axis=axis)
        self.points = self.points[lex_indices, :]
        return self, lex_indices

    @staticmethod
    def center_points_in_unit_sphere(points):
        n_points = points.shape[0]
        barycenter = np.sum(points, axis=0) / n_points
        points -= barycenter   # Center it in the origin.
        max_dist = np.max(l2_norm(points, axis=1))  # Make max distance equal to one.
        points /= max_dist * 2
        return points

    @staticmethod
    def plot_3d_point_cloud(x, y, z, show=True, in_u_sphere=False, *args, **kwargs):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z, *args, **kwargs)

        if in_u_sphere:
            ax.set_xlim3d(-0.5, 0.5)
            ax.set_ylim3d(-0.5, 0.5)
            ax.set_zlim3d(-0.5, 0.5)

        if show:
            plt.show()
        return fig

    @staticmethod
    def load(in_file):
        with open(in_file, 'r') as f_in:
            res = cPickle.load(f_in)
        return res
