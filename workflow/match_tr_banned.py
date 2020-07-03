import numpy as np
import pandas as pd
import sys
from fuzzywuzzy import fuzz
import networkx as nx
import utils


if __name__ == "__main__":

    # Get Input
    TR_SUSPENDED_PAIRS_FILE = sys.argv[1]
    OUTPUT_FILE = sys.argv[2]

    # Connect to graph database
    graph = utils.get_db()

    # Load the list of journal pairs suspended by TR
    df = pd.read_csv(TR_SUSPENDED_PAIRS_FILE, sep="\t")
    cartel_journals = np.unique(df[["Recipient", "Donor"]].values)

    # Merge overlapping pairs into one group
    cartel_list = []
    cid = 0
    for year, dg in df.groupby("YearReported"):
        G = nx.Graph()
        for _, row in dg.iterrows():
            G.add_edge(row["Donor"], row["Recipient"])
        coms = nx.connected_components(G)
        coms = [list(c) for c in coms]
        for c in coms:
            cartel_list += [pd.DataFrame({"year": year, "Name": c, "group_id": cid})]
            cid = cid + 1
    cartel_list = pd.concat(cartel_list, ignore_index=True)

    # Retrieve the list of all journals from database
    query = """
    MATCH (n: Journal)
    return toInteger(n.JournalId) as mag_journal_id, n.NormalizedName as name
    """
    journals = graph.run(query).to_data_frame()

    # Matching journals by names
    name2id = {}
    for fi, wos_journal_name in enumerate(cartel_journals):

        jid = -1
        query = """
        MATCH (n: Journal)
        where n.NormalizedName = '%s'
        return toInteger(n.JournalId) as mag_journal_id, n.NormalizedName as name
        """ % (
            wos_journal_name.lower()
        )

        res = graph.run(query).to_data_frame()

        if res.shape[0] == 1:  # exact match
            jid = res["mag_journal_id"][0]
        else:  # fuzzy match
            jid = -1
            for i, journal in journals.iterrows():

                jid = journal["mag_journal_id"]
                name = journal["name"]

                sim = fuzz.ratio(name.lower(), wos_journal_name.lower())

                if sim > 95:
                    break
            print("Not exact match. Should check manually : ", wos_journal_name, name)
        name2id[wos_journal_name] = jid

    # Save to file
    # nodes = pd.DataFrame({"Name": cartel_journals})
    # nodes["mag_journal_id"] = nodes["Name"].apply(lambda x: name2id[x])
    cartel_list["mag_journal_id"] = cartel_list["Name"].apply(lambda x: name2id[x])
    cartel_list.to_csv(OUTPUT_FILE, sep="\t", index=False)
