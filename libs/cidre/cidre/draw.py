import pandas as pd
import numpy as np
from scipy import sparse
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib import patches
import matplotlib.colors as colors
import textwrap
import re


class DrawCartel:
    def __init__(self):
        self.theta_1 = np.pi * 0.7
        self.angle_margin = 3 * np.pi / 25
        self.node2color = {}
        self.angles = None
        self.radius = 2
        self.label_node_margin = 0.35
        self.group_arc_node_margin = 0.1
        self.edge_norm = lambda x: np.power(x, 1 / 2)
        self.max_edge_width = 15
        self.font_size = 15 
        self.node_size = 0.25
        self.label_width = 15
        self.max_label_width = 35
        self.group_order = {"source": 0, "target": 1, "reciprocal": 2, "other": 3}

    def draw(
        self,
        A,
        node_ids,
        donor_score,
        recipient_score,
        theta,
        node_names,
        cmap=None,
        ax=None,
    ):
        """
        Draw citation networks within a citation cartel
        
        Parameters
        ----------
        A : scipy.sparse matrix
            The adjacency matrix for the network with all nodes
        node_ids : np.array or list
            The node ids of the nodes in the cartel
        donor_score : np.array or list
            The donor score of the nodes in the cartel.
            We assume the donor_score[i] indicates the 
            donor score for node_ids[i]
        recipient_score : np.array or list
            The recipient score of the nodes in the cartel.
            We assume the recipient_score[i] indicates the 
            recipient score for node_ids[i]
        theta : float
            The threshold for the donor and recipient score
        node_name : list
            Node names. Assume that node_name[i] indicates the 
            name of the node_ids[i]
        cmap : matplotlib color map or list 
            Color map or List of strings indicating hex code
        ax : axis
        
        Return 
        ------
        ax : axis
        """

        #
        # Input formatting
        #
        node_ids = np.array(node_ids)
        donor_score = np.array(donor_score)
        recipient_score = np.array(recipient_score)

        # Classify nodes into donor, recipient and reciprocal
        node_types = self.classify_nodes(donor_score, recipient_score, theta)

        # Change the angle for the reciprocal journals based on the number of it
        num_reciprocal = np.sum(
            np.array([node_types[i] == "reciprocal" for i in range(len(node_types))])
        )
        if num_reciprocal > 2:
            self.theta_1 = np.pi * 0.3
        else:
            self.theta_1 = np.pi * 0.7

        #
        # Construct the adjacency matrix with 'Other' node
        #
        brow = A[:, node_ids].sum(axis=0)
        bcol = A[node_ids, :].sum(axis=1)
        As = A[:, node_ids][node_ids, :].toarray()

        # Add 'Other' node to the adjacency matrix
        As = np.block([[As, bcol], [brow, np.array([0])]])
        As = np.array(As)
        node_types += ["other"]
        node_names += ["Other"]

        #
        # Calculate the positions and sizes
        #

        # Make node table
        num_nodes = len(node_types)
        node_table = pd.DataFrame(
            {"id": np.arange(num_nodes), "group": node_types, "name": node_names}
        )

        # Calculate the angle of each node
        node_table, self.angles = self.calc_node_angles(node_table)

        # Calculate the position of journals based on the angles
        node_table = self.calc_node_position(node_table)

        # Text folding
        node_table = self.fold_node_name(node_table)

        # Compute the edge positions based on the nodes
        edge_table = self.make_edge_table(node_table, As)

        # make color map
        self.make_color_map(node_table, cmap)

        #
        # Plot
        #
        self.plot_edges(node_table, edge_table, ax)

        self.plot_node_label(node_table, ax)

        self.plot_nodes(node_table, A, As, node_ids, ax)

        self.plot_group_arc(node_table, ax)

        self.trim(ax)

        return ax

    def classify_nodes(self, donor_score, recipient_score, threshold):
        is_recipient = recipient_score >= threshold
        is_donor = donor_score >= threshold
        is_reciprocal = is_recipient & is_donor
        is_recipient = is_recipient & (~is_reciprocal)
        is_donor = is_donor & (~is_reciprocal)
        node_type = is_recipient + 2 * is_donor + 3 * is_reciprocal
        node_type = np.array(["", "target", "source", "reciprocal"])[node_type]
        return node_type.tolist()

    def calc_node_angles(self, node_table):
        # Compute the coordinate of nodes
        self.theta_2 = np.pi - self.theta_1 - 2 * self.angle_margin

        node_table["within_group_id"] = -1
        node_table["angle"] = -1
        angles = {"margin_angle": self.angle_margin}
        for group_name in ["source", "target", "reciprocal", "other"]:
            dg = node_table[node_table.group == group_name]
            if group_name == "source":
                start_angle = -self.angle_margin - self.theta_1 - self.theta_2 / 2
                end_angle = start_angle + self.theta_1
            elif group_name == "target":
                start_angle = self.angle_margin + self.theta_2 / 2
                end_angle = start_angle + self.theta_1
            elif group_name == "reciprocal":
                start_angle = -self.theta_2 / 2
                end_angle = start_angle + self.theta_2
            elif group_name == "other":
                start_angle = self.theta_2 / 2 + self.angle_margin * 2 + self.theta_1
                end_angle = start_angle + self.theta_2

            ids = np.arange(dg.shape[0])
            node_table.loc[dg.index, "within_group_id"] = ids
            n = dg.shape[0]

            if (group_name == "reciprocal") and (n >= 2):
                a = (
                    (ids) * ((end_angle - start_angle) - self.angle_margin) / (n - 1)
                    + start_angle
                    + 0.5 * self.angle_margin
                )
            else:
                if n >= 2:
                    a = (
                        ids
                        * ((end_angle - start_angle) - 1.5 * self.angle_margin)
                        / (n - 1)
                        + start_angle
                        + 0.75 * self.angle_margin
                    )
                else:
                    a = (
                        (ids + 1)
                        * ((end_angle - start_angle) - 1.5 * self.angle_margin)
                        / (n + 1)
                        + start_angle
                        + 0.75 * self.angle_margin
                    )
                # node_table.loc[dg.index, "angle"] = (ids +1) * angle_group / (n-1) + start_angle
            node_table.loc[dg.index, "angle"] = a

            angles[group_name] = {"start": start_angle, "end": end_angle}
        return node_table, angles

    def calc_node_position(self, node_table):
        nodes = node_table.copy()
        nodes["x"] = self.radius * np.sin(nodes.angle)
        nodes["y"] = self.radius * np.cos(nodes.angle)
        return nodes

    def make_edge_table(self, node_table, As):

        # Compute the edge table
        src, trg = np.where(As)
        selfloop = src != trg
        src, trg = src[selfloop], trg[selfloop]
        w = As[(src, trg)]
        edge_table = pd.DataFrame({"src": src, "trg": trg, "w": w})

        edges = edge_table.copy()
        edges = pd.merge(
            edges,
            node_table[["id", "x", "y"]],
            left_on="src",
            right_on="id",
            how="left",
        ).rename(columns={"x": "src_x", "y": "src_y"})
        edges = pd.merge(
            edges,
            node_table[["id", "x", "y"]],
            left_on="trg",
            right_on="id",
            how="left",
        ).rename(columns={"x": "trg_x", "y": "trg_y"})

        # Normalize the maximum to be one
        wmax = np.maximum(
            np.max(np.triu(As[:, :-1][:-1, :], 1)),
            np.max(np.tril(As[:, :-1][:-1, :], 1)),
        )
        edges["w"] = edges["w"] / wmax
        edges["w"] = self.edge_norm(edges["w"])
        edges["w"] = edges["w"] / edges["w"].max()
        n = As.shape[0] - 1
        return edges

    def make_color_map(self, node_table, cmap):
        n = node_table.shape[0]

        # sort nodes
        _node_table = node_table.copy()
        _node_table["group_order"] = _node_table.apply(
            lambda x: self.group_order[x["group"]], axis=1
        )
        _node_table = _node_table.sort_values(by="group_order")
        
        if cmap is None:
            if _node_table.shape[0] <= 8:
                cmap = sns.color_palette().as_hex()
            elif _node_table.shape[0] <= 20:
                cmap = sns.color_palette().as_hex()
                cmap2 = sns.color_palette("husl", 12).as_hex()
                cmap = cmap + cmap2
            elif _node_table.shape[0] <= 20:
                cmap = sns.color_palette().as_hex()
                cmap2 = sns.color_palette("Paired").as_hex()
                cmap = cmap + [c for i, c in enumerate(cmap2) if i % 2 == 1] + [
                    c for i, c in enumerate(cmap2) if i % 2 == 0
                ]
            elif _node_table.shape[0] <= 40:
                # cmap = sns.color_palette("Set1").as_hex()
                cmap = sns.color_palette("tab20").as_hex()
                cmap_list = []
                for l in range(5):
                    cmap_list += [c for i, c in enumerate(cmap) if i % 2 == l]
                cmap_1 = cmap_list
                cmap = sns.color_palette("tab20b").as_hex()
                cmap_list = []
                for l in range(5):
                    cmap_list += [c for i, c in enumerate(cmap) if i % 2 == l]
                cmap_2 = cmap_list
                cmap = cmap_1 + cmap_2
            else:
                cmap = sns.color_palette("Spectral", n).as_hex()

        self.node2color = {}
        i = 0

        for _, row in _node_table.iterrows():
            if row["group"] == "other":
                self.node2color[row["id"]] = "#c4c4c4"
            else:
                self.node2color[row["id"]] = cmap[i]
                i += 1

        return self.node2color

    def plot_edges(self, node_table, edge_table, ax):
        _edges = edge_table.sort_values(by="w").sort_values(
            by=["src", "trg"], ascending=False
        )
        for i, edge in _edges.iterrows():
            if edge.src == edge.trg:
                continue
            x_pos = edge.src_x
            y_pos = edge.src_y
            dx = edge.trg_x - edge.src_x
            dy = edge.trg_y - edge.src_y
            length = np.sqrt(dx * dx + dy * dy)
            orient = np.array([edge.trg_x, edge.trg_y])

            w = edge["w"]
            style = """Simple,tail_width={w},head_width={w1}
                  """.format(
                w=w * self.max_edge_width, w1=2 * w * self.max_edge_width,
            )

            src_id = int(edge.src)
            trg_id = int(edge.trg)
            color = self.node2color[int(edge.src)]
            color = (
                color + "66"
                if node_table.iloc[src_id]["group"] == "other"
                else color + "cc"
            )
            kw = dict(arrowstyle=style, color=color, linewidth=0,)
            connectionstyle = "arc3,rad=.2"
            a3 = patches.FancyArrowPatch(
                (edge.src_x, edge.src_y),
                (edge.trg_x, edge.trg_y),
                # shrinkB=15,
                connectionstyle=connectionstyle,
                **kw
            )

            ax.add_patch(a3)

    def plot_node_label(self, node_table, ax):
        reciprocal_num = np.sum(node_table["group"].values == "reciprocal")

        texts = []
        for i, row in node_table.iterrows():
            x = row["x"] + (self.label_node_margin) * np.sin(row["angle"])
            y = row["y"] + (self.label_node_margin) * np.cos(row["angle"])
            if (x > 0) and (y > 0):
                ha = "left"
                va = "bottom"
            elif (x > 0) and (y < 0):
                ha = "left"
                va = "top"
            elif (x < 0) and (y < 0):
                ha = "right"
                va = "top"
            elif (x < 0) and (y > 0):
                ha = "right"
                va = "bottom"

            va = "center"
            if row["group"] == "reciprocal":
                if reciprocal_num > 2:
                    pass
                else:
                    ha = "center"
                    va = "bottom"
            if row["group"] == "other":
                ha = "center"
                va = "top"
            texts += [ax.text(x, y, row["name"], ha=ha, va=va, fontsize = self.font_size)]

    def plot_group_arc(self, node_table, ax):
        params = {"lw": 3, "fc": "white", "alpha": 0.3, "zorder": 0, "angle": 90}

        a3 = patches.Arc(
            (0, 0),
            2 * self.radius * (self.group_arc_node_margin + 1),
            2 * self.radius * (self.group_arc_node_margin + 1),
            theta1=-180 * self.angles["reciprocal"]["end"] / np.pi,
            theta2=-180 * self.angles["source"]["start"] / np.pi,
            ec="black",
            ls="-",
            **params
        )
        ax.add_patch(a3)

        a3 = patches.Arc(
            (0, 0),
            2 * self.radius * (self.group_arc_node_margin + 1.05),
            2 * self.radius * (self.group_arc_node_margin + 1.05),
            theta2=-180 * self.angles["reciprocal"]["start"] / np.pi,
            theta1=-180 * self.angles["target"]["end"] / np.pi,
            ec="black",
            ls="--",
            **params
        )
        ax.add_patch(a3)

    def trim(self, ax):
        R = self.radius * 1.2
        ax.set_xlim(left=-R, right=R)
        ax.set_ylim(bottom=-R, top=R)
        ax.axis("off")

    def plot_nodes(self, node_table, A, As, node_ids, ax):

        # Calculate the angle of pie
        indeg = np.array(A[:, node_ids].sum(axis=0)).reshape(-1)
        share = As[:-1, :-1] @ np.diag(1.0 / np.maximum(1, indeg))

        for i, row in node_table.iterrows():
            if row["group"] == "other":
                ax.pie(
                    [1],
                    startangle=90,
                    colors=[self.node2color[row["id"]]],
                    center=(row["x"], row["y"]),
                    radius=self.node_size,
                    wedgeprops={"edgecolor": self.node2color[i], "linewidth": 3},
                )
            else:
                order = np.argsort(share[:, i])

                node_color_list = [self.node2color[j] for j in order]

                ax.pie(
                    [1 - np.sum(share[:, i])]
                    + np.array(share[order, i]).reshape(-1).tolist(),
                    startangle=90,
                    colors=["#ffffffff"] + node_color_list,
                    center=(row["x"], row["y"]),
                    radius=self.node_size,
                    wedgeprops={"linewidth": 0},
                )
                c = patches.Circle(
                    (row["x"], row["y"]),
                    self.node_size,
                    fill=None,
                    edgecolor=self.node2color[row["id"]],
                    linewidth=3,
                )
                ax.add_patch(c)

    def fold_node_name(self, node_table):
        for g, dg in node_table.groupby("group"):
            if dg.shape[0] < 8:
                node_table.loc[dg.index, "name"] = dg["name"].apply(
                    lambda x: self.fold_text(
                        x, width=self.label_width, max_width=self.max_label_width
                    )
                )
            else:
                node_table.loc[dg.index, "name"] = dg["name"].apply(
                    lambda x: self.fold_text(x, width=45, max_width=99999)
                )
        return node_table

    def fold_text(self, txt, width, max_width):
        if width == "auto":
            w = 10
            while True:
                s = textwrap.wrap(txt, w)
                if (len(s) <= 2) or (w >= max_width):
                    break
                w += 1
            txt = "\n".join(s)
        elif width is not None:
            txt = "\n".join(textwrap.wrap(txt, width))
        return txt
