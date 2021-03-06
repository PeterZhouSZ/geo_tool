'''
Created on June 14, 2016

@author:    Panos Achlioptas.
@contact:   pachlioptas @ gmail.com
@copyright: You are free to use, change, or redistribute this code in any way you want for non-commercial purposes.
@updated:   Winnie Lin (winniepwlin1994@gmail.com), March 2018.
'''

import numpy as np
import math
import scipy.sparse as sparse
from scipy.sparse.linalg import eigs

from general_tools.rla.one_d_transforms import smooth_normal_outliers, find_non_homogeneous_vectors
from general_tools.arrays.basics import scale
from .. utils import linalg_utils as utils


def fiedler_of_component_spectra(in_mesh, in_lb, thres):
    spectra, multi_cc = in_lb.multi_component_spectra(2, thres)
    n_cc = len(multi_cc)
    aggregate_color = np.zeros((in_mesh.num_vertices, 1))
    for i in xrange(n_cc):
        nodes = multi_cc[i]
        if spectra[i]:
            magic_color = scale(spectra[i][1][:, -1]**2)
            aggregate_color[nodes] = magic_color.reshape(len(nodes), 1)
    return aggregate_color[:, 0]


def hks_of_component_spectra(in_mesh, in_lb, area_type, percent_of_eigs, time_horizon, min_nodes=None, min_eigs=None, max_eigs=None):
    spectra, multi_cc = in_lb.multi_component_spectra(in_mesh, area_type, percent_of_eigs,
                                                      min_nodes=min_nodes, min_eigs=min_eigs, max_eigs=max_eigs)
    n_cc = len(multi_cc)
    hks_signature = np.zeros((in_mesh.num_vertices, time_horizon))
    aggregate_color = np.zeros((in_mesh.num_vertices, ))

    for i in xrange(n_cc):
        nodes = multi_cc[i]
        if spectra[i]:
            evals = spectra[i][0]
            evecs = spectra[i][1].T
            pos_index = evals > 0
            if np.sum(pos_index) == 0:
                continue
            evals = evals[pos_index]
            evecs = evecs[pos_index, :]
            evecs = np.around(evecs, 2)
            smooth_normal_outliers(evecs, 3)
            index = find_non_homogeneous_vectors(evecs, 0.95)
            if len(index) >= 2:
                evecs = evecs[index, :]
                evals = evals[index] + 1        # Add 1 to make the division on time_samples strictly decreasing
                ts = hks_time_sample_generator(evals[0], evals[-1], time_horizon)
                sig = heat_kernel_signature(evals, evecs, ts)
                sig = sig / utils.l2_norm(sig, axis=0)
                hks_signature[nodes, :] = sig
                magic_color = scale(np.sum(sig, 1))
                aggregate_color[nodes] = magic_color.reshape(len(nodes), 1)

    return aggregate_color, hks_signature


def gaussian_curvature(in_mesh):
    acc_map = in_mesh.triangles.ravel()
    angles = in_mesh.angles_of_triangles().ravel()
    acc_array = np.bincount(acc_map, weights=angles)
    gauss_curv = (2 * np.pi - acc_array)
    gauss_curv = gauss_curv.reshape(len(gauss_curv), 1)
    gauss_curv /= in_mesh.area_of_vertices()
    return gauss_curv


def mean_curvature(in_mesh, laplace_beltrami):
    N = in_mesh.normals_of_vertices()
    mean_curv = 0.5 * np.sum(N * (laplace_beltrami.W * in_mesh.vertices), 1)
    return mean_curv


def heat_kernel_embedding(lb, n_eigs, n_time):
    evals, evecs = lb.spectra(n_eigs)
    pos_index = evals > 0
    evals = evals[pos_index]
    evecs = evecs[:, pos_index]
    time_points = hks_time_sample_generator(evals[0], evals[-1], n_time)
    return heat_kernel_signature(evals, evecs.T, time_points)


def heat_kernel_signature(evals, evecs, time_horizon, verbose=False):
    ''' given eigenbasis of mesh's Laplace Beltrami operator, returns the heat kernel signature at each time point within the time_horizon.

    input dimensions:
        evecs = (n_vecs, n_vertices)
        evals = (n_vecs,)
        time_horizon = [n_timepoints]

    output dimensions = (n_vertices,n_timepoints)
    '''

    if len(evals) != evecs.shape[0]:
        raise ValueError('Eigenvectors must have dimension = #eigen-vectors x nodes.')
    if verbose:
        print "Computing Heat Kernel Signature with %d eigen-pairs." % (len(evals),)

    n = evecs.shape[1]  # Number of nodes.
    signatures = np.empty((n, len(time_horizon)))
    squared_evecs = np.square(evecs)
    for t, tp in enumerate(time_horizon):
        interm = np.exp(-tp * evals)
        signatures[:, t] = np.matmul(interm, squared_evecs)

    return signatures


def hks_time_sample_generator(min_eval, max_eval, time_points):
    '''
    returns sampled time intervals to be passed into heat_kernel_signature().

    output dimensions = [time_points]
    '''

    if max_eval <= min_eval or min_eval <= 0:
        raise ValueError('Two non-negative and sorted eigen-values are expected as input.')

    logtmin = math.log(math.log(10) / max_eval)
    logtmax = math.log(math.log(10) / min_eval)
    assert(logtmax > logtmin) 
    stepsize = (logtmax - logtmin) / (time_points - 1) #minus 1 is to ensure we reach max
    logts = [logtmin + i * stepsize for i in range(time_points)]
    return [math.exp(i) for i in logts]


def wave_kernel_signature(evals, evecs, energies, sigma=1):
    ''' given eigenbasis of mesh's Laplace Beltrami operator, returns the wave kernel signature at each time point within the time_horizon.

    input dimensions:
        evecs = (n_vecs, n_vertices)
        evals = (n_vecs,)
        energies = [n_timepoints]
    output dimensions = (n_vertices,n_timepoints)
    '''

    if len(evals) != evecs.shape[0]:
        raise ValueError('Eigenvectors must have dimension = #eigen-vectors x nodes.')

    n = evecs.shape[1]  # Number of nodes.
    signatures = np.empty((n, len(energies)))
    squared_evecs = np.square(evecs)

    log_evals = np.log(evals)
    var = 2 * (sigma**2)
    for t, en in enumerate(energies):
        interm = np.exp(-(en - log_evals) ** 2 / var)
        norm_factor = 1 / np.sum(interm)
        signatures[:, t] = np.matmul(interm, squared_evecs) * norm_factor

    assert(np.alltrue(signatures >= 0))
    return signatures


def wks_energy_generator(min_eval, max_eval, time_points, padding=7, shrink=1):
    '''
    returns sampled energy intervals to be passed into wave_kernel_signature().

    output dimensions = [time_points]

    parameters from original paper:
      emin= e_1+2*sigma
      emax= e_n-2*sigma
      delta= (emax-emin)/num_timepoints
      sigma= 7*delta

    '''

    if min_eval == 0:
        raise ValueError('minimum eigenvalue must not be zero.')

    logmin = math.log(min_eval)
    logmax = math.log(max_eval)
    logmax = shrink * logmax + (1 - shrink) * logmin
    #if shrink != 1:
    #    emax = math.log(max_eval) / float(shrink)
    #else:
    #    emax = math.log(max_eval)
    #if emax <= emin:
    #    print "Warning: too much shrink. - Will be set manually."
    #    emax = emin + 0.05 * emin

    delta = (logmax - logmin) / (time_points + 2 * padding - 1) #minus 1 is to ensure we reach emax (emax = logmax - sigma)
    sigma = padding * delta
    emin = logmin + sigma
    res = [emin + i * delta for i in range(time_points)]
    return res, sigma


def merge_component_spectra(in_mesh, in_lb, percent_of_eigs, merger=np.sum):
        spectra, multi_cc = in_lb.multi_component_spectra(in_mesh, percent=percent_of_eigs)
        n_cc = len(multi_cc)
        signature = np.zeros((in_mesh.num_vertices, 1))
        for i in xrange(n_cc):
            nodes = multi_cc[i]
            if spectra[i]:
                magic_color = merger(spectra[i][1]**2, axis=1)
                signature[nodes] = magic_color.reshape(len(nodes), 1)
        return signature[:, 0]


def extrinsic_laplacian(in_mesh, num_eigs):
    V = in_mesh.vertices
    E = in_mesh.undirected_edges()
    vals = V[E[:, 1]]
    Wx = sparse.csr_matrix((vals[:, 0], (E[:, 0], E[:, 1])), shape=(in_mesh.num_vertices, in_mesh.num_vertices))
    Wy = sparse.csr_matrix((vals[:, 1], (E[:, 0], E[:, 1])), shape=(in_mesh.num_vertices, in_mesh.num_vertices))
    Wz = sparse.csr_matrix((vals[:, 2], (E[:, 0], E[:, 1])), shape=(in_mesh.num_vertices, in_mesh.num_vertices))
    _, evecsx = eigs(Wx, num_eigs, which='LM')
    _, evecsy = eigs(Wy, num_eigs, which='LM')
    _, evecsz = eigs(Wz, num_eigs, which='LM')
    evecsx = np.sum(evecsx.real, axis=1)
    evecsy = np.sum(evecsy.real, axis=1)
    evecsz = np.sum(evecsz.real, axis=1)
    return np.vstack((evecsx, evecsy, evecsz))
