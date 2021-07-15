import numpy as np
import py2neo
import pandas as pd
import networkx as nx
from scipy import sparse

DATA_DIR = "data"


def get_db():
    username = "neo4j"
    password = "dolphinsNeverSleep"
    uri = "http://localhost:7474"
    graph = py2neo.Graph(uri=uri, user=username, password=password)
    return graph


def construct_adjacency_matrix(nodes, edges):

    # Compute the mapping from node ids to id
    max_node_id = np.max(nodes)
    node2id = -np.ones(max_node_id + 1)
    node2id[nodes] = np.arange(nodes.size)

    max_edge_id = np.max(edges[:, :2])

    # Remove edges that do not exist in nodes list
    edges = edges[(np.max(edges[:, :2], axis=1) <= max_node_id), :]

    edges[:, :2] = node2id[edges[:, :2].reshape(-1)].reshape((edges.shape[0], 2))

    # Remove edges that do not exist in nodes list again
    edges = edges[(np.min(edges[:, :2], axis=1) >= 0), :]

    # Adjacency matrix
    N = len(nodes)
    A = sparse.csr_matrix((edges[:, 2], (edges[:, 0], edges[:, 1])), shape=(N, N))

    return A


def load_network(years, net_data_dir=None):

    if hasattr(years, "__len__") == False:
        years = [years]

    if net_data_dir is None:
        net_data_dir = "%s/networks/" % DATA_DIR

    # Load the node and edge files
    df_nodes = []
    df_edges = []
    df_raw_edges = []
    for year in years:

        node_file = "{root}/nodes-{year}.csv".format(
            root=net_data_dir, year=year
        )
        edge_file = "{root}/edges-{year}.csv".format(
            root=net_data_dir, year=year
        )
        raw_edge_file = "{root}/raw-edges-{year}.csv".format(
            root=net_data_dir, year=year
        )

        _df_nodes = pd.read_csv(node_file, sep="\t")
        _df_edges = pd.read_csv(edge_file, sep="\t")
        _df_raw_edges = pd.read_csv(raw_edge_file, sep="\t")

        df_nodes += [_df_nodes]
        df_edges += [_df_edges]
        df_raw_edges += [_df_raw_edges]

    df_nodes = pd.concat(df_nodes, ignore_index=True)
    df_edges = pd.concat(df_edges, ignore_index=True)
    df_raw_edges = pd.concat(df_raw_edges, ignore_index=True)

    # Nodes
    nodes = np.unique(df_edges[["source", "target"]].values.reshape(-1))

    # Edges
    edges = df_edges[["source", "target", "w"]].values
    raw_edges = df_raw_edges[["source", "target", "w"]].values

    # Construct networks
    A = construct_adjacency_matrix(nodes, edges)
    Araw = construct_adjacency_matrix(nodes, raw_edges)
    
    return A, Araw, nodes

def neo4jid2mag_journalid(neo4jids):

    graph = get_db()
    query = """
    match (j:Journal)
    where ID(j) in [{neo4jids}]
    return ID(j) as neo4jid, j.JournalId as journal_id 
    """.format(neo4jids = ",".join(["%d" % x for x in neo4jids]))
    df = graph.run(query).to_data_frame()
    return df.set_index("neo4jid").loc[neo4jids,"journal_id"].values


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
    return nx.relabel_nodes(G, dict(zip(np.arange(nodes.size), nodes)))


def load_detected_cartels(years, cartel_dir):
    cartel_table_list = []
    group_id_offset = 0
    for year in years:
        cartel_table = pd.read_csv(
            "{root}/cartels-{year}.csv".format(root=cartel_dir, year=year), sep="\t"
        )
        cartel_table["year"] = year
        #cartel_table["group_id"] += group_id_offset
        cartel_table["gross_group_id"] = cartel_table["group_id"]
        cartel_table["gross_group_id"] += group_id_offset
        group_id_offset = np.max(cartel_table["gross_group_id"].values) + 1
        cartel_table_list += [cartel_table]
    cartel_table = pd.concat(cartel_table_list, ignore_index=True)
    return cartel_table

def slice_groups(T, group_ids, group_id_col):
    s = T[group_id_col].apply(lambda x: x in group_ids).values
    return T[s]
