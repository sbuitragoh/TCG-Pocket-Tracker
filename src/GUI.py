from src import importer, logic, img_aqcuisition
from src.utils import resource_path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import polars as pl
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
import re


def ensure_row_index(df: pl.DataFrame, name: str = "row_idx") -> pl.DataFrame:
    return df if name in df.columns else df.with_row_index(name=name)


def safe_str(value):
    if isinstance(value, pl.Series):
        return str(value.item()) if value.len() > 0 else ""
    return str(value) if value is not None else ""


class CollectionViewer(tk.Tk):
    def __init__(self, dataframe: pl.DataFrame):
        super().__init__()
        self._init_ui()
        self._init_data(dataframe)
        self._create_menu()
        self._create_widgets()
        self.show_dataframe(self.df)
        self.base_dir = pathlib.Path(__file__).resolve().parent

    def _init_ui(self):
        self.title("Test APK")
        self.geometry("1280x720")
        self.state("zoomed")

    def _init_data(self, dataframe: pl.DataFrame):
        self.unique_packs = (
            dataframe["pack"].unique().to_list() if "pack" in dataframe.columns else []
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
        self.pack_display_order = self.df.select("pack").unique().to_series().to_list()
        os.makedirs(self.local_image_folder, exist_ok=True)

    def _process_dataframe(self, df):
        if "pack" in df.columns:
            unique_pack = df["pack"].n_unique()
            fill_val = "Both" if unique_pack > 1 else "Single"
            df = df.with_columns(pl.col("pack").fill_null(fill_val))

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
                self._process_dataframe(importer.read_json_file(path))
                for path in file_paths
            ]
            self.df = pl.concat(dfs, how="vertical")
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
            self.set_status_message(f"Failed to save inventory")

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
                df = self._process_dataframe(df)

                self.df = df
                self.json_path = json_path

                if self.df.columns:
                    self.group_var.set(self.df.columns[0])
                    self.show_dataframe(self.df)

            except Exception as e:
                self.set_status_message(f"Failed to load referenced JSON: {e}")

        self.inventory = indices

        if self.groups and self.df.columns:
            self.on_group_change(self.group_var.get())

        elif not self.groups and self.df.columns:
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

        # Filtrar "id" y "name"
        group_options = ["Checked"] + [
            col for col in self.df.columns if col not in ("name")
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
                    self.df[col]
                    .drop_nans()
                    .map_elements(len, return_dtype=pl.Int64)
                    .max()
                    if not self.df.height > 0
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
            text="Inventory Completion",
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
            text="Inventory Pack Completion",
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

        self.suggest_label = tk.Label(
            sug_lbl_frame, text="", font=("Arial", 12, "bold"), fg="#1565c0"
        )
        self.suggest_label.pack(fill=tk.BOTH, expand=True)

        self.suggest_label_set = tk.Label(
            sug_lbl_frame, text="", font=("Arial", 12, "bold"), fg="#1565c0"
        )
        self.suggest_label_set.pack(fill=tk.BOTH, expand=True)

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
        set_df = ensure_row_index(set_df)
        self.set = set(set_df["row_idx"].to_list())
        self._show_tree(self.tree, df, self.chart_frame, is_set=False)
        self._show_tree(self.tree_set, set_df, self.chart_frame_set, is_set=True)
        self.groups = None
        self.update_inventory_counter()
        self.show_group_bar_chart()
        self.show_group_bar_chart(is_set=True)
        self.update_pack_suggestion()
        self.update_pack_suggestion(is_set=True)
        self._update_set_completion()

    def _show_tree(self, tree, df, chart_frame, is_set):
        tree.delete(*tree.get_children())

        # Initialize checkbox_vars dictionaries
        if not hasattr(self, "checkbox_vars_all"):
            self.checkbox_vars_all = {}
            self.checkbox_vars_set = {}

        checkbox_vars = self.checkbox_vars_set if is_set else self.checkbox_vars_all
        checkbox_vars.clear()

        df = ensure_row_index(df)
        in_inventory = df["row_idx"].is_in(list(self.inventory))

        # Efficiently create 'checked' and 'unchecked' data
        checked_data = df.filter(in_inventory)
        unchecked_data = df.filter(~in_inventory)

        # Insert group headings
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

        # Insert checked and unchecked items
        for row in checked_data.iter_rows(named=True):
            values = ["☑"] + [row[col] for col in df.columns if col != "row_idx"]
            item_id = tree.insert(
                checked_group_id, tk.END, values=values, tags=("item",)
            )
            checkbox_vars[item_id] = tk.IntVar(value=1)
            tree.set(item_id, "Inventory", "☑")

        for row in unchecked_data.iter_rows(named=True):
            values = ["☐"] + [row[col] for col in df.columns if col != "row_idx"]
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
        """
        Populates the given Treeview with data from the grouped DataFrame.

        Args:
            tree: The Treeview widget to populate.
            grouped_data: A DataFrameGroupBy object or a dictionary of DataFrames.
            checkbox_vars: Dictionary to store checkbox variables.
            is_set: Boolean indicating if it's for the set completion tree.
            open_groups: Boolean indicating whether to initially open the groups.
        """
        tree.delete(*tree.get_children())
        checkbox_vars.clear()

        groups = {}  # Store group IDs for later use

        # Handle both DataFrameGroupBy and a dictionary of DataFrames
        if hasattr(grouped_data, "groups"):  # It's a DataFrameGroupBy object
            for name, indices in grouped_data.groups.items():
                group = grouped_data.obj.loc[indices]
                groups[name] = group  # Store group DataFrame
                group_owned = sum(group.filter(pl.col("row_idx").is_in(self.inventory)))
                group_total = len(group)
                group_display = f"{name[0]} ({group_owned}/{group_total})"
                values = ["", group_display] + [""] * (len(self.df.columns) - 1)
                group_id = tree.insert(
                    "",
                    tk.END,
                    text=f"Group: {name}",
                    values=values,
                    open=open_groups,
                    tags=("group",),
                )
                groups[group_id] = group  # Store group_id: group mapping
        else:  # It's a dictionary of DataFrames
            for name, group in grouped_data:
                group = ensure_row_index(group)
                groups[name] = group  # Store group DataFrame
                group_owned = group.filter(pl.col("row_idx").is_in(self.inventory))
                group_total = len(group)
                group_display = f"{name[0]} ({group_owned.height}/{group_total})"
                values = ["", group_display] + [""] * (len(self.df.columns) - 1)
                group_id = tree.insert(
                    "",
                    tk.END,
                    text=f"Group: {name}",
                    values=values,
                    open=open_groups,
                    tags=("group",),
                )
                groups[group_id] = group  # Store group_id: group mapping

        return groups  # Return the groups dictionary

    def on_group_change(self, value):
        # Common operations
        self.groups = self.groups_all = {}  # Initialize/Clear groups
        self.groups_set = {}
        self.checkbox_vars_all = {}
        self.checkbox_vars_set = {}
        df = ensure_row_index(self.df)

        if value == "Checked":
            # Group by checked/unchecked
            groups = {
                "Checked": df.filter(pl.col("row_idx").is_in(list(self.inventory))),
                "Unchecked": df.filter(~pl.col("row_idx").is_in(list(self.inventory))),
            }
            self.groups_all = self._populate_tree(
                self.tree, groups, self.checkbox_vars_all, is_set=False
            )

            set_df = self._get_set_df(df)
            groups_set = {
                "Checked": set_df.filter(pl.col("row_idx").is_in(list(self.inventory))),
                "Unchecked": set_df.filter(
                    ~pl.col("row_idx").is_in(list(self.inventory))
                ),
            }
            self.groups_set = self._populate_tree(
                self.tree_set, groups_set, self.checkbox_vars_set, is_set=True
            )
        else:
            # Group by selected column
            grouped = df.group_by(value)
            self.groups_all = self._populate_tree(
                self.tree, grouped, self.checkbox_vars_all, is_set=False
            )

            set_df = self._get_set_df(df)
            grouped_set = set_df.group_by(value)
            self.groups_set = self._populate_tree(
                self.tree_set, grouped_set, self.checkbox_vars_set, is_set=True
            )

        self.groups = self.groups_all  # Set self.groups after populating
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
        for row in group_df.iter_rows(named=True):
            idx = row["row_idx"]
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
                group_owned = sum(i in self.inventory for i in group_df["row_idx"])
                group_total = len(group_df)
                group_col = self.group_var.get()
                group_name = group_df[group_col][0]
                group_display = f"{group_name} ({group_owned}/{group_total})"
                values = widget.item(parent_id, "values")
                new_values = list(values)
                new_values[1] = group_display
                widget.item(parent_id, values=new_values)

        self._update_set_completion()
        self.update_inventory_counter()
        self.show_group_bar_chart()
        self.show_group_bar_chart(is_set=True)
        self.update_pack_suggestion_for_current_tab()

    def get_df_index_from_tree_item(self, item_id, tree_widget=None):
        if tree_widget is None:
            tree_widget = self.tree

        try:
            item_values = tree_widget.item(item_id, "values")
            selected_id = item_values[self.df.columns.index("id") + 1]

            df = ensure_row_index(self.df)
            df_match = df.filter(pl.col("id").cast(str) == str(selected_id))
            if df_match.height > 0:
                return df_match[0, "row_idx"]
        except Exception as e:
            self.set_status_message(e)

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

        df = ensure_row_index(df).fill_null("None")
        owned_mask = df.filter(pl.col("row_idx").is_in(list(self.inventory)))
        group_counts = df.group_by(group_col).len().rename({"len": "total"})
        owned_counts = owned_mask.group_by(group_col).len().rename({"len": "owned"})
        filled_join = group_counts.join(
            owned_counts, on=group_col, how="left"
        ).with_columns((pl.col("owned").fill_null(0)))
        missing_join = filled_join.with_columns(
            (pl.col("total") - pl.col("owned")).alias("missing")
        )
        joined = missing_join.with_columns(
            [
                (pl.col("owned") / pl.col("total") * 100).alias("owned_pct"),
                (pl.col("missing") / pl.col("total") * 100).alias("missing_pct"),
            ]
        )

        labels = (
            joined[group_col].to_list()
            if group_col != "set"
            else re.findall(r"\((.*?)\)", joined[group_col].to_list()[0])
        )
        owned_pct = joined["owned_pct"].to_list()
        missing_pct = joined["missing_pct"].to_list()

        ring_data = list(map(list, zip(owned_pct, missing_pct)))
        colors = ["#4caf50", "#e57373"]
        center_radius = 0.5
        step_radius = (1 - center_radius) / len(labels)

        fig, ax = plt.subplots(figsize=(5, 5))
        for i, v in enumerate(labels):
            data = ring_data[i]
            draw_radius = 1 - (i * step_radius)
            ax.pie(
                data,
                radius=draw_radius,
                labels=[v, ""],
                autopct="%.2f%%",
                pctdistance=0.65,
                colors=colors,
                wedgeprops=dict(width=center_radius, edgecolor="w"),
            )
        plt.tight_layout()

        # Replace the chart in the GUI with fixed size
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
        # self._update_set_completion()
        self._update_inventory_count()
        self._update_inventory_by_pack()
        self.update_pack_suggestion_for_current_tab()

    def _get_set_df(self, df: pl.DataFrame) -> pl.DataFrame:
        df = ensure_row_index(df)
        if "rarity" in df.columns:
            return df.filter(pl.col("rarity").is_in(self.set_completion_rarities))
        return df

    def _update_set_completion(self):
        if "rarity" in self.df.columns:
            set_df = self._get_set_df(self.df)
            owned_set = ensure_row_index(set_df).filter(
                pl.col("row_idx").is_in(list(self.inventory))
            )
            set_total = set_df.height
            set_owned = owned_set.height
            set_missing = set_total - set_owned
            self.set_comp_label.config(
                text=f"Minimum Set Completion: {set_owned} / {set_total} (missing: {set_missing})"
            )
            self._update_set_pack_completion(set_df)
        else:
            self.set_comp_label.config(text="No rarity data available.")
            self._clear_set_pack_completion("No rarity data available.", "#e8f5e9")

    def update_completion(self, df_c: pl.DataFrame, color_c: str):
        df = ensure_row_index(df_c)

        total_counts = df.group_by("pack").len().rename({"len": "total"})
        owned_df = df.filter(pl.col("row_idx").is_in(list(self.inventory)))
        owned_counts = owned_df.group_by("pack").len().rename({"len": "owned"})

        joined = (
            total_counts.join(owned_counts, on="pack", how="left")
            .with_columns(
                [
                    pl.col("owned").fill_null(0),
                    (pl.col("total") - pl.col("owned")).alias("missing"),
                ]
            )
            .sort("pack")
        )

        pack_order = {pack: i for i, pack in enumerate(self.pack_display_order)}
        joined_rows = sorted(
            joined.iter_rows(named=True),
            key=lambda row: pack_order.get(row["pack"], 9999),
        )

        for row in joined_rows:
            color = color_c if row["missing"] == 0 else "#b9c4ba"
            text = f"{row['pack']}: {row['owned']}/{row['total']} \
            (missing: {row['missing'] if row['missing'] != None else row['total']})"
            if color_c == "#1c9625":
                lbl = tk.Label(
                    self.set_pack_completion_frame,
                    text=text,
                    bg=color,
                    font=("Arial", 10),
                    anchor="w",
                )
            else:
                lbl = tk.Label(
                    self.inv_pack_completion_frame,
                    text=text,
                    bg=color,
                    font=("Arial", 10),
                    anchor="w",
                )
            lbl.pack(side=tk.TOP, anchor="w", fill=tk.X, padx=2, pady=1)

    def _update_set_pack_completion(self, set_df: pl.DataFrame):
        for widget in self.set_pack_completion_frame.winfo_children():
            widget.destroy()

        if "pack" not in set_df.columns:
            lbl = tk.Label(
                self.set_pack_completion_frame,
                text="No pack data available",
                bg="#e3f2fd",
            )
            lbl.pack(side=tk.TOP, anchor="w", fill=tk.X, padx=2, pady=1)
            return

        self.update_completion(df_c=set_df, color_c="#1c9625")

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

        if "pack" not in self.df.columns:
            lbl = tk.Label(
                self.inv_pack_completion_frame,
                text="No pack data available.",
                bg="#e3f2fd",
            )
            lbl.pack(side=tk.TOP, anchor="w", fill=tk.X, padx=2, pady=1)
            return

        self.update_completion(df_c=self.df, color_c="#2b2ee9")

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

        df = self._get_set_df(self.df) if is_set else self.df
        df = ensure_row_index(df)
        relevant_indices = self.set if is_set else set(df["row_idx"].to_list())

        missing_cards = df.filter(
            (~pl.col("row_idx").is_in(self.inventory))
            & (pl.col("row_idx").is_in(list(relevant_indices)))
            & pl.col("rarity").is_not_null()
            & pl.col("pack").is_not_null()
        )

        pack_probs = self._calculate_pack_probabilities(packs, missing_cards)

        if not pack_probs:
            self._set_suggest_label("No probability data available.", is_set)
            return

        self._display_pack_suggestion(pack_probs, is_set)

    def _set_suggest_label(self, text, is_set):
        if is_set:
            self.suggest_label_set.config(text=text)
            self.suggest_label.config(text="")  # hide the other
        else:
            self.suggest_label.config(text=text)
            self.suggest_label_set.config(text="")

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
            owned_packs = (
                ensure_row_index(self.df)
                .filter(pl.col("row_idx").is_in(self.inventory))["pack"]
                .value_counts()
            )

            incomplete_df = (
                pack_counts.join(owned_packs, on="pack", how="left", suffix="_owned")
                .with_columns(
                    [
                        pl.col("count_owned").fill_null(0).alias("owned"),
                        pl.col("count").alias("total"),
                    ]
                )
                .with_columns([(pl.col("total") - pl.col("owned")).alias("missing")])
                .filter((pl.col("pack") != "Both") & (pl.col("missing") > 0))
                .select(["pack", "owned", "total", "missing"])
            )

            incomplete = incomplete_df.rows()

        return incomplete

    def _calculate_pack_probabilities(self, packs, missing_cards):
        pack_probs = {}
        prob_matrix = logic.calc_prob(current_set=self.df["set"].unique()[0])

        for pack_info in packs:
            pack_name = pack_info[0]
            filtered = missing_cards.filter(
                (pl.col("pack") == pack_name) | (pl.col("pack") == "Both")
            )

            if filtered.height == 0:
                pack_probs[pack_name] = 0.0
            else:
                prob_seted = filtered.with_columns(
                    (pl.col("rarity").replace_strict(prob_matrix)).alias("rar_prob")
                )
                prob_separated = prob_seted.with_columns(
                    pl.col("rar_prob").list.to_struct(fields=["P_123", "P_4", "P_5"])
                ).unnest("rar_prob")
                p_prev = prob_separated.with_columns(
                    [
                        (1 - pl.col("P_123")).alias("nP_123"),
                        (1 - pl.col("P_4")).alias("nP_4"),
                        (1 - pl.col("P_5")).alias("nP_5"),
                    ]
                )
                prob_calc = p_prev.with_columns(
                    [
                        (pl.col("nP_123") ** 3 * pl.col("nP_4") * pl.col("nP_5"))
                        .cast(pl.Decimal(precision=20, scale=15))
                        .alias("P")
                    ]
                )
                pp = prob_calc.with_columns((1 - pl.col("P")).alias("1-P"))
                final_prob = pp.select(pl.sum("1-P"))
                pack_probs[pack_name] = float(final_prob.__array__().item())

        return pack_probs

    def _display_pack_suggestion(self, pack_probs, is_set=False):
        max_prob = max(pack_probs.values())
        best_packs = [p for p, v in pack_probs.items() if abs(v - max_prob) < 1e-8]
        suggestion = ""

        df = ensure_row_index(self.df)
        missing_df = df.filter(~pl.col("row_idx").is_in(list(self.inventory)))
        if missing_df.is_empty():
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
        """Downloads all card images from JSON files in the 'sets' folder and updates the progress bar."""

        no_cap_sets, all_sets = self._get_local_set_names(
            folder=self.sets_folder
        )  # Get sets from 'sets' folder
        total_cards = 0
        for set_name in no_cap_sets:
            json_path = os.path.join(self.sets_folder, f"{set_name}.json")
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    set_data = json.load(f)
                total_cards += len(set_data)  # Assuming set_data is a list of cards
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
                set_df = pl.DataFrame(set_data)  # Create DataFrame from JSON data

                for index, row in set_df.iter_rows(named=True):
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
        """Gets a list of set names from the specified folder (e.g., 'sets' or 'img')."""
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
        """Loads an image from the local folder if it exists and returns both PIL Image and PhotoImage."""

        set_folder = os.path.join(self.local_image_folder, set_name)
        filename = f"{card_name.replace(' ', '_')}_{card_id}_{card_rarity.replace(' ', '_')}.png"
        local_path = os.path.join(set_folder, filename)

        if os.path.exists(local_path):
            try:
                pil_image = Image.open(local_path)
                original_width, original_height = pil_image.size

                # Calculate scaling factors
                container_width, container_height = 480, 420
                width_scale = container_width / original_width
                height_scale = container_height / original_height
                scale = min(width_scale, height_scale)  # Use the smaller scale

                # Calculate new dimensions
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
        # Ensure DataFrame has row_idx
        df = ensure_row_index(self.df)

        # Get the row by index
        match = df.filter(pl.col("row_idx") == idx)
        if match.is_empty():
            return

        row = match[0]
        # Extract values
        card_name = safe_str(row["name"])
        card_id = safe_str(row["id"])
        card_rarity = safe_str(row["rarity"])
        set_name = safe_str(row["set"]).replace(" ", "_")

        if "-" in card_id:
            card_id = card_id.split("-")[1].lstrip("0")

        # Get the correct label depending on which tree was clicked
        label = self.img_label_set if widget == self.tree_set else self.img_label

        label.config(image="", text="Loading image...")
        label.image = None  # Remove reference to any previous image

        pil_image, photo = self._load_local_image(
            card_name, card_id, set_name, card_rarity
        )

        if pil_image:
            # Resize to fit container
            container_width, container_height = 480, 420
            original_width, original_height = pil_image.size
            scale = min(
                container_width / original_width, container_height / original_height
            )
            new_size = (int(original_width * scale), int(original_height * scale))
            resized_image = pil_image.resize(new_size, Image.LANCZOS)

            if idx not in self.inventory:
                # Grayscale version for unowned
                grayscale_image = pil_image.convert("L").resize(new_size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(grayscale_image)
            else:
                photo = ImageTk.PhotoImage(resized_image)

            label.config(image=photo, text="", compound="center")
            label.image = photo  # ✅ Retain reference to prevent garbage collection
        else:
            label.config(image="", text="Image not available locally")

    def _show_download_progress(self):
        """Shows a message box with a progress bar during image download."""
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
