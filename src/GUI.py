from src import importer, logic, img_aqcuisition
from src.utils import resource_path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import io
import os
import pathlib
import requests
import threading
import numpy as np
import json


class CollectionViewer(tk.Tk):
    def __init__(self, dataframe):
        super().__init__()
        self._init_ui()
        self._init_data(dataframe)
        self._create_menu()
        self._create_widgets()
        self.show_dataframe(self.df)
        self.base_dir = pathlib.Path(__file__).resolve().parent

    def _init_ui(self):
        self.title("TCG Pocket Collection Tracker")
        self.geometry("1280x720")
        self.state("zoomed")

    def _init_data(self, dataframe):
        self.unique_packs = (
            dataframe["pack"].unique if "pack" in dataframe.columns else []
        )
        self.df = self._process_dataframe(dataframe)
        self.set = set()
        self.group_var = tk.StringVar(self)
        self.groups_all = {}
        self.groups_set = {}
        self.current_group = None
        self.inventory = set()
        self.checkbox_vars = {}
        self.set_completion_rarities = ["Common", "Uncommon", "Rare", "Rare EX"]
        self.json_path = resource_path("utils/a3-celestial-guardians.json")
        self.local_image_folder = "img"
        self.sets_folder = "sets"
        os.makedirs(self.local_image_folder, exist_ok=True)

    def _process_dataframe(self, df):
        if "pack" in df.columns:
            unique_packs = df["pack"].unique()
            df["pack"] = np.where(
                df["pack"].isna(),
                "Both" if len(unique_packs) != 1 else "Single",
                df["pack"],
            )

        return df

    def _create_menu(self):
        menubar = tk.Menu(self)
        self._create_file_menu(menubar)
        self._create_json_menu(menubar)
        self.config(menu=menubar)

    def _create_file_menu(self, menubar):
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Load Progress", command=self.load_progress)
        file_menu.add_command(label="Save Progress", command=self.save_progress)
        menubar.add_cascade(label="File", menu=file_menu)

    def _create_json_menu(self, menubar):
        json_menu = tk.Menu(menubar, tearoff=0)
        json_menu.add_command(label="Load Database", command=self.import_json)
        json_menu.add_command(
            label="Fetch Card Images", command=self._show_download_progress
        )
        menubar.add_cascade(label="Dataset", menu=json_menu)

    def import_json(self):
        file_paths = filedialog.askopenfilenames(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )

        if not file_paths:
            return

        try:
            dfs = [
                self._process_dataframe(
                    importer.clean_db(importer.read_json_file(path))
                )
                for path in file_paths
            ]
            self.df = pd.concat(dfs, ignore_index=True)
            self.group_var.set(self.df.columns[0])
            self.inventory = set()
            self.show_dataframe(self.df)
            self.json_path = (
                file_paths[0] if len(file_paths) == 1 else ";".join(file_paths)
            )
        except Exception as e:
            self.set_status_message(f"Failed to import database: {e}")

    def save_progress(self):
        file_path_str = filedialog.asksaveasfilename(
            defaultextension=".pif",
            filetypes=[("Pokemon Inventory Files", "*.pif"), ("All Files", "*.*")],
        )

        if not file_path_str:
            return

        file_path = pathlib.Path(file_path_str)

        try:
            if not getattr(self, "json_path", None):
                self.json_path = pathlib.Path(
                    resource_path("/sets/a3-celestial-guardians.json")
                )

            elif isinstance(self.json_path, str):
                self.json_path = pathlib.Path(self.json_path)

            with open(file_path, "w") as f:
                f.write(f"#json_path={self.json_path}\n")
                f.write("\n".join(map(str, self.inventory)) + "\n")

        except Exception as e:
            self.set_status_message(f"Failed to save inventory: {e}")

    def load_progress(self):
        file_path_str = filedialog.askopenfilename(
            defaultextension=".pif",
            filetypes=[("Pokemon Inventory Files", "*.pif"), ("All Files", "*.*")],
        )

        if not file_path_str:
            return

        file_path = pathlib.Path(file_path_str)

        try:
            json_path, indices = self._read_and_parse_progress_file(file_path)
            self._update_df_and_inventory(json_path, indices)

        except Exception as e:
            self.set_status_message(f"Failed to load inventory: {e}")

    def _read_and_parse_progress_file(self, file_path):
        json_path_str = None
        indices = set()

        try:
            with open(file_path, "r") as f:
                json_line = next(f, "").strip()

                if json_line.startswith("#json_path="):
                    json_path_str = json_line.split("=", 1)[1]

                for line in f:
                    line = line.strip()

                    if line:
                        try:
                            idx = int(line)
                            indices.add(idx)

                        except ValueError:
                            indices.add(line)

            json_path = pathlib.Path(json_path_str) if json_path_str else None

            return json_path, indices

        except Exception as e:
            self.set_status_message(f"Error en el archivo: {e}")

    def _update_df_and_inventory(self, json_path, indices):
        if json_path and getattr(self, "json_path", None) != json_path:
            try:
                df = importer.read_json_file(json_path)
                df = importer.clean_db(df)
                df = self._process_dataframe(df)

                self.df = df
                self.json_path = json_path

                if self.df.columns.any():
                    self.group_var.set(self.df.columns[0])
                    self.show_dataframe(self.df)

            except Exception as e:
                self.set_status_message(f"Failed to load referenced JSON: {e}")

        self.inventory = indices

        if self.groups and self.df.columns.any():
            self.on_group_change(self.group_var.get())

        elif not self.groups and self.df.columns.any():
            self.show_dataframe(self.df)

    def _create_widgets(self):
        style = ttk.Style(self)
        style.configure("Treeview", font=("Arial", 12))
        style.configure("Treeview.Heading", font=("Arial", 12))

        self._create_top_frame()
        self._create_bottom_frame()
        self._create_status_bar()

    def _create_top_frame(self):
        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        group_options = ["Checked"] + [
            col for col in self.df.columns if col not in ("id", "name")
        ]
        self.group_var.set("Checked")
        group_menu = ttk.Combobox(
            top_frame,
            textvariable=self.group_var,
            values=group_options,
            state="readonly",
        )
        group_menu.pack(side=tk.LEFT, padx=5)
        group_menu.bind(
            "<<ComboboxSelected>>", lambda e: self.on_group_change(self.group_var.get())
        )

        self.tab_control = ttk.Notebook(self)
        self.tab_control.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tab_all = tk.Frame(self.tab_control)
        self.tab_control.add(self.tab_all, text="All Inventory")

        self.tab_set = tk.Frame(self.tab_control)
        self.tab_control.add(self.tab_set, text="Set Completion Only")

        self.main_frames = {}
        for tab, is_set in [(self.tab_all, False), (self.tab_set, True)]:
            main_frame = tk.Frame(tab)
            main_frame.pack(fill=tk.BOTH, expand=True)
            self.main_frames[tab] = main_frame

            tree_frame = tk.Frame(main_frame)
            tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tree_frame.config(width=700)
            tree_frame.grid_propagate(False)
            tree_frame.grid_columnconfigure(0, weight=1)
            tree_frame.grid_rowconfigure(0, weight=1)

            columns = ["Inventory"] + list(self.df.columns)
            tree = ttk.Treeview(
                tree_frame, columns=columns, show="headings", selectmode="browse"
            )
            tree.heading("Inventory", text="✓")
            tree.column("Inventory", width=50, anchor="center", stretch=False)

            for col in self.df.columns:
                tree.heading(col, text=col.capitalize())
                longest_width = (
                    self.df[col].dropna().apply(len).max()
                    if not self.df[col].empty
                    else 10
                )
                tree.column(
                    col,
                    width=min(longest_width * 20, 150),
                    anchor="center",
                    stretch=False,
                )

            v_scrollbar = ttk.Scrollbar(
                tree_frame, orient="vertical", command=tree.yview
            )
            tree.configure(yscroll=v_scrollbar.set)

            h_scrollbar = ttk.Scrollbar(
                tree_frame, orient="horizontal", command=tree.xview
            )
            tree.configure(xscroll=h_scrollbar.set)

            tree.grid(row=0, column=0, sticky="nsew")
            v_scrollbar.grid(row=0, column=1, sticky="ns")
            h_scrollbar.grid(row=1, column=0, sticky="ew")

            tree.bind("<<TreeviewSelect>>", lambda event: self.on_item_select(event))
            tree.bind("<Button-1>", self.on_tree_click)

            if is_set:
                self.tree_set = tree
            else:
                self.tree = tree

            right_frame = tk.Frame(main_frame, width=500)
            right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
            right_frame.pack_propagate(False)

            right_notebook = ttk.Notebook(right_frame)
            right_notebook.pack(fill=tk.BOTH, expand=True)

            image_tab = tk.Frame(right_notebook, width=500, height=420)
            right_notebook.add(image_tab, text="Image Display")
            image_tab.pack_propagate(False)

            img_container = tk.Frame(image_tab, width=480, height=420)  # Tamaño fijo
            img_container.pack(pady=10)
            img_container.pack_propagate(False)

            img_label = tk.Label(
                img_container, text="Card image will appear here.", font=("Arial", 12)
            )
            img_label.pack(fill=tk.BOTH, expand=True)  # No expandir el Label

            if is_set:
                self.img_label_set = img_label
            else:
                self.img_label = img_label

            graph_tab = tk.Frame(right_notebook, width=500, height=420)
            right_notebook.add(graph_tab, text="Completion Chart")
            graph_tab.pack_propagate(False)

            chart_frame = tk.LabelFrame(
                graph_tab,
                text="Completion Chart",
                padx=10,
                pady=10,
                width=480,
                height=400,
            )
            chart_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            chart_frame.pack_propagate(False)

            if is_set:
                self.chart_frame_set = chart_frame
                self.chart_canvas_set = None
            else:
                self.chart_frame = chart_frame
                self.chart_canvas = None

    def _create_bottom_frame(self):
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=5, pady=5)

        ## Set Completion Frame

        set_frame = tk.Frame(bottom_frame)
        set_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        set_comp_frame = tk.LabelFrame(
            set_frame,
            text="Set Completion",
            padx=5,
            pady=5,
            bg="#e8f5e9",
            fg="#1b5e20",
            labelanchor="n",
        )
        set_comp_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=2, pady=2)
        self.set_comp_label = tk.Label(
            set_comp_frame,
            text="",
            bg="#e8f5e9",
            fg="#1b5e20",
            font=("Arial", 11, "bold"),
            anchor="w",
            justify="left",
        )
        self.set_comp_label.pack(anchor="w", padx=5, pady=2)

        set_pack_completion_frame = tk.LabelFrame(
            set_frame,
            text="Set Pack Completion",
            padx=5,
            pady=5,
            bg="#e8f5e9",
            fg="#1b5e20",
            labelanchor="n",
        )
        set_pack_completion_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2
        )
        self.set_pack_completion_frame = tk.Frame(
            set_pack_completion_frame, bg="#e8f5e9"
        )
        self.set_pack_completion_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        ## Inventory Completion Frame

        inv_frame = tk.Frame(bottom_frame)
        inv_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        inv_comp_frame = tk.LabelFrame(
            inv_frame,
            text="Set Completion",
            padx=5,
            pady=5,
            bg="#e3f2fd",
            fg="#1565c0",
            labelanchor="n",
        )
        inv_comp_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=2, pady=2)
        self.inv_comp_label = tk.Label(
            inv_comp_frame,
            text="",
            bg="#e3f2fd",
            fg="#1565c0",
            font=("Arial", 11, "bold"),
            anchor="w",
            justify="left",
        )
        self.inv_comp_label.pack(anchor="w", padx=5, pady=2)

        inv_pack_completion_frame = tk.LabelFrame(
            inv_frame,
            text="Set Pack Completion",
            padx=5,
            pady=5,
            bg="#e3f2fd",
            fg="#1565c0",
            labelanchor="n",
        )
        inv_pack_completion_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2
        )
        self.inv_pack_completion_frame = tk.Frame(
            inv_pack_completion_frame, bg="#e3f2fd"
        )
        self.inv_pack_completion_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        ## Suggestion Frame

        sug_frame = tk.Frame(bottom_frame)
        sug_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        sug_lbl_frame = tk.LabelFrame(
            sug_frame, text="What pack should you open?", padx=10, pady=10
        )
        sug_lbl_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        sug_label = tk.Label(
            sug_lbl_frame, text="", font=("Arial", 12, "bold"), fg="#1565c0"
        )
        sug_label.pack(fill=tk.BOTH, expand=True)

        self.suggest_label = sug_label
        self.suggest_label_set = sug_label

        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def _create_status_bar(self):
        self.status_var = tk.StringVar()
        self.status_bar = tk.Label(
            self,
            textvariable=self.status_var,
            bd=1,
            relief=tk.SUNKEN,
            anchor="w",
            font=("Arial", 10),
            bg="#f5f5f5",
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.set_status_message("Ready")

    def set_status_message(self, message, timeout=5000):
        self.status_var.set(message)
        if timeout:
            self.after(timeout, self.clear_status_message)

    def clear_status_message(self):
        self.status_var.set("")

    def show_dataframe(self, df):
        set_df = self._get_set_df(df)
        self.set = set(set_df.index)
        self._show_tree(self.tree, df, self.chart_frame, is_set=False)
        self._show_tree(self.tree_set, set_df, self.chart_frame_set, is_set=True)
        self.groups = None
        self.update_inventory_counter()
        self.show_group_bar_chart()
        self.show_group_bar_chart(is_set=True)
        self.update_pack_suggestion()
        self.update_pack_suggestion(is_set=True)

    def _show_tree(self, tree, df, chart_frame, is_set):
        tree.delete(*tree.get_children())

        if not hasattr(self, "checkbox_vars_all"):
            self.checkbox_vars_all = {}
            self.checkbox_vars_set = {}

        checkbox_vars = self.checkbox_vars_set if is_set else self.checkbox_vars_all
        checkbox_vars.clear()

        in_inventory = df.index.isin(self.inventory)

        checked_data = df[in_inventory]
        unchecked_data = df[~in_inventory]

        checked_group_id = tree.insert(
            "",
            tk.END,
            values=["", "Checked"] + [""] * (len(df.columns) - 1),
            tags=("checked_group",),
        )
        unchecked_group_id = tree.insert(
            "",
            tk.END,
            values=["", "Unchecked"] + [""] * (len(df.columns) - 1),
            tags=("unchecked_group",),
        )

        for idx, row in checked_data.iterrows():
            values = ["☑"] + row.tolist()
            item_id = tree.insert(
                checked_group_id, tk.END, values=values, tags=("item",)
            )
            checkbox_vars[item_id] = tk.IntVar(value=1)
            tree.set(item_id, "Inventory", "☑")

        for idx, row in unchecked_data.iterrows():
            values = ["☐"] + row.tolist()
            item_id = tree.insert(
                unchecked_group_id, tk.END, values=values, tags=("item",)
            )
            checkbox_vars[item_id] = tk.IntVar(value=0)
            tree.set(item_id, "Inventory", "☐")

    def on_tab_change(self, event):
        tab = self.tab_control.select()

        if tab == str(self.tab_all):
            self.show_group_bar_chart(is_set=False)
            self.update_pack_suggestion_for_current_tab()
        else:
            self.show_group_bar_chart(is_set=True)
            self.update_pack_suggestion_for_current_tab()

    def _populate_tree(
        self, tree, grouped_data, checkbox_vars, is_set, open_groups=True
    ):
        tree.delete(*tree.get_children())
        checkbox_vars.clear()

        groups = {}

        if hasattr(grouped_data, "groups"):
            for name, indices in grouped_data.groups.items():
                group = grouped_data.obj.loc[indices]
                groups[name] = group
                group_owned = sum(group.index.isin(self.inventory))
                group_total = len(group)
                group_display = f"{name} ({group_owned}/{group_total})"
                values = ["", group_display] + [""] * (len(self.df.columns) - 1)
                group_id = tree.insert(
                    "",
                    tk.END,
                    text=f"Group: {name}",
                    values=values,
                    open=open_groups,
                    tags=("group",),
                )
                groups[group_id] = group
        else:
            for name, group in grouped_data.items():
                groups[name] = group
                group_owned = sum(group.index.isin(self.inventory))
                group_total = len(group)
                group_display = f"{name} ({group_owned}/{group_total})"
                values = ["", group_display] + [""] * (len(self.df.columns) - 1)
                group_id = tree.insert(
                    "",
                    tk.END,
                    text=f"Group: {name}",
                    values=values,
                    open=open_groups,
                    tags=("group",),
                )
                groups[group_id] = group

        return groups

    def on_group_change(self, value):
        self.groups = self.groups_all = {}
        self.groups_set = {}
        self.checkbox_vars_all = {}
        self.checkbox_vars_set = {}

        if value == "Checked":
            in_inventory = self.df.index.isin(self.inventory)
            groups = {
                "Checked": self.df[in_inventory],
                "Unchecked": self.df[~in_inventory],
            }
            self.groups_all = self._populate_tree(
                self.tree, groups, self.checkbox_vars_all, is_set=False
            )

            set_df = self._get_set_df(self.df)
            in_inventory_set = set_df.index.isin(self.inventory)
            groups_set = {
                "Checked": set_df[in_inventory_set],
                "Unchecked": set_df[~in_inventory_set],
            }
            self.groups_set = self._populate_tree(
                self.tree_set, groups_set, self.checkbox_vars_set, is_set=True
            )
        else:
            grouped = self.df.groupby(value)
            self.groups_all = self._populate_tree(
                self.tree, grouped, self.checkbox_vars_all, is_set=False
            )

            set_df = self._get_set_df(self.df)
            grouped_set = set_df.groupby(value)
            self.groups_set = self._populate_tree(
                self.tree_set, grouped_set, self.checkbox_vars_set, is_set=True
            )

        self.groups = self.groups_all
        self.update_inventory_counter()
        self.show_group_bar_chart()
        self.show_group_bar_chart(is_set=True)
        self.update_pack_suggestion_for_current_tab()

    def on_item_select(self, event=None):
        widget = event.widget
        selected = widget.selection()

        if not selected:
            return

        item_id = selected[0]

        if widget == self.tree:
            groups = self.groups_all
        elif widget == self.tree_set:
            groups = self.groups_set
        else:
            return

        if groups and item_id in groups:
            self.handle_group_selection(item_id, widget, groups)
        else:
            self.handle_item_selection()

        idx = self.get_df_index_from_tree_item(item_id, widget)

        if idx is not None:
            self.display_card_image(idx, widget)

    def handle_group_selection(self, item_id, tree_widget, groups):
        group_df = groups[item_id]

        if not tree_widget.get_children(item_id):
            self.expand_group(item_id, group_df, tree_widget)
        else:
            self.collapse_group(item_id, tree_widget)

        self.current_group = group_df
        self.update_inventory_counter()

    def expand_group(self, item_id, group_df, tree_widget):
        for idx, row in group_df.iterrows():
            inv = 1 if idx in self.inventory else 0
            values = ["☑" if inv else "☐"] + [row[col] for col in self.df.columns]
            tree_widget.insert(item_id, tk.END, values=values, tags=("item",))

    def collapse_group(self, item_id, tree_widget):
        for child in tree_widget.get_children(item_id):
            tree_widget.delete(child)

    def handle_item_selection(self):
        self.current_group = None
        self.update_inventory_counter()

    def on_tree_click(self, event):
        widget = event.widget
        region = widget.identify("region", event.x, event.y)

        if region != "cell":
            return

        col = widget.identify_column(event.x)

        if col != "#1":
            return

        item_id = widget.identify_row(event.y)

        if not item_id or "item" not in widget.item(item_id, "tags"):
            return

        idx = self.get_df_index_from_tree_item(item_id, widget)

        if idx is None:
            return

        if idx in self.inventory:
            self.inventory.remove(idx)
            widget.set(item_id, "Inventory", "☐")
        else:
            self.inventory.add(idx)
            widget.set(item_id, "Inventory", "☑")

        if self.groups and widget == self.tree:
            parent_id = widget.parent(item_id)

            if parent_id in self.groups:
                group_df = self.groups[parent_id]
                group_owned = sum(i in self.inventory for i in group_df.index)
                group_total = len(group_df)
                group_col = self.group_var.get()
                group_name = group_df[group_col].iloc[0]
                group_display = f"{group_name} ({group_owned}/{group_total})"
                values = widget.item(parent_id, "values")
                new_values = list(values)
                new_values[1] = group_display
                widget.item(parent_id, values=new_values)

        self.update_inventory_counter()
        self.update_pack_suggestion_for_current_tab()

    def get_df_index_from_tree_item(self, item_id, tree_widget=None):
        if tree_widget is None:
            tree_widget = self.tree

        parent = tree_widget.parent(item_id)
        values = tree_widget.item(item_id, "values")[1:]

        if (
            parent
            and self.groups
            and parent in self.groups
            and tree_widget == self.tree
        ):
            group_df = self.groups[parent]
            condition = pd.Series(True, index=group_df.index)
            for i, col in enumerate(self.df.columns):
                condition &= group_df[col].astype(str) == str(values[i])
            matching_rows = group_df[condition]
        else:
            condition = pd.Series(True, index=self.df.index)
            for i, col in enumerate(self.df.columns):
                condition &= self.df[col].astype(str) == str(values[i])
            matching_rows = self.df[condition]

        if not matching_rows.empty:
            return matching_rows.index[0]
        return None

    def show_group_bar_chart(self, is_set=False):
        group_col = self.group_var.get()

        if group_col.lower() in ["id", "name"]:
            self.clear_chart(is_set)
            return

        df = self._get_set_df(self.df) if is_set else self.df

        if group_col not in df.columns:
            self.clear_chart(is_set)
            return

        owned_mask = df.index.isin(self.inventory)
        group_counts = df[group_col].value_counts().sort_index()
        owned_counts = (
            df[owned_mask][group_col]
            .value_counts()
            .reindex(group_counts.index, fill_value=0)
        )
        missing_counts = group_counts - owned_counts

        total_counts = group_counts
        owned_pct = owned_counts / total_counts * 100
        missing_pct = missing_counts / total_counts * 100

        fig, ax = plt.subplots(figsize=(4, 4))
        ax.barh(group_counts.index, owned_pct, label="Owned", color="#4caf50")
        ax.barh(
            group_counts.index,
            missing_pct,
            left=owned_pct,
            label="Missing",
            color="#e57373",
        )
        ax.set_xlabel("Percentage (%)")
        ax.set_ylabel(group_col.capitalize())
        ax.set_xlim(0, 100)
        ax.set_title(f"{group_col.capitalize()} - Owned vs Missing (%)")
        ax.legend(loc="lower right")
        plt.tight_layout()

        chart_frame = self.chart_frame_set if is_set else self.chart_frame
        chart_canvas = self.chart_canvas_set if is_set else self.chart_canvas

        if chart_canvas:
            chart_canvas.get_tk_widget().destroy()

        new_canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        new_canvas.draw()
        new_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        if is_set:
            self.chart_canvas_set = new_canvas
        else:
            self.chart_canvas = new_canvas

        plt.close(fig)

    def clear_chart(self, is_set=False):
        if is_set:
            if getattr(self, "chart_canvas_set", None):
                self.chart_canvas_set.get_tk_widget().destroy()
                self.chart_canvas_set = None
        else:
            if getattr(self, "chart_canvas", None):
                self.chart_canvas.get_tk_widget().destroy()
                self.chart_canvas = None

    def update_inventory_counter(self):
        self._update_set_completion()
        self._update_inventory_count()
        self._update_inventory_by_pack()
        self.update_pack_suggestion_for_current_tab()

    def _get_set_df(self, df):
        if "rarity" in df.columns:
            return df[df["rarity"].isin(self.set_completion_rarities)]
        return df

    def _update_set_completion(self):
        rarities = self.set_completion_rarities

        if "rarity" in self.df.columns:
            set_df = self.df[self.df["rarity"].isin(rarities)]
            set_total = len(set_df)
            set_owned = len(set_df[set_df.index.isin(self.inventory)])
            set_missing = set_total - set_owned
            self.set_comp_label.config(
                text=f"Minimum Set Completion: {set_owned} / {set_total} (missing: {set_missing})"
            )
            self._update_set_pack_completion(set_df)
        else:
            self.set_comp_label.config(text="No rarity data available.")
            self._clear_set_pack_completion("No rarity data available.", "#e8f5e9")

    def _update_set_pack_completion(self, set_df):
        for widget in self.set_pack_completion_frame.winfo_children():
            widget.destroy()

        if "pack" in self.df.columns:
            pack_counts = set_df["pack"].value_counts()
            owned_packs = set_df[set_df.index.isin(self.inventory)][
                "pack"
            ].value_counts()
            self.pack_completion_data = []

            for pack in pack_counts.index:
                owned = owned_packs.get(pack, 0)
                total_pack = pack_counts[pack]
                missing = total_pack - owned
                color = "#1c9625" if missing == 0 else "#b9c4ba"
                text = f"{pack}: {owned}/{total_pack} (missing: {missing})"
                lbl = tk.Label(
                    self.set_pack_completion_frame,
                    text=text,
                    bg=color,
                    font=("Arial", 10),
                    anchor="w",
                )
                lbl.pack(side=tk.TOP, anchor="w", fill=tk.X, padx=2, pady=1)
                self.pack_completion_data.append((pack, owned, total_pack, missing))

            self.update_pack_suggestion_for_current_tab()
        else:
            self._clear_set_pack_completion("No pack data available.", "#e8f5e9")
            self.pack_completion_data = []
            self.update_pack_suggestion_for_current_tab()

    def _clear_set_pack_completion(self, text, bg):
        for widget in self.set_pack_completion_frame.winfo_children():
            widget.destroy()

        lbl = tk.Label(self.set_pack_completion_frame, text=text, bg=bg)
        lbl.pack(side=tk.TOP, anchor="w", fill=tk.X, padx=2, pady=1)
        self.pack_completion_data = []
        self.update_pack_suggestion_for_current_tab()

    def _update_inventory_count(self):
        total = len(self.df)
        owned = len(self.inventory)
        missing = total - owned
        self.inv_comp_label.config(
            text=f"Inventory: {owned} / {total} (missing: {missing})"
        )

    def _update_inventory_by_pack(self):
        for widget in self.inv_pack_completion_frame.winfo_children():
            widget.destroy()

        if "pack" in self.df.columns:
            pack_counts = self.df["pack"].value_counts()
            owned_packs = self.df[self.df.index.isin(self.inventory)][
                "pack"
            ].value_counts()

            for pack in pack_counts.index:
                owned = owned_packs.get(pack, 0)
                total_pack = pack_counts[pack]
                missing = total_pack - owned
                color = "#0a78f4" if missing == 0 else "#b5c1ca"
                text = f"{pack}: {owned}/{total_pack} (missing: {missing})"
                lbl = tk.Label(
                    self.inv_pack_completion_frame,
                    text=text,
                    bg=color,
                    font=("Arial", 10),
                    anchor="w",
                )
                lbl.pack(side=tk.TOP, anchor="w", fill=tk.X, padx=2, pady=1)
        else:
            lbl = tk.Label(
                self.inv_pack_completion_frame,
                text="No pack data available.",
                bg="#e3f2fd",
            )
            lbl.pack(side=tk.TOP, anchor="w", fill=tk.X, padx=2, pady=1)

    def update_pack_suggestion_for_current_tab(self):
        current_tab = self.tab_control.select()
        is_set = current_tab == str(self.tab_set)
        self.update_pack_suggestion(is_set=is_set)

    def update_pack_suggestion(self, is_set=False):
        packs = self._get_incomplete_packs(is_set=is_set)

        if not packs:
            self._set_suggest_label("Congratulations! All packs are complete.", is_set)
            return

        if "pack" not in self.df.columns or "rarity" not in self.df.columns:
            self._set_suggest_label("Pack or rarity data missing.", is_set)
            return

        if is_set:
            df = self._get_set_df(self.df)
            relevant_indices = self.set
        else:
            df = self.df
            relevant_indices = set(self.df.index)

        missing_cards = df[
            (~df.index.isin(self.inventory)) & (df.index.isin(relevant_indices))
        ]
        missing_cards = missing_cards[
            missing_cards["rarity"].notna() & missing_cards["pack"].notna()
        ]
        rarity_to_row = self._get_rarity_to_row()
        pack_probs = self._calculate_pack_probabilities(
            packs, missing_cards, rarity_to_row
        )

        if not pack_probs:
            self._set_suggest_label("No probability data available.", is_set)
            return

        self._display_pack_suggestion(pack_probs, is_set)

    def _set_suggest_label(self, text, is_set):
        if is_set:
            self.suggest_label_set.config(text=text)
        else:
            self.suggest_label.config(text=text)

    def _get_incomplete_packs(self, is_set=False):
        if is_set:
            return [
                p
                for p in getattr(self, "pack_completion_data", [])
                if p[0] != "Both" and p[3] > 0
            ]
        else:
            if "pack" not in self.df.columns:
                return []

            pack_counts = self.df["pack"].value_counts()
            owned_packs = self.df[self.df.index.isin(self.inventory)][
                "pack"
            ].value_counts()
            incomplete = []

            for pack in pack_counts.index:
                owned = owned_packs.get(pack, 0)
                total = pack_counts[pack]
                missing = total - owned

                if pack != "Both" and missing > 0:
                    incomplete.append((pack, owned, total, missing))

        return incomplete

    def _get_rarity_to_row(self):
        rarity_order = list(self.df["rarity"].dropna().unique())
        return {r: i for i, r in enumerate(rarity_order)}

    def _calculate_pack_probabilities(self, packs, missing_cards, rarity_to_row):
        pack_probs = {}
        prob_matrix = logic.calc_prob(current_set=self.df["set"].unique()[0])
        prob_matrix = pd.DataFrame.from_dict(prob_matrix, orient="index")

        for pack_info in packs:
            pack_name = pack_info[0]
            cards_in_pack = missing_cards[
                (missing_cards["pack"] == pack_name) | (missing_cards["pack"] == "Both")
            ]

            if cards_in_pack.empty:
                pack_probs[pack_name] = 0.0

            rarities = cards_in_pack["rarity"]
            row_indices = np.array([rarity_to_row.get(r, -1) for r in rarities])
            valid_indices = (row_indices >= 0) & (row_indices < len(prob_matrix))
            row_indices = row_indices[valid_indices]

            if len(row_indices) > 0:
                row_p = 1 - prob_matrix.iloc[row_indices].values
                prob = np.concatenate(
                    (np.repeat(row_p[:, 0], 3).reshape(-1, 3), row_p[:, 1:]), axis=1
                )
                pack_probs[pack_name] = np.sum(1 - np.prod(prob, axis=1))

        return pack_probs

    def _display_pack_suggestion(self, pack_probs, is_set=False):
        max_prob = max(pack_probs.values())
        best_packs = [p for p, v in pack_probs.items() if abs(v - max_prob) < 1e-8]
        suggestion = ""

        if self.df[~self.df.index.isin(self.inventory)].empty:
            suggestion += "You have all cards in your collection.\n"

        if len(best_packs) == 1:
            max_prob = 1 if max_prob > 1 else max_prob
            if max_prob == 1:
                suggestion += f"Suggestion: Open '{best_packs[0]}' pack.\nIt's more likely to get a new card with it!"
            else:
                suggestion += f"Suggestion: Open '{best_packs[0]}' pack.\nIt has a probability of {max_prob * 100:.2f} % to have a new card.\n"
        else:
            suggestion += f"Any pack has the same chance to get you a new card!\n"

        self._set_suggest_label(suggestion.strip(), is_set)

    def _download_all_set_images_with_progress(self, progress_var, progress_label, top):
        no_cap_sets, all_sets = self._get_local_set_names(folder=self.sets_folder)
        total_cards = 0
        for set_name in no_cap_sets:
            json_path = os.path.join(self.sets_folder, f"{set_name}.json")
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    set_data = json.load(f)
                total_cards += len(set_data)
            except FileNotFoundError:
                print(f"Warning: JSON file not found for set '{set_name}'")
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in file for set '{set_name}'")

        downloaded_cards = 0

        for json_name, set_name in zip(no_cap_sets, all_sets):
            set_folder = os.path.join(self.local_image_folder, set_name)
            os.makedirs(set_folder, exist_ok=True)
            json_path = os.path.join(self.sets_folder, f"{json_name}.json")

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    set_data = json.load(f)
                set_df = pd.DataFrame(set_data)

                for index, row in set_df.iterrows():
                    card_name = row.get("name", "")
                    card_id = row.get("id", "")
                    card_id = (
                        card_id.split("-")[1].lstrip("0") if "-" in card_id else card_id
                    )
                    card_rarity = row.get("rarity", "")

                    filename = f"{card_name.replace(' ', '_')}_{card_id}_{card_rarity.replace(' ', '_')}.png"
                    local_path = os.path.join(set_folder, filename)

                    if not os.path.exists(local_path):
                        url = img_aqcuisition.get_image(
                            card_name=card_name,
                            card_id=card_id,
                            set_name=set_name,
                            card_rarity=card_rarity,
                        )
                        if url:
                            try:
                                response = requests.get(url, stream=True, timeout=10)
                                response.raise_for_status()
                                with open(local_path, "wb") as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        f.write(chunk)
                            except requests.exceptions.RequestException as e:
                                print(f"Error downloading {card_name} from {url}: {e}")
                        else:
                            print(f"URL not found for {card_name} in {set_name}")

                    downloaded_cards += 1
                    progress = (downloaded_cards / total_cards) * 100
                    progress_var.set(progress)
                    progress_label.config(text=f"Downloading... ({int(progress)}%)")
                    top.update()

            except FileNotFoundError:
                print(f"Warning: JSON file not found for set '{set_name}'")
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in file for set '{set_name}'")

        progress_label.config(text="Download Complete!")
        top.after(1000, top.destroy)

    def _get_local_set_names(self, folder):
        set_names = []
        set_cap = []
        for item in os.listdir(folder):
            if item.endswith(".json") and os.path.isfile(os.path.join(folder, item)):
                set_names.append(item[:-5])  # Remove ".json"
            elif os.path.isdir(os.path.join(folder, item)):
                set_names.append(item)  # If it's a directory

        for set_name in set_names:
            joined = []
            set_name_split = set_name.split("-")
            set_name_split = list(map(str.capitalize, set_name_split))
            set_code = set_name_split[0]
            set_id = set_name_split[1:]
            for id in set_id:
                if id == "Space":
                    joined.append("Space-Time")
                    set_id.remove("Time")
                else:
                    joined.append(id)

            set_cap.append(f"{'_'.join(joined)}_({set_code})")

        return set_names, set_cap

    def _load_local_image(self, card_name, card_id, set_name, card_rarity):
        set_folder = os.path.join(self.local_image_folder, set_name)
        filename = f"{card_name.replace(' ', '_')}_{card_id}_{card_rarity.replace(' ', '_')}.png"
        local_path = os.path.join(set_folder, filename)

        if os.path.exists(local_path):
            try:
                pil_image = Image.open(local_path)
                original_width, original_height = pil_image.size

                container_width, container_height = 480, 420
                width_scale = container_width / original_width
                height_scale = container_height / original_height
                scale = min(width_scale, height_scale)

                new_width = int(original_width * scale)
                new_height = int(original_height * scale)

                resized_image = pil_image.resize(
                    (new_width, new_height),
                    Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS,
                )
                photo_image = ImageTk.PhotoImage(resized_image)
                return pil_image, photo_image
            except Exception as e:
                print(f"Error loading local image {local_path}: {e}")
                return None, None
        return None, None

    def display_card_image(self, idx, widget):
        try:
            row = self.df.loc[idx]
        except Exception:
            return

        card_name = row.get("name", "")
        card_id = row.get("id", "")
        card_id = card_id.split("-")[1].lstrip("0") if "-" in card_id else card_id
        card_rarity = row.get("rarity", "")
        set_name = row.get("set", "").replace(" ", "_")
        label = self.img_label_set if widget == self.tree_set else self.img_label
        label.config(image="", text="Loading image...")
        label.image = None

        pil_image, photo = self._load_local_image(
            card_name, card_id, set_name, card_rarity
        )

        if pil_image:
            container_width, container_height = 480, 420
            original_width, original_height = pil_image.size
            width_scale = container_width / original_width
            height_scale = container_height / original_height
            scale = min(width_scale, height_scale)
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            resized_image = pil_image.resize(
                (new_width, new_height),
                Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS,
            )
            photo = ImageTk.PhotoImage(resized_image)

            if idx not in self.inventory:
                grayscale_image = pil_image.convert("L")
                grayscale_resized = grayscale_image.resize(
                    (new_width, new_height),
                    Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS,
                )
                grayscale_photo = ImageTk.PhotoImage(grayscale_resized)
                label.config(image=grayscale_photo, text="", compound="center")
                label.image = grayscale_photo
            else:
                label.config(image=photo, text="", compound="center")
                label.image = photo
        else:
            label.config(image="", text="Image not available locally")

    def _show_download_progress(self):
        top = tk.Toplevel(self)
        top.title("Downloading Images")
        progress_var = tk.DoubleVar()
        progressbar = ttk.Progressbar(top, variable=progress_var, maximum=100)
        progressbar.pack(pady=10, padx=20, fill=tk.X)
        progress_label = tk.Label(top, text="Downloading...")
        progress_label.pack(pady=5)

        self.download_thread = threading.Thread(
            target=self._download_all_set_images_with_progress,
            args=(progress_var, progress_label, top),
            daemon=True,
        )
        self.download_thread.start()
