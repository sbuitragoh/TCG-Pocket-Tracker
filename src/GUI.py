from src import importer
from src import logic
from src import img_aqcuisition
from src.utils import resource_path
import io
import requests
import threading
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk

class DataFrameViewer(tk.Tk):
    
    def __init__(self, dataframe):
        super().__init__()
        self.title("TCG Pocket Tracker")
        self.state('zoomed')
        
        if 'pack' in dataframe.columns:
            dataframe['pack'] = dataframe['pack'].where(dataframe['pack'].notna(), 'Both')

        self.df = dataframe
        self.set = set()  
        self.group_var = tk.StringVar(self)
        self.group_var.set(self.df.columns[0])
        self.groups = None
        self.current_group = None
        self.inventory = set()  
        self.checkbox_vars = {}  
        self.set_completion_rarities = ["Common", "Uncommon", "Rare", "Rare EX"]
        self.json_path = resource_path('sets/a3-celestial-guardians.json')
        self.create_menu()
        self.create_widgets()
        self.show_dataframe(self.df)

        self.groups_all = {} 
        self.groups_set = {} 

    def create_menu(self):

        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Import JSON", command=self.import_json)
        filemenu.add_command(label="Save Progress", command=self.save_progress)
        filemenu.add_command(label="Load Progress", command=self.load_progress)
        menubar.add_cascade(label="File", menu=filemenu)
        self.config(menu=menubar)

    def import_json(self):
        file_paths = filedialog.askopenfilenames(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if file_paths:
            dfs = []
            for path in file_paths:
                try:
                    df = importer.read_json_file(path)
                    df = importer.clean_db(df)
                    dfs.append(df)
                except Exception as e:
                    self.set_status_message(f"Failed to import {path}: {e}")
            if dfs:
                self.df = pd.concat(dfs, ignore_index=True)
                if 'pack' in self.df.columns:
                    self.df['pack'] = self.df['pack'].where(self.df['pack'].notna(), 'Both')
                self.group_var.set(self.df.columns[0])
                self.inventory = set()
                self.show_dataframe(self.df)
                # Store the path of the first JSON loaded (or all, if you want)
                self.json_path = file_paths[0] if len(file_paths) == 1 else ";".join(file_paths)

    def save_progress(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pif",
            filetypes=[("Pokemon Inventory Files", "*.pif"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                # Ensure self.json_path is set
                if not getattr(self, "json_path", ""):
                    self.json_path = resource_path('sets/a3-celestial-guardians.json')
                with open(file_path, "w") as f:
                    # Save the current JSON path as the first line
                    f.write(f"#json_path={self.json_path}\n")
                    for idx in self.inventory:
                        f.write(str(idx) + "\n")
            except Exception as e:
                self.set_status_message(f"Failed to save progress: {e}")

    def load_progress(self):
        file_path = filedialog.askopenfilename(defaultextension=".pif", filetypes=[("Pokemon Inventory Files", "*.pif"), ("All Files", "*.*")])
        if not file_path:
            return
        try:
            lines = self._read_progress_file(file_path)
            json_path, indices = self._parse_progress_lines(lines)
            self._update_df_and_inventory(json_path, indices)
        except Exception as e:
            self.set_status_message(f"Failed to load progress: {e}")

    def _read_progress_file(self, file_path):
        with open(file_path, "r") as f:
            return f.readlines()

    def _parse_progress_lines(self, lines):
        json_path = ""
        if lines and lines[0].startswith("#json_path="):
            json_path = lines[0].strip().split("=", 1)[1]
            lines = lines[1:]
        indices = set()
        for line in lines:
            line = line.strip()
            if line:
                try:
                    idx = int(line)
                except ValueError:
                    idx = line
                indices.add(idx)
        return json_path, indices

    def _update_df_and_inventory(self, json_path, indices):
        # If JSON path is present and different, reload it
        if json_path and getattr(self, "json_path", "") != json_path:
            try:
                df = importer.read_json_file(json_path)
                df = importer.clean_db(df)
                # --- Fix: Normalize 'pack' column here ---
                if 'pack' in df.columns:
                    df['pack'] = df['pack'].where(df['pack'].notna(), 'Both')
                self.df = df
                self.json_path = json_path
                self.group_var.set(self.df.columns[0])
                self.show_dataframe(self.df)
            except Exception as e:
                self.set_status_message(f"Failed to load referenced JSON: {e}")
        self.inventory = indices
        if self.groups:
            self.on_group_change(self.group_var.get())
        else:
            self.show_dataframe(self.df)

    def create_widgets(self):
        
        style = ttk.Style(self)
        style.configure("Treeview", font = ("Arial", 12))
        style.configure("Treeview.Heading", font = ("Arial", 12))

        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        group_options = ["Checked"] + list(self.df.columns)
        self.group_var.set('Checked')
        group_menu = ttk.Combobox(top_frame, textvariable=self.group_var, values=group_options, state="readonly")
        group_menu.pack(side=tk.LEFT, padx=5)
        group_menu.bind("<<ComboboxSelected>>", lambda e: self.on_group_change(self.group_var.get()))
        
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

            
            columns = ["Inventory"] + list(self.df.columns)
            tree = ttk.Treeview(main_frame, columns=columns, show="headings", selectmode="browse")
            tree.heading("Inventory", text="✓")
            tree.column("Inventory", width=60, anchor="center")
            for col in self.df.columns:
                tree.heading(col, text=col)
                tree.column(col, width=120, anchor="center")
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tree.bind("<<TreeviewSelect>>", self.on_item_select)
            tree.bind("<Button-1>", self.on_tree_click)
            if is_set:
                self.tree_set = tree
            else:
                self.tree = tree

            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            tree.configure(yscroll=scrollbar.set)
            scrollbar.pack(side=tk.LEFT, fill=tk.Y)

            right_frame = tk.Frame(main_frame)
            right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

            # --- NEW: Add notebook for right frame ---
            right_notebook = ttk.Notebook(right_frame)
            right_notebook.pack(fill=tk.BOTH, expand=True)

            # Tab 1: Image Display
            image_tab = tk.Frame(right_notebook)
            right_notebook.add(image_tab, text="Image Display")
            # Placeholder for image display widget
            img_label = tk.Label(image_tab, text="Card image will appear here.", font=("Arial", 12))
            img_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            if is_set:
                self.img_label_set = img_label
            else:
                self.img_label = img_label

            # Tab 2: Chart/Graph
            graph_tab = tk.Frame(right_notebook)
            right_notebook.add(graph_tab, text="Completion Chart")
            pie_frame = tk.LabelFrame(graph_tab, text="Completion Chart", padx=10, pady=10)
            pie_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            if is_set:
                self.pie_frame_set = pie_frame
                self.pie_canvas_set = None
            else:
                self.pie_frame = pie_frame
                self.pie_canvas = None

        # Create a 3-column layout for the bottom section: Left (Set Completion), Middle (Inventory), Right (Suggestion)
        bottom_main_frame = tk.Frame(self)
        bottom_main_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Left: Set Completion
        set_frame = tk.Frame(bottom_main_frame)
        set_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        set_completion_frame = tk.LabelFrame(set_frame, text="Set Completion", padx=10, pady=10, bg="#e8f5e9", fg="#1b5e20", labelanchor="n")
        set_completion_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=2, pady=2)
        self.set_completion_label = tk.Label(set_completion_frame, text="", bg="#e8f5e9", fg="#1b5e20", font=("Arial", 11, "bold"), anchor="w", justify="left")
        self.set_completion_label.pack(anchor="w", padx=5, pady=2)

        set_pack_completion_frame = tk.LabelFrame(set_frame, text="Set Pack Completion", padx=10, pady=10, bg="#e8f5e9", fg="#1b5e20", labelanchor="n")
        set_pack_completion_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.set_pack_completion_frame = tk.Frame(set_pack_completion_frame, bg="#e8f5e9")
        self.set_pack_completion_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        # Middle: Inventory
        inventory_frame = tk.Frame(bottom_main_frame)
        inventory_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 5))

        inventory_main_frame = tk.LabelFrame(inventory_frame, text="Inventory", padx=10, pady=10, bg="#e3f2fd", fg="#1565c0", labelanchor="n")
        inventory_main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=2, pady=2)

        self.general_inventory_label = tk.Label(inventory_main_frame, text="", bg="#e3f2fd", fg="#1565c0", font=("Arial", 11, "bold"))
        self.general_inventory_label.pack(anchor="w", padx=5, pady=2)

        inventory_packs_frame = tk.LabelFrame(inventory_frame, text="Inventory Packs", padx=10, pady=10, bg="#e3f2fd", fg="#1565c0", labelanchor="n")
        inventory_packs_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.pack_inventory_frame = tk.Frame(inventory_packs_frame, bg="#e3f2fd")
        self.pack_inventory_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        # Right: Suggestion
        suggestion_frame = tk.Frame(bottom_main_frame)
        suggestion_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        suggestion_main_frame = tk.LabelFrame(suggestion_frame, text="Which pack should you open?", padx=10, pady=10)
        suggestion_main_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        suggestion_label = tk.Label(suggestion_main_frame, text="", font=("Arial", 12, "bold"), fg="#1565c0")
        suggestion_label.pack(fill=tk.BOTH, expand=True)
        self.suggestion_label = suggestion_label
        self.suggestion_label_set = suggestion_label  # For compatibility with set tab


        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.status_var = tk.StringVar()
        self.status_bar = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor="w", font=("Arial", 10), bg="#f5f5f5")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def show_dataframe(self, df):
        
        set_df = self._get_set_df(df)
        self.set = set(set_df.index)
        self._show_tree(self.tree, df, self.pie_frame, is_set=False)
        self._show_tree(self.tree_set, set_df, self.pie_frame_set, is_set=True)
        self.groups = None
        self.update_inventory_counter()
        self.show_group_bar_chart()
        self.show_group_bar_chart(is_set=True)
        self.update_pack_suggestion()
        self.update_pack_suggestion(is_set=True)

    def _show_tree(self, tree, df, pie_frame, is_set):

        tree.delete(*tree.get_children())
        if not hasattr(self, 'checkbox_vars_all'):
            self.checkbox_vars_all = {}
            self.checkbox_vars_set = {}
        checkbox_vars = self.checkbox_vars_set if is_set else self.checkbox_vars_all
        checkbox_vars.clear()
        checked = []
        unchecked = []
        for idx, row in df.iterrows():
            inv = 1 if idx in self.inventory else 0
            if inv:
                checked.append((idx, row))
            else:
                unchecked.append((idx, row))
        checked_group_id = tree.insert("", tk.END, values=["", "Checked"] + [""] * (len(self.df.columns) - 1), tags=("checked_group",))
        for idx, row in checked:
            values = [u"☑"] + [row[col] for col in self.df.columns]
            item_id = tree.insert(checked_group_id, tk.END, values=values, tags=("item",))
            checkbox_vars[item_id] = tk.IntVar(value=1)
            tree.set(item_id, "Inventory", u"☑")
        unchecked_group_id = tree.insert("", tk.END, values=["", "Unchecked"] + [""] * (len(self.df.columns) - 1), tags=("unchecked_group",))
        for idx, row in unchecked:
            values = [u"☐"] + [row[col] for col in self.df.columns]
            item_id = tree.insert(unchecked_group_id, tk.END, values=values, tags=("item",))
            checkbox_vars[item_id] = tk.IntVar(value=0)
            tree.set(item_id, "Inventory", u"☐")

    def on_tab_change(self, event):

        tab = self.tab_control.select()
        if tab == str(self.tab_all):
            self.show_group_bar_chart(is_set=False)
            self.update_pack_suggestion_for_current_tab()
        else:
            self.show_group_bar_chart(is_set=True)
            self.update_pack_suggestion_for_current_tab()

    def on_group_change(self, value):
        if value == "Checked":
            # Group by checked/unchecked
            checked = self.df[self.df.index.isin(self.inventory)]
            unchecked = self.df[~self.df.index.isin(self.inventory)]
            groups = {"Checked": checked, "Unchecked": unchecked}

            self.tree.delete(*self.tree.get_children())
            self.checkbox_vars_all = {}
            self.groups_all = {}
            for name, group in groups.items():
                group_owned = len(group)
                group_total = len(group)
                group_display = f"{name} ({group_owned}/{group_total})"
                values = ["", group_display] + [""] * (len(self.df.columns) - 1)
                group_id = self.tree.insert("", tk.END, text=f"Group: {name}", values=values, open=False, tags=("group",))
                self.groups_all[group_id] = group
            self.groups = self.groups_all  # <-- Set self.groups!

            set_df = self._get_set_df(self.df)
            checked_set = set_df[set_df.index.isin(self.inventory)]
            unchecked_set = set_df[~set_df.index.isin(self.inventory)]
            groups_set = {"Checked": checked_set, "Unchecked": unchecked_set}

            self.tree_set.delete(*self.tree_set.get_children())
            self.checkbox_vars_set = {}
            self.groups_set = {}
            for name, group in groups_set.items():
                group_owned = len(group)
                group_total = len(group)
                group_display = f"{name} ({group_owned}/{group_total})"
                values = ["", group_display] + [""] * (len(self.df.columns) - 1)
                group_id = self.tree_set.insert("", tk.END, text=f"Group: {name}", values=values, open=False, tags=("group",))
                self.groups_set[group_id] = group

            self.update_inventory_counter()
            self.show_group_bar_chart()
            self.show_group_bar_chart(is_set=True)
            self.update_pack_suggestion_for_current_tab()
        else:
            # Group by selected column
            grouped = self.df.groupby(value)
            self.tree.delete(*self.tree.get_children())
            self.checkbox_vars_all = {}
            self.groups_all = {}
            for name, group in grouped:
                group_owned = sum(idx in self.inventory for idx in group.index)
                group_total = len(group)
                group_display = f"{name} ({group_owned}/{group_total})"
                values = ["", group_display] + [""] * (len(self.df.columns) - 1)
                group_id = self.tree.insert("", tk.END, text=f"Group: {name}", values=values, open=False, tags=("group",))
                self.groups_all[group_id] = group
            self.groups = self.groups_all

            set_df = self._get_set_df(self.df)
            grouped_set = set_df.groupby(value)
            self.tree_set.delete(*self.tree_set.get_children())
            self.checkbox_vars_set = {}
            self.groups_set = {}
            for name, group in grouped_set:
                group_owned = sum(idx in self.inventory for idx in group.index)
                group_total = len(group)
                group_display = f"{name} ({group_owned}/{group_total})"
                values = ["", group_display] + [""] * (len(self.df.columns) - 1)
                group_id = self.tree_set.insert("", tk.END, text=f"Group: {name}", values=values, open=False, tags=("group",))
                self.groups_set[group_id] = group

            self.update_inventory_counter()
            self.show_group_bar_chart()
            self.show_group_bar_chart(is_set=True)
            self.update_pack_suggestion_for_current_tab()
            

    def on_item_select(self, event):
        
        widget = event.widget
        selected = widget.selection()
        if not selected:
            return
        item_id = selected[0]
        # Determine which tree and group mapping to use
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
        # Display image for selected card
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
            values = [u"☑" if inv else u"☐"] + [row[col] for col in self.df.columns]
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
            widget.set(item_id, "Inventory", u"☐")
        else:
            self.inventory.add(idx)
            widget.set(item_id, "Inventory", u"☑")
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
        if parent and self.groups and parent in self.groups and tree_widget == self.tree:
            group_df = self.groups[parent]
            values = tree_widget.item(item_id, "values")[1:]
            for idx, row in group_df.iterrows():
                if all(str(row[col]) == str(val) for col, val in zip(self.df.columns, values)):
                    return idx
        else:
            values = tree_widget.item(item_id, "values")[1:]
            for idx, row in self.df.iterrows():
                if all(str(row[col]) == str(val) for col, val in zip(self.df.columns, values)):
                    return idx
        return None

    def show_group_bar_chart(self, is_set=False):
        group_col = self.group_var.get()
        if group_col.lower() in ["id", "name"]:
            self.clear_pie_chart(is_set)
            return
        df = self._get_set_df(self.df) if is_set else self.df
        if group_col not in df.columns:
            self.clear_pie_chart(is_set)
            return

        owned_mask = df.index.isin(self.inventory)
        group_counts = df[group_col].value_counts().sort_index()
        owned_counts = df[owned_mask][group_col].value_counts().reindex(group_counts.index, fill_value=0)
        missing_counts = group_counts - owned_counts

        # Normalize to percentage
        total_counts = group_counts
        owned_pct = owned_counts / total_counts * 100
        missing_pct = missing_counts / total_counts * 100

        fig, ax = plt.subplots(figsize=(6, max(4, len(group_counts) * 0.6)))
        ax.barh(group_counts.index, owned_pct, label="Owned", color="#4caf50")
        ax.barh(group_counts.index, missing_pct, left=owned_pct, label="Missing", color="#e57373")
        ax.set_xlabel("Percentage (%)")
        ax.set_ylabel(group_col.capitalize())
        ax.set_xlim(0, 100)
        ax.set_title(f"{group_col.capitalize()} - Owned vs Missing (%)")
        ax.legend(loc="lower right")
        plt.tight_layout()

        # Replace the pie chart with the bar chart in the GUI
        if is_set:
            if getattr(self, "pie_canvas_set", None):
                self.pie_canvas_set.get_tk_widget().destroy()
            self.pie_canvas_set = FigureCanvasTkAgg(fig, master=self.pie_frame_set)
            self.pie_canvas_set.draw()
            self.pie_canvas_set.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            if getattr(self, "pie_canvas", None):
                self.pie_canvas.get_tk_widget().destroy()
            self.pie_canvas = FigureCanvasTkAgg(fig, master=self.pie_frame)
            self.pie_canvas.draw()
            self.pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        plt.close(fig)

    def clear_pie_chart(self, is_set=False):
        if is_set:
            if getattr(self, "pie_canvas_set", None):
                self.pie_canvas_set.get_tk_widget().destroy()
                self.pie_canvas_set = None
        else:
            if getattr(self, "pie_canvas", None):
                self.pie_canvas.get_tk_widget().destroy()
                self.pie_canvas = None

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
            self.set_completion_label.config(
                text=f"Minimum Set Completion: {set_owned} / {set_total} (missing: {set_missing})"
            )
            self._update_set_pack_completion(set_df)
        else:
            self.set_completion_label.config(text="No rarity data available.")
            self._clear_set_pack_completion("No rarity data available.", "#e8f5e9")

    def _update_set_pack_completion(self, set_df):

        for widget in self.set_pack_completion_frame.winfo_children():
            widget.destroy()
        if "pack" in self.df.columns:
            pack_counts = set_df["pack"].value_counts()
            owned_packs = set_df[set_df.index.isin(self.inventory)]["pack"].value_counts()
            self.pack_completion_data = []
            for pack in pack_counts.index:
                owned = owned_packs.get(pack, 0)
                total_pack = pack_counts[pack]
                missing = total_pack - owned
                color = "#1c9625" if missing == 0 else "#b9c4ba"
                text = f"{pack}: {owned}/{total_pack} (missing: {missing})"
                lbl = tk.Label(self.set_pack_completion_frame, text=text, bg=color, font=("Arial", 10), anchor="w")
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
        self.general_inventory_label.config(text=f"Inventory: {owned} / {total} (missing: {missing})")

    def _update_inventory_by_pack(self):

        for widget in self.pack_inventory_frame.winfo_children():
            widget.destroy()
        if 'pack' in self.df.columns:
            pack_counts = self.df['pack'].value_counts()
            owned_packs = self.df[self.df.index.isin(self.inventory)]['pack'].value_counts()
            for pack in pack_counts.index:
                owned = owned_packs.get(pack, 0)
                total_pack = pack_counts[pack]
                missing = total_pack - owned
                color = "#0a78f4" if missing == 0 else "#b5c1ca"
                text = f"{pack}: {owned}/{total_pack} (missing: {missing})"
                lbl = tk.Label(self.pack_inventory_frame, text=text, bg=color, font=("Arial", 10), anchor="w")
                lbl.pack(side=tk.TOP, anchor="w", fill=tk.X, padx=2, pady=1)
        else:
            lbl = tk.Label(self.pack_inventory_frame, text="No pack data available.", bg="#e3f2fd")
            lbl.pack(side=tk.TOP, anchor="w", fill=tk.X, padx=2, pady=1)

    def update_pack_suggestion_for_current_tab(self):

        current_tab = self.tab_control.select()
        is_set = (current_tab == str(self.tab_set))
        self.update_pack_suggestion(is_set=is_set)

    def update_pack_suggestion(self, is_set=False):

        packs = self._get_incomplete_packs(is_set=is_set)
        if not packs:
            self._set_suggestion_label("Congratulations! All packs are complete.", is_set)
            return

        if "pack" not in self.df.columns or "rarity" not in self.df.columns:
            self._set_suggestion_label("Pack or rarity data missing.", is_set)
            return

        if is_set:
            df = self._get_set_df(self.df)
            relevant_indices = self.set
        else:
            df = self.df
            relevant_indices = set(self.df.index)

        missing_cards = df[(~df.index.isin(self.inventory)) & (df.index.isin(relevant_indices))]
        missing_cards = missing_cards[missing_cards["rarity"].notna() & missing_cards["pack"].notna()]
        rarity_to_row = self._get_rarity_to_row()
        pack_probs = self._calculate_pack_probabilities(packs, missing_cards, rarity_to_row)

        if not pack_probs:
            self._set_suggestion_label("No probability data available.", is_set)
            return

        self._display_pack_suggestion(pack_probs, is_set)

    def _set_suggestion_label(self, text, is_set):

        if is_set:
            self.suggestion_label_set.config(text=text)
        else:
            self.suggestion_label.config(text=text)

    def _get_incomplete_packs(self, is_set=False):
        if is_set:
            return [p for p in getattr(self, 'pack_completion_data', []) if p[0] != "Both" and p[3] > 0]
        else:
            
            if "pack" not in self.df.columns:
                return []
            pack_counts = self.df["pack"].value_counts()
            owned_packs = self.df[self.df.index.isin(self.inventory)]["pack"].value_counts()
            incomplete = []
            for pack in pack_counts.index:
                owned = owned_packs.get(pack, 0)
                total = pack_counts[pack]
                missing = total - owned
                if pack != "Both" and missing > 0:
                    incomplete.append((pack, owned, total, missing))
        return incomplete

    def _get_rarity_to_row(self):
        rarity_order = [
            "Common", "Uncommon", "Rare", "Rare EX", "Full Art",
            "Full Art EX/Support", "Immersive", "Gold Crown", "One shiny star", "Two shiny star"
        ]
        return {r: i for i, r in enumerate(rarity_order)}

    def _calculate_pack_probabilities(self, packs, missing_cards, rarity_to_row):

        pack_probs = {}
        prob_matrix = logic.calc_prob()
        for pack_info in packs:
            pack_name = pack_info[0]
            cards_in_pack = missing_cards[(missing_cards["pack"] == pack_name) | (missing_cards["pack"] == "Both")]
            prob_sum = [1.0, 1.0, 1.0, 1.0, 1.0]
            for _, card in cards_in_pack.iterrows():
                rarity = card["rarity"]
                if rarity not in rarity_to_row:
                    continue
                row_idx = rarity_to_row[rarity]
                if row_idx >= len(prob_matrix):
                    continue
                row_p = 1 - np.array(prob_matrix[row_idx])
                prob = np.concatenate((np.repeat(row_p[0], 3), row_p[1:]))
                prob_sum *= prob

            pack_probs[pack_name] = 1 - np.prod(prob_sum)
        return pack_probs

    def _display_pack_suggestion(self, pack_probs, is_set=False):
        
        max_prob = max(pack_probs.values())
        best_packs = [p for p, v in pack_probs.items() if abs(v - max_prob) < 1e-8]
        suggestion = ""
        if len(best_packs) == 1:
            suggestion += f"Suggestion: Open '{best_packs[0]}' for better chances of completion.\n"
        else:
            suggestion += f"Suggestion: Open any of {', '.join(best_packs)}\n"
        self._set_suggestion_label(suggestion.strip(), is_set)

    def display_card_image(self, idx, widget):
        try:
            row = self.df.loc[idx]
        except Exception:
            return

        card_name = row.get("name", "")
        card_id = row.get("id", "")
        card_id = card_id.split('-')[1].lstrip('0') if '-' in card_id else card_id

        label = self.img_label_set if widget == self.tree_set else self.img_label

        label.config(image="", text="Loading image...")
        label.image = None

        threading.Thread(
            target=self._fetch_and_update_image,
            args=(card_name, card_id, label),
            daemon=True
        ).start()

    def _fetch_and_update_image(self, card_name, card_id, label):
        photo = None
        error_message = None
        try:
            url = img_aqcuisition.get_image(card_name=card_name, card_id=card_id)
            if not url:
                error_message = "No image URL found"
            else:
                response = requests.get(url)
                image = Image.open(io.BytesIO(response.content))
                image = image.resize((300, 420), Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS)
                photo = ImageTk.PhotoImage(image)
        except Exception as e:
            error_message = f"Image load error: {e}"

        def update_label():
            if error_message:
                self.set_status_message(error_message)
                label.config(image="", text="Image not available")
                label.image = None
            elif photo:
                label.config(image=photo, text="")
                label.image = photo
            else:
                label.config(image="", text="Image not available")
                label.image = None

        self.after(0, update_label)

    def set_status_message(self, message, timeout=5000):
        self.status_var.set(message)
        if timeout:
            self.after(timeout, lambda: self.status_var.set(""))

