import numpy as np
import pandas as pd
import random
from scipy import stats, sparse
import ccartel
import pickle


def touch(fname, times=None):
    with open(fname, "a"):
        os.utime(fname, times)


#
# Parameters
#
YEAR_LIST = list(range(2000, 2020))
THETA_LIST = [0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]
ALPHA = 0.01
COMMUNITY_LAYER_ID = 0

for YEAR in YEAR_LIST:

    # if YEAR <2010: continue
    #
    # Load the data
    #
    with open("data/networks/%d.pickle" % YEAR, "rb") as f:
        R = pickle.load(f)
        A, Araw, node_table = R["A"], R["Araw"], R["node_table"]
    with open("data/communities/nonnested-sbm/community-year=all.pickle", "rb") as f:
        R = pickle.load(f)
        community_table = R["community_list"]
    node_community_table = pd.merge(
        node_table, community_table, left_on="neo4jid", right_on="neo4jid", how="left"
    )

    N = A.shape[0]
    K = node_community_table.community_level_0.values.max() + 1
    C = sparse.csc_matrix(
        (
            np.ones(node_community_table.shape[0]),
            (
                node_community_table.node_id.values,
                node_community_table.community_level_0.values,
            ),
        ),
        shape=(N, K),
    )

    #
    # Cartel Detection
    #
    cartel_table, A_sig = ccartel.detect(
        A, Araw, threshold_list=THETA_LIST, C_SBM=C, alpha=ALPHA
    )

    sz_max = pd.DataFrame(cartel_table.groupby("threshold")["csize"].max()).rename(
        columns={"csize": "max"}
    )
    sz_mean = pd.DataFrame(cartel_table.groupby("threshold")["csize"].mean()).rename(
        columns={"csize": "mean"}
    )
    sz_num = pd.DataFrame(
        cartel_table.groupby("threshold").apply(lambda x: x["cid"].max() + 1)
    ).rename(columns={"csize": "num"})
    print("-----------")
    print("YEAR = %d" % YEAR)
    print(pd.concat([sz_max, sz_mean, sz_num], axis=1))
    #
    # Save results
    #
    resfilename = "data/cartels/%d.pickle" % YEAR
    cartel_table = pd.merge(
        left=cartel_table,
        right=node_community_table,
        left_on="node_id",
        right_on="node_id",
        how="left",
    )
    res = {"cartel_table": cartel_table, "A_sig": A_sig, "A": A}
    with open(resfilename, "wb") as f:
        pickle.dump(res, f)
