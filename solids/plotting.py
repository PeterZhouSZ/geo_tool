'''
Created on Dec 30, 2017

@author: optas
'''

import numpy as np
import matplotlib.pylab as plt
import matplotlib.cm as cm

from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from plotly.graph_objs import Mesh3d, Data, Scatter3d, Line
from plotly.offline import iplot

from .. point_clouds import Point_Cloud


def plot_mesh_via_matplotlib(in_mesh, in_u_sphere=True, axis=None, figsize=(5, 5), show=True):
    '''Alternative to plotting a mesh with matplotlib.
       TODO Need colorize vertex/faces. more input options'''

    faces = in_mesh.triangles
    verts = in_mesh.vertices
    if in_u_sphere:
        verts = Point_Cloud(verts).center_in_unit_sphere().points

    if axis is None:
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')
    else:
        ax = axis
        fig = axis

    mesh = Poly3DCollection(verts[faces])
    mesh.set_edgecolor('k')
    ax.add_collection3d(mesh)
    ax.set_xlabel("x-axis")
    ax.set_ylabel("y-axis")
    ax.set_zlabel("z-axis")

    miv = np.min(verts)
    mav = np.max(verts)
    ax.set_xlim(miv, mav)
    ax.set_ylim(miv, mav)
    ax.set_zlim(miv, mav)
    plt.tight_layout()
    if show:
        plt.show()
    else:
        return fig


def plot_mesh_via_plottly(in_mesh, colormap=cm.RdBu, plot_edges=None, vertex_color=None, show=True):
    x = in_mesh.vertices[:, 0]
    y = in_mesh.vertices[:, 1]
    z = in_mesh.vertices[:, 2]
    simplices = in_mesh.triangles
    tri_vertices = map(lambda index: in_mesh.vertices[index], simplices)    # vertices of the surface triangles
    I, J, K = ([triplet[c] for triplet in simplices] for c in range(3))

    triangles = Mesh3d(x=x, y=y, z=z, vertexcolor=vertex_color, i=I, j=J, k=K, name='')

    if plot_edges is None:  # The triangle edges are not plotted.
        res = Data([triangles])
    else:
        # Define the lists Xe, Ye, Ze, of x, y, resp z coordinates of edge end points for each triangle
        # None separates data corresponding to two consecutive triangles
        lists_coord = [[[T[k % 3][c] for k in range(4)] + [None] for T in tri_vertices] for c in range(3)]
        Xe, Ye, Ze = [reduce(lambda x, y: x + y, lists_coord[k]) for k in range(3)]

        # Define the lines to be plotted
        lines = Scatter3d(x=Xe, y=Ye, z=Ze, mode='lines', line=Line(color='rgb(50, 50, 50)', width=1.5))
        res = Data([triangles, lines])

    if show:
        iplot(res)
    else:
        return res
