import numpy as np
from scipy import sparse
import networkx as nx


def to_adjacency_matrix(net, node_labels=None):
    if sparse.issparse(net):
        return sparse.csr_matrix(net), np.arange(net.shape[0])
    elif "networkx" in "%s" % type(net):
        if node_labels is not None:
            G = nx.subgraph(net, node_labels)
            return nx.adjacency_matrix(G, node_labels), node_labels
        else:
            return nx.adjacency_matrix(net), list(net.nodes())
    elif "numpy.ndarray" == type(net):
        return sparse.csr_matrix(net), np.arange(net.shape[0])


def to_community_matrix(community_ids):
    K = np.max(community_ids) + 1
    N = community_ids.size
    return sparse.csc_matrix((np.ones(N), (np.arange(N), community_ids)), shape=(N, K))


def construct_adjacency_matrix(src, dst, w, N):
    """
    Construct adjacency matrix from the list of edges

    Parameters
    ----------
    src : numpy.ndarray
        Source nodes 
    dst : numpy.ndarray
        Target nodes 
    w : numpy.ndarray
        Weight of edges
    N : int
        Number of nodes

    Returns
    -------
    A : scipy sparse matrix
        Adjacency matrix where A[i,j] indicate the 
        weight of the edge from node i to node j
    """
    return sparse.csr_matrix((w, (src, dst)), shape=(N, N))


def find_non_self_loop_edges(A):
    """
    Parameters
    ---------
    A : scipy sparse matrix
    
    Returns
    ------
    r: numpy.ndarray
        Row ids for the non-zero elements
    c: numpy.ndarray
        Column ids for the non-zero elements
    v: numpy.ndarray
        Values of non-zero elements 
    """
    r, c, v = sparse.find(A)
    non_self_loop = r != c
    r, c, v = r[non_self_loop], c[non_self_loop], v[non_self_loop]
    return r, c, v

    # Pack the community ids to an array
    community_ids = []
    if "networkx" in "%s" % type(net):
        community_ids = np.array([community_membership[x] for x in net.nodes()])
    else:
        community_ids = np.array([community_membership[x] for x in range(A.shape[0])])


def to_networkx_graph(A, nodes, create_using=nx.DiGraph):
    """
    Parameters
    ----------
    A : scipy sparse matrix
        Adjacency matrix
    nodes : list or numpy array
        List of node names in order of nodes in A

    Returns
    ------
    G : networkx.Graph
    """
    G = nx.from_scipy_sparse_matrix(A, create_using=create_using)
    return nx.relabel_nodes(G, dict(zip(np.arange(len(nodes)), nodes)))


def pairing(k1, k2, ordered=True):
    """
    Cantor pairing function
    """
    k12 = k1 + k2
    if ordered == False:
        return (k12 * (k12 + 1)) * 0.5 + np.minimum(k1, k2)
    else:
        return (k12 * (k12 + 1)) * 0.5 + k2


def depairing(z):
    """
    Inverse of Cantor pairing function
    """
    w = np.floor((np.sqrt(8 * z + 1) - 1) * 0.5)
    t = (w ** 2 + w) * 0.5
    y = np.round(z - t).astype(np.int64)
    x = np.round(w - y).astype(np.int64)
    return x, y
