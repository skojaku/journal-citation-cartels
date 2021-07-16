#!/usr/bin/env python
# coding: utf-8

import graph_tool.all as gt
import numpy as np
import pandas as pd
import os,sys
import utils
from scipy import sparse


def to_graph_tool(adj, membership=None):
    g = gt.Graph(directed=True)
    r, c, v = sparse.find(adj)
    nedges = v.size
    edge_weights = g.new_edge_property("double")
    g.edge_properties["weight"] = edge_weights
    g.add_edge_list(
        np.hstack([np.transpose((r, c)), np.reshape(v, (nedges, 1))]),
        eprops=[edge_weights],
    )

    return g


def make_community_table(states, nodes):
    b = states.get_blocks()
    cids = b.a
    return pd.DataFrame({"node_id":np.arange(nodes.size), "mag_affiliation_id": nodes, "community_id": cids})


if __name__ == "__main__":

    OUTPUT = sys.argv.pop()
    YEARS = [int(y) for y in sys.argv[1:]]

    print("years", YEARS)

    print("Loading networks")
    A, Araw, nodes = utils.load_network(YEARS)

    print("Construct graph tool graph object")
    G = to_graph_tool(A)

    print("Estimating")
    states = gt.minimize_blockmodel_dl(
        G,
       
        # deg_corr=True,
        state_args=dict(eweight=G.ep.weight),
        multilevel_mcmc_args=dict(B_max=np.round(A.shape[0] / 3).astype(int)),

        # verbose=True,
        #TODO params have changed so this no longer works
    )

    print("Save")
    community_table = make_community_table(states, nodes)
    community_table.to_csv(OUTPUT, sep="\t")
