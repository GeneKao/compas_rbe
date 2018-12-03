from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
from math import fabs

try:
    from numpy import array

    from scipy.linalg import solve
    from scipy.spatial import cKDTree
except ImportError:
    if 'ironpython' not in sys.version.lower():
        raise

try:
    from shapely.geometry import Polygon
except ImportError:
    if 'ironpython' not in sys.version.lower():
        raise

from compas.geometry import global_coords_numpy


__all__ = [
    'identify_interfaces',
    'identify_interfaces_xfunc',
]


def _find_nearest_neighbours(cloud, nmax):
    tree  = cKDTree(cloud)
    nnbrs = [tree.query(root, nmax) for root in cloud]
    nnbrs = [(d.flatten().tolist(), n.flatten().tolist()) for d, n in nnbrs]
    return nnbrs


def identify_interfaces_xfunc(data, **kwargs):
    from compas_rbe.datastructures import Assembly
    from compas_rbe.datastructures import Block

    assembly = Assembly.from_data(data['assembly'])
    assembly.blocks = {int(key): Block.from_data(data['blocks'][key]) for key in data['blocks']}

    identify_interfaces(assembly, **kwargs)

    return {
        'assembly': assembly.to_data(),
        'blocks': {str(key): assembly.blocks[key].to_data() for key in assembly.blocks}
    }


def identify_interfaces(assembly,
                        nmax=10,
                        tmax=1e-6,
                        amin=1e-1,
                        lmin=1e-3,
                        face_face=True,
                        face_edge=False,
                        face_vertex=False):
    """Identify the interfaces between the blocks of an assembly.

    Parameters
    ----------
    assembly : compas_rbe.datastructures.Assembly
        An assembly of discrete blocks.
    nmax : int, optional
        Maximum number of neighbours per block.
        Default is ``10``.
    tmax : float, optional
        Maximum deviation from the perfectly flat interface plane.
        Default is ``1e-6``.
    amin : float, optional
        Minimum area of a "face-face" interface.
        Default is ``1e-1``.
    lmin : float, optional
        Minimum length of a "face-edge" interface.
        Default is ``1e-3``.
    face_face : bool, optional
        Test for "face-face" interfaces.
        Default is ``True``.
    face_edge : bool, optional
        Test for "face-edge" interfaces.
        Default is ``False``.
    face_vertex : bool, optional
        Test for "face-vertex" interfaces.
        Default is ``False``.

    References
    ----------
    The identification of interfaces is discussed in detail here [Frick2016]_.

    Examples
    --------
    .. code-block:: python

        pass

    """

    key_index   = {key: index for index, key in enumerate(assembly.vertices())}
    index_key   = {index: key for index, key in enumerate(assembly.vertices())}

    blocks      = [assembly.blocks[key] for key in assembly.vertices()]
    nmax        = min(nmax, len(blocks))
    block_cloud = [assembly.vertex_coordinates(key) for key in assembly.vertices()]
    block_nnbrs = _find_nearest_neighbours(block_cloud, nmax)

    # k:      key of the base block
    # i:      index of the base block
    # block:  base block
    # nbrs:   list of indices of the neighbouring blocks
    # frames: list of frames for each of the faces of the base block

    # f0:   key of the current base face
    # A:    uvw base frame of f0
    # o:    origin of the base frame of f0
    # xyz0: xyz coordinates of the vertices of f0
    # rst0: local coordinates of the vertices of f0, with respect to the frame of f0
    # p0:   2D polygon of f0 in local coordinates

    # j:   index of the current neighbour
    # n:   key of the current neighbour
    # nbr: neighbour block
    # k_i: key index map for the vertices of the nbr block
    # xyz: xyz coorindates of all vertices of nbr
    # rst: local coordinates of all vertices of nbr, with respect to the frame of f0

    # f1:   key of the current neighbour face
    # rst1: local coordinates of the vertices of f1, with respect to the frame of f0
    # p1:   2D polygon of f1 in local coordinates

    for k in assembly.vertices():
        print(k)

        i      = key_index[k]
        block  = assembly.blocks[k]
        nbrs   = block_nnbrs[i][1]
        frames = block.frames()

        if face_face:

            # parallelise?
            # exclude faces with parallel normals
            # e.g. exclude overlapping top faces of two neighbouring blocks in same row

            for f0, (origin, uvw) in frames.items():
                A    = array(uvw)
                o    = array(origin).reshape((-1, 1))
                xyz0 = array(block.face_coordinates(f0)).reshape((-1, 3)).T
                rst0 = solve(A.T, xyz0 - o).T.tolist()
                p0   = Polygon(rst0)

                for j in nbrs:
                    n = index_key[j]

                    if n == k:
                        continue

                    if k in assembly.edge and n in assembly.edge[k]:
                        continue

                    if n in assembly.edge and k in assembly.edge[n]:
                        continue

                    nbr = assembly.blocks[n]
                    k_i = {key: index for index, key in enumerate(nbr.vertices())}
                    xyz = array([nbr.vertex_coordinates(key) for key in nbr.vertices()]).reshape((-1, 3)).T
                    rst = solve(A.T, xyz - o).T.tolist()
                    rst = {key: rst[k_i[key]] for key in nbr.vertices()}

                    for f1 in nbr.faces():

                        rst1 = [rst[key] for key in nbr.face_vertices(f1)]

                        if any(fabs(t) > tmax for r, s, t in rst1):
                            continue

                        p1 = Polygon(rst1)

                        if p1.area == 0.0:
                            continue

                        if p0.intersects(p1):
                            intersection = p0.intersection(p1)
                            # try:
                            #     intersection = p0.intersection(p1)
                            # except Exception:
                            #     print(p0, p1)
                            #     continue
                            # else:
                            area = intersection.area

                            if area >= amin:

                                coords = [[x, y, 0.0] for x, y, z in intersection.exterior.coords]
                                coords = global_coords_numpy(o, A, coords)

                                attr = {
                                    'interface_type'   : 'face_face',
                                    'interface_size'   : area,
                                    'interface_points' : coords.tolist()[: -1],
                                    'interface_origin' : origin,
                                    'interface_uvw'    : uvw,
                                }

                                assembly.add_edge(k, n, attr_dict=attr)


# ==============================================================================
# Debugging
# ==============================================================================

if __name__ == "__main__":
    pass