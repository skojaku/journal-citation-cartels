import numpy as np
import pandas as pd
import utils
import sys

sys.path.append(os.path.abspath(os.path.join("libs/cidre")))
from cidre import cidre, filters


#
# Parameters
#
if __name__ == "__main__":

    YEAR = int(sys.argv[1])
    NETWORK_DIR = sys.argv[2]
    THETA = float(sys.argv[3])
    ALPHA = float(sys.argv[4])
    COMMUNITY_FILE = sys.argv[5]
    OUTPUT = sys.argv[6]

    # Load the network data
    A_eff, A_gen, nodes = utils.load_network(YEAR, NETWORK_DIR)

    # Load the communty membership
    community_table = pd.read_csv(COMMUNITY_FILE, sep="\t")
    community_ids = (
        community_table.set_index("mag_journal_ids").loc[nodes, "community_id"].values
    )

    # Define the filter
    is_excessive_func = filters.get_dcsbm_threshold_filter(
        A_eff, A_gen, community_ids, ref_frac_weight=0.5, alpha=ALPHA
    )

    # Detect cartel
    cartel_table = cidre.detect(A_eff, THETA, is_excessive_func, min_group_edge_num=50)

    # Rename node labels
    cartel_table["mag_journal_id"] = cartel_table["node_id"].apply(lambda x : nodes[x])

    # Save results
    cartel_table.to_csv(OUTPUT, sep="\t")
