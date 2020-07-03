import numpy as np
from scipy import stats, sparse
import sys
import pandas as pd
import networkx as nx
from cidre import utils
from functools import partial


def get_dcsbm_threshold_filter(
    A, A_ref, community_ids, ref_frac_weight=1.0, alpha=0.01
):
    """
    Filtering function used in the original CIDRE algorithm.
    The function is a combination of two filterings, dcSBM_filter and threshold filter. 
    See get_dcSBM_filter and get_threshold_filter for details. 

    Parameters
    ----------
    net : networkx.Graph
        Network. 
    net_ref : networkx.Graph
        Reference network. We remove an edge with weight w <= w_ref * ref_frac_weight, where w and w_ref is the weight of the edge in
        the net and net_ref 
    community_membership : dict
        Group membership of nodes. The keys and values of the dict object are
        the names of nodes and IDs of groups to which the nodes belong.
    ref_frac_weight : float
    alpha : float
        Significance level for the statistical test based on the stochastic block model

    Returns
    -------
    cidre_filter : function
        Filtering function 
    """

    dcsbm_filter = get_dcSBM_filter(A, community_ids, alpha)
    threshold_filter = get_threshold_filter(A_ref, ref_frac_weight)

    def cidre_filter(src, trg, w):
        return dcsbm_filter(src, trg, w) * threshold_filter(src, trg, w)

    return cidre_filter


def get_dcSBM_filter(A, community_ids, alpha):
    """
    Filtering edges based on the dcSBM

    Parameters
    ----------
    net : networkx.Graph
        Given network
    community_membership : dict
        Group membership of nodes. The keys and values of the dict object are
        the names of nodes and IDs of groups to which the nodes belong.
    alpha : float 
        Significance level for the statistical test based on the stochastic block model

    Returns
    -------
    dcSBM_filter : function
        Filtering function 
    """

    # Find the edges whose weights are larger than that expected for the null model
    src, trg, weight = find_significant_edges_dcSBM(A, community_ids, alpha)

    return make_filter_func(src, trg, None, A.shape[0])


def get_threshold_filter(A, frac_weight=0.5):
    """
    Filtering edges by thresholding 

    Parameters
    ----------
    net : networkx.Graph
        Given network
    frac_weight : float
        We remove the edges whose weight is smaller than or equal to w * frac_weight, where
        w is the weight of edge in net

    Returns
    -------
    threshhold_filter : function
        Filtering function 
    """
    src, trg, w = sparse.find(A)
    return make_filter_func(src, trg, w * frac_weight, A.shape[0])


def make_filter_func(src, trg, wth, N):
    """
    Make a filter function

    Parameters
    ----------
    src : numpy.ndarray
        Source node
    trg : numpy.ndarray
        Target node
    wth : numpy.ndarray
        Weight of edges between source and target nodes

    Returns
    -------
    filter : function
        Filtering function 
    """
    if wth is None:
        wth = 1e-8 * np.ones_like(src)

    # Convert pairs of integers into integers
    W = sparse.csr_matrix((wth, (src, trg)), shape=(N, N))

    # Define the is_excessive function for CIDRE
    def is_excessive(src_, trg_, w_, W):
        wth = np.array(W[(src_, trg_)]).reshape(-1)
        return (w_ >= wth) * (wth > 0)

    return partial(is_excessive, W=W)


def find_significant_edges_dcSBM(A, community_ids, alpha=0.01):
    """
    
    Filter edges based on the degree-corrected stochastic block model 

    Parameters
    ----------
    A : scipy sparse matrix
        Adjacency matrix for the network
    community_ids :  dict


    Returns
    -------
    A_filtered : scipy sparse matrix
        The adjacnecy matrix of the network composed of 
        edges whose weight is larger or equal to the threshold values.
    """
    # Compute the p-values
    p_value, src, dst, w = calc_p_values_dcsbm(A, community_ids)

    # Perform the Benjamini-Hochberg statistical test
    is_significant = benjamini_hochberg_test(p_value, alpha)

    return src[is_significant], dst[is_significant], w[is_significant]


def calc_p_values_dcsbm(A, community_ids):
    """
    Calculate the p_values using the degree-corrected stochastic block model. 

    Parameters
    ----------
    A : scipy sparse matrix
        Adjacency matrix, where A[i,j] indicates the weight of the edge 
        from node i to node j
    community_ids :  numpy.ndarray
        community_ids[i] indicates the ID of the group to which node i belongs

    Returns
    -------
    p-value : p-values 
    ---
    """

    N = A.shape[0]
    indeg = np.array(A.sum(axis=0)).reshape(-1)
    outdeg = np.array(A.sum(axis=1)).reshape(-1)
    C_SBM = utils.to_community_matrix(community_ids)

    Lambda = C_SBM.T @ A @ C_SBM
    Din = np.array(Lambda.sum(axis=0)).reshape(-1)
    Dout = np.array(Lambda.sum(axis=1)).reshape(-1)

    theta_in = indeg / np.maximum(C_SBM @ Din, 1.0)
    theta_out = outdeg / np.maximum(C_SBM @ Dout, 1.0)

    src, dst, w = utils.find_non_self_loop_edges(A)
    lam = (
        np.array(Lambda[community_ids[src], community_ids[dst]]).reshape(-1)
        * theta_out[src]
        * theta_in[dst]
    )
    lam = np.maximum(lam, 1.0)
    pvals = 1.0 - stats.poisson.cdf(w - 1, lam)

    return pvals, src, dst, w


def benjamini_hochberg_test(pvals, alpha):
    """
    Benjamini-Hochberg statistical test


    Parameters
    ----------
    pvals : numpy.ndarray
        Array of p-values
    alpha : float
        Statistical significance level

    Return 
    ------
    significant : numpy.ndarray
        significant[i] = True if the ith element is significant.
        Otherwise signfiicant[i] = False.
    """
    order = np.argsort(pvals)
    M = pvals.size
    last_true_id = np.where(pvals[order] <= (alpha * np.arange(1, M + 1) / M))[0][-1]
    is_sig = np.zeros(M)
    is_sig[order[: (last_true_id + 1)]] = 1
    return is_sig > 0
