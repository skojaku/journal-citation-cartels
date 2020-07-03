import numpy as np
from scipy import sparse
import pandas as pd
import networkx as nx
from cidre import utils


def detect(
    A, threshold, is_excessive, min_group_edge_num=0,
):
    """
    CIDRE algorithm 

    Parameters
    -----------
    A : scipy sparse matrix
        Adjacency matrix 
    threshold : float
        The algorithm seeks the groups of nodes that have a
        donor score or a recipient score larger than or equal to the threshold value.
    is_excessive : filtering function
        is_excessive(srg, trg, w) returns True if the edge from src to trg with weight w 
        is excessive. Otherwise is_excessive(srg, trg, w) returns False.
    min_group_edge_num: int (Optional; Default 0)
        The minimum number of edges that the detected group has. 
        If the algoirthm finds a group of nodes that contain less than or equal to min_edge_num, 
        the algorithm exlcudes the group from the list of detected groups.

    Returns
    -------
    df : pandas.DataFrame
        Table of nodes detected by CIDRE. df consists of the following columns:
        - node_labels : label of nodes
        - group id : ID of the group to which the node belongs
        - donor_score : donor score for the node
        - recipient_score : recipient score for the node
        - is_donor : True if the node is a donor. Otherwise False.
        - is_recipient : True if the node is a recipient. Otherwise False.
    """

    # Filter edges before grouping
    src, dst, w = utils.find_non_self_loop_edges(A)
    excessive_edges = is_excessive(src, dst, w)

    A_pruned = utils.construct_adjacency_matrix(
        src[excessive_edges], dst[excessive_edges], w[excessive_edges], A.shape[0]
    )

    # Find the group of nodes U with
    # a donor score or a recipient score
    # larger than or equal to the threshold
    num_nodes = A.shape[0]
    U = np.ones(num_nodes)
    indeg_zero_truncated = np.maximum(np.array(A.sum(axis=0)).ravel(), 1.0)
    outdeg_zero_truncated = np.maximum(np.array(A.sum(axis=1)).ravel(), 1.0)
    while True:
        # Compute the donor score, recipient score and cartel score
        donor_score = np.multiply(U, (A_pruned @ U) / outdeg_zero_truncated)
        recipient_score = np.multiply(U, (U @ A_pruned) / indeg_zero_truncated)

        # Drop the nodes with a cartel score < threshold
        drop_from_U = (U > 0) * (np.maximum(donor_score, recipient_score) < threshold)

        # Break the loop if no node is dropped from the cartel
        if np.any(drop_from_U) == False:
            break

        # Otherwise, drop the nodes from the cartel
        U[drop_from_U] = 0

    # Find the nodes in U
    nodes_in_U = np.where(U)[0]

    # Partition U into disjoint groups, U_l
    A_U = A_pruned[:, nodes_in_U][nodes_in_U, :].copy()
    net_U = nx.from_scipy_sparse_matrix(A_U, create_using=nx.DiGraph)
    net_U.remove_nodes_from(list(nx.isolates(net_U)))
    df_Ul_list = []
    for _, _nd in enumerate(nx.weakly_connected_components(net_U)):
        nodes_in_Ul = nodes_in_U[np.array(list(_nd))]

        # Remove the group U_l if
        # U_l does not contain edges less than or equal to
        # min_group_edge_num
        A_Ul = A[nodes_in_Ul, :][:, nodes_in_Ul]
        num_edges_in_Ul = A_Ul.sum() - A_Ul.diagonal().sum()
        if num_edges_in_Ul <= min_group_edge_num:
            continue

        # Pack the results into a pandas
        df_Ul = pd.DataFrame(
            {
                "node_id": nodes_in_Ul,
                "group_id": np.ones_like(nodes_in_Ul) * len(df_Ul_list),
                "recipient_score": recipient_score[nodes_in_Ul],
                "donor_score": donor_score[nodes_in_Ul],
                "is_recipient": (recipient_score[nodes_in_Ul] >= threshold).astype(int),
                "is_donor": (donor_score[nodes_in_Ul] >= threshold).astype(int),
            }
        )
        df_Ul_list += [df_Ul]
    df_U = pd.concat(df_Ul_list, ignore_index=True)
    return df_U
