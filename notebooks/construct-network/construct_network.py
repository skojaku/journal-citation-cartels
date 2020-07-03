import numpy as np
import pandas as pd
import py2neo
import pickle
import os,sys
from scipy import sparse

def edges2adj(edges, raw_edges, year, pcount):

    # Uniqify edges
    def uniqify_edges(edges, pcount):
        ccount = edges.groupby(["target"])["s_target"].nunique()
        nodes = pd.DataFrame({"ccount": ccount})
        nodes = nodes.reset_index().rename(columns={"target": "id"})
        edges = edges.groupby(["source", "target"]).size().reset_index(name="w")
        return nodes, edges

    node_table, edges = uniqify_edges(edges, pcount)
    _, raw_edges = uniqify_edges(raw_edges, pcount)

    # Add paper count
    _pcount = pcount[((year - 2) <= pcount.year) & (pcount.year < year)].copy()
    _pcount = _pcount.groupby("id").agg("sum")["pcount"].reset_index()
    node_table = pd.merge(
        left=node_table, right=_pcount, left_on="id", right_on="id", how="left"
    )
    node_table = node_table.rename(columns={"id": "neo4jid"})
    node_table["jif"] = node_table["ccount"] / node_table["pcount"]

    username = "neo4j"
    password = "FSailing4046"
    graph_db = py2neo.Graph(
        bolt=True, host="localhost", user=username, password=password
    )
    query = "MATCH (n:Journal) return ID(n) as id, n.NormalizedName as name"
    journals = graph_db.run(query).to_data_frame()

    # Compute the journal imapct factor of each journal
    nodes = np.unique(edges[["source", "target"]].values)
    node_table = pd.merge(
        left=pd.DataFrame({"neo4jid": nodes, "node_id": np.arange(nodes.shape[0])}),
        right=node_table,
        left_on="neo4jid",
        right_on="neo4jid",
        how="left",
    ).fillna(0)

    # Construct the adjacency matrix for journals
    N = node_table.shape[0]
    edges = (
        pd.merge(
            left=edges,
            right=node_table[["node_id", "neo4jid"]].rename(
                columns={"node_id": "source_id"}
            ),
            left_on="source",
            right_on="neo4jid",
            how="left",
        )
        .drop(columns=["neo4jid", "source"])
        .rename(columns={"source_id": "source"})
    )

    edges = (
        pd.merge(
            left=edges,
            right=node_table[["node_id", "neo4jid"]].rename(
                columns={"node_id": "target_id"}
            ),
            left_on="target",
            right_on="neo4jid",
            how="left",
        )
        .drop(columns=["neo4jid", "target"])
        .rename(columns={"target_id": "target"})
    )
    edges = edges.rename(columns={"w": "weight"})
    edges["source"] = edges["source"].astype(int)
    edges["target"] = edges["target"].astype(int)

    raw_edges = (
        pd.merge(
            left=raw_edges,
            right=node_table[["node_id", "neo4jid"]].rename(
                columns={"node_id": "source_id"}
            ),
            left_on="source",
            right_on="neo4jid",
            how="left",
        )
        .drop(columns=["neo4jid", "source"])
        .dropna()
        .rename(columns={"source_id": "source"})
    )

    raw_edges = (
        pd.merge(
            left=raw_edges,
            right=node_table[["node_id", "neo4jid"]].rename(
                columns={"node_id": "target_id"}
            ),
            left_on="target",
            right_on="neo4jid",
            how="left",
        )
        .drop(columns=["neo4jid", "target"])
        .dropna()
        .rename(columns={"target_id": "target"})
    )
    raw_edges = raw_edges.rename(columns={"w": "weight"})
    raw_edges["source"] = raw_edges["source"].astype(int)
    raw_edges["target"] = raw_edges["target"].astype(int)

    A = sparse.csc_matrix(
        (edges.weight.values, (edges.source, edges.target)), shape=(N, N)
    )
    Araw = sparse.csc_matrix(
        (raw_edges.weight.values, (raw_edges.source, raw_edges.target)), shape=(N, N)
    )

    def add_citation_from_retracted_papers(B, node_table, year):
        # add retracted journals
        if (year == 2010) or (year == "all"):
            B = sparse.lil_matrix(B)
            dst = np.where(node_table["name"] == "cell transplantation")[0][0]
            src_1 = np.where(node_table["name"] == "medical science monitor")[0][0]
            src_2 = np.where(node_table["name"] == "the scientific world journal")[0][0]
            B[src_1, dst] = B[src_1, dst] + 445
            B[src_2, dst] = B[src_2, dst] + 96
            B[src_1, src_1] = B[src_1, src_1] + 44
            B[src_2, src_2] = B[src_2, src_2] + 26
            B = sparse.csc_matrix(B)

            node_table.loc[
                node_table["name"] == "medical science monitor", "pcount"
            ] += 1
            node_table.loc[
                node_table["name"] == "the scientific world journal", "pcount"
            ] += 1

        if (year == 2011) or (year == "all"):
            B = sparse.lil_matrix(B)
            ct = np.where(node_table["name"] == "cell transplantation")[0][0]
            msm = np.where(node_table["name"] == "medical science monitor")[0][0]
            swj = np.where(node_table["name"] == "the scientific world journal")[0][0]
            ti = np.where(node_table["name"] == "technology and innovation")[0][0]
            B[msm, ct] = B[msm, ct] + 87
            B[msm, msm] = B[msm, msm] + 32
            B[swj, ct] = B[swj, ct] + 109
            B[swj, swj] = B[swj, swj] + 29
            B[ct, ti] = B[ct, ti] + 24
            B = sparse.csc_matrix(B)

            node_table.loc[node_table["name"] == "cell transplantation", "pcount"] += 1
            node_table.loc[
                node_table["name"] == "medical science monitor", "pcount"
            ] += 1
            node_table.loc[
                node_table["name"] == "the scientific world journal", "pcount"
            ] += 1

        return B, node_table

    node_table = pd.merge(
        left=node_table, right=journals, left_on="neo4jid", right_on="id", how="left"
    )

    A, node_table = add_citation_from_retracted_papers(A, node_table, year)
    Araw, _ = add_citation_from_retracted_papers(Araw, node_table.copy(), year)

    # Add out-in degree info to node table
    outdeg = np.array(A.sum(axis=1)).reshape(-1)
    indeg = np.array(A.sum(axis=0)).reshape(-1)
    outdeg_raw = np.array(Araw.sum(axis=1)).reshape(-1)
    indeg_raw = np.array(Araw.sum(axis=0)).reshape(-1)

    node_table["indeg"] = indeg
    node_table["outdeg"] = outdeg
    node_table["indeg_raw"] = indeg_raw
    node_table["outdeg_raw"] = outdeg_raw
    node_table["ccount"] = node_table["indeg"]
    return A, Araw, node_table

if __name__ == "__main__":

    PCOUNT_FILE = sys.argv[1]
    YEAR = int(sys.argv[2])
    OUTPUT_FILE  = sys.argv[3]
   
    # Parameters
    window_length = 2
    ys = YEAR - window_length
    yf = YEAR
    pcount = pd.read_csv(PCOUNT_FILE)

    # Connect to the database
    username = "neo4j"
    password = "FSailing4046"
    uri = "bolt://127.0.0.1:7687"
    graph = py2neo.Graph(bolt=True, host="localhost", user=username, password=password)
    
    # Find the edges between journals 
    query = """
    MATCH (jtrg:Journal)<-[:published_from]-(trg:Paper)<-[:cites]-(src:Paper {Year:%d})-[:published_from]->(jsrc:Journal)
    where trg.Year<%d and trg.Year >= %d
    return ID(jsrc) as source, ID(jtrg) as target, ID(trg) as p_target, ID(src) as s_target
    """ % (
        yf,
        yf,
        ys,
    )
    edges = graph.run(query).to_data_frame()
   
    query = """
    MATCH (jtrg:Journal)<-[:published_from]-(trg:Paper)<-[:cites]-(src:Paper {Year:%d})-[:published_from]->(jsrc:Journal)
    return ID(jsrc) as source, ID(jtrg) as target, ID(trg) as p_target, ID(src) as s_target
    """ % (
        yf
    )
    raw_edges = graph.run(query).to_data_frame()
    
    # Convert to the adjacency matrices 
    A, Araw, nodes = edges2adj(edges, raw_edges, YEAR, pcount)
    
    # Save 
    with open(OUTPUT_FILE, "wb") as f:
        pickle.dump({"node_table": nodes, "A": A, "Araw": Araw}, f)
