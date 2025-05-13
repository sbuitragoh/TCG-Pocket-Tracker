import tkinter as tk
import importer
import logic
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import filedialog
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

class DataFrameViewer(tk.Tk):
    
    def __init__(self, dataframe):
        super().__init__()
        self.title("DataFrame Viewer")
        self.geometry("1300x900")
        
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
        self.create_menu()
        self.create_widgets()
        self.show_dataframe(self.df)

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
                    tk.messagebox.showerror("Error", f"Failed to import {path}:\n{e}")
            if dfs:
                self.df = pd.concat(dfs, ignore_index=True)
                if 'pack' in self.df.columns:
                    self.df['pack'] = self.df['pack'].where(self.df['pack'].notna(), 'Both')
                self.group_var.set(self.df.columns[0])
                self.inventory = set()
                self.show_dataframe(self.df)

    def save_progress(self):

        file_path = filedialog.asksaveasfilename(defaultextension=".pif", filetypes=[("Pokemon Inventory Files", "*.pif"), ("All Files", "*.*")])
        if file_path:
            try:
                with open(file_path, "w") as f:
                    for idx in self.inventory:
                        f.write(str(idx) + "\n")
            except Exception as e:
                tk.messagebox.showerror("Error", f"Failed to save progress:\n{e}")

    def load_progress(self):

        file_path = filedialog.askopenfilename(defaultextension=".pif", filetypes=[("Pokemon Inventory Files", "*.pif"), ("All Files", "*.*")])
        if file_path:
            try:
                with open(file_path, "r") as f:
                    indices = set()
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                idx = int(line)
                            except ValueError:
                                idx = line
                            indices.add(idx)
                    self.inventory = indices

                if self.groups:
                    self.on_group_change(self.group_var.get())
                else:
                    self.show_dataframe(self.df)
            except Exception as e:
                tk.messagebox.showerror("Error", f"Failed to load progress:\n{e}")

    def create_widgets(self):
        
        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        group_label = tk.Label(top_frame, text="Group by:")
        group_label.pack(side=tk.LEFT)
        group_menu = ttk.Combobox(top_frame, textvariable=self.group_var, values=list(self.df.columns), state="readonly")
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

            pie_frame = tk.LabelFrame(right_frame, text="Pie Chart", padx=10, pady=10)
            pie_frame.pack(fill=tk.BOTH, expand=False, pady=5)
            if is_set:
                self.pie_frame_set = pie_frame
                self.pie_canvas_set = None
            else:
                self.pie_frame = pie_frame
                self.pie_canvas = None

            suggestion_frame = tk.LabelFrame(right_frame, text="Which pack should you open?", padx=10, pady=10)
            suggestion_frame.pack(fill=tk.BOTH, expand=False, pady=5)
            suggestion_label = tk.Label(suggestion_frame, text="", font=("Arial", 12, "bold"), fg="#1565c0")
            suggestion_label.pack(fill=tk.BOTH, expand=True)
            if is_set:
                self.suggestion_label_set = suggestion_label
            else:
                self.suggestion_label = suggestion_label

        bottom_main_frame = tk.Frame(self)
        bottom_main_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

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

        inventory_frame = tk.Frame(bottom_main_frame)
        inventory_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        inventory_main_frame = tk.LabelFrame(inventory_frame, text="Inventory", padx=10, pady=10, bg="#e3f2fd", fg="#1565c0", labelanchor="n")
        inventory_main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=2, pady=2)

        self.general_inventory_label = tk.Label(inventory_main_frame, text="", bg="#e3f2fd", fg="#1565c0", font=("Arial", 11, "bold"))
        self.general_inventory_label.pack(anchor="w", padx=5, pady=2)


        inventory_packs_frame = tk.LabelFrame(inventory_frame, text="Inventory Packs", padx=10, pady=10, bg="#e3f2fd", fg="#1565c0", labelanchor="n")
        inventory_packs_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.pack_inventory_frame = tk.Frame(inventory_packs_frame, bg="#e3f2fd")
        self.pack_inventory_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def show_dataframe(self, df):
        
        set_df = self._get_set_df(df)
        self.set = set(set_df.index)
        
        self._show_tree(self.tree, df, self.pie_frame, is_set=False)
        self._show_tree(self.tree_set, set_df, self.pie_frame_set, is_set=True)
        self.groups = None
        self.update_inventory_counter()
        self.show_group_pie_chart()
        self.show_group_pie_chart(is_set=True)
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
            self.show_group_pie_chart(is_set=False)
            self.update_pack_suggestion_for_current_tab()
        else:
            self.show_group_pie_chart(is_set=True)
            self.update_pack_suggestion_for_current_tab()

    def on_group_change(self, value):
        
        grouped = self.df.groupby(value)
        self.tree.delete(*self.tree.get_children())
        self.checkbox_vars_all = {}
        self.groups = {}
        for name, group in grouped:
            group_owned = sum(idx in self.inventory for idx in group.index)
            group_total = len(group)
            group_display = f"{name} ({group_owned}/{group_total})"
            values = ["", group_display] + [""] * (len(self.df.columns) - 1)
            group_id = self.tree.insert("", tk.END, text=f"Group: {name}", values=values, open=False, tags=("group",))
            self.groups[group_id] = group
        
        set_df = self._get_set_df(self.df)
        grouped_set = set_df.groupby(value)
        self.tree_set.delete(*self.tree_set.get_children())
        self.checkbox_vars_set = {}
        for name, group in grouped_set:
            group_owned = sum(idx in self.inventory for idx in group.index)
            group_total = len(group)
            group_display = f"{name} ({group_owned}/{group_total})"
            values = ["", group_display] + [""] * (len(self.df.columns) - 1)
            group_id = self.tree_set.insert("", tk.END, text=f"Group: {name}", values=values, open=False, tags=("group",))
            self.groups[group_id] = group
        
        self.update_inventory_counter()
        self.show_group_pie_chart()
        self.show_group_pie_chart(is_set=True)
        self.update_pack_suggestion_for_current_tab()

    def on_item_select(self, event):
        
        widget = event.widget
        selected = widget.selection()
        if not selected:
            return
        item_id = selected[0]
        if self.is_group_node(item_id):
            self.handle_group_selection(item_id)
        else:
            self.handle_item_selection()

    def is_group_node(self, item_id):
        return self.groups and item_id in self.groups

    def handle_group_selection(self, item_id):

        group_df = self.groups[item_id]
        if not self.tree.get_children(item_id):
            self.expand_group(item_id, group_df)
        else:
            self.collapse_group(item_id)
        self.current_group = group_df
        self.update_inventory_counter()

    def expand_group(self, item_id, group_df):

        for idx, row in group_df.iterrows():
            inv = 1 if idx in self.inventory else 0
            values = [u"☑" if inv else u"☐"] + [row[col] for col in self.df.columns]
            child_id = self.tree.insert(item_id, tk.END, values=values, tags=("item",))
            self.checkbox_vars_all[child_id] = tk.IntVar(value=inv)
            self.tree.set(child_id, "Inventory", u"☑" if inv else u"☐")

    def collapse_group(self, item_id):

        for child in self.tree.get_children(item_id):
            self.tree.delete(child)

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

    def show_group_pie_chart(self, is_set=False):

        group_col = self.group_var.get()
        if group_col.lower() in ["id", "name"]:
            self.clear_pie_chart(is_set)
            return
        df = self._get_set_df(self.df) if is_set else self.df
        counts = df[group_col].value_counts()
        if counts.empty:
            self.clear_pie_chart(is_set)
            return
        owned_counts = df[df.index.isin(self.inventory)][group_col].value_counts()
        labels = []
        for group in counts.index:
            owned = owned_counts.get(group, 0)
            total = counts[group]
            labels.append(f"{group} ({owned}/{total})")
        fig, ax = plt.subplots(figsize=(2.5, 2.5))
        wedges, _ = ax.pie(counts, labels=None, startangle=90)
        ax.set_title(f"{group_col} distribution")
        ax.legend(wedges, labels, title=group_col, loc="lower center", bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=9)
        fig.subplots_adjust(left=0.05, right=0.95, bottom=0.25, top=0.90)
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
                text=f"Set Completion (Common/Uncommon/Rare/Rare EX): {set_owned} / {set_total} (missing: {set_missing})"
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
                color = "#a5d6a7" if missing == 0 else "#ffe082"
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
                color = "#a5d6a7" if missing == 0 else "#ffe082"
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

    def _calculate_pack_probabilities(self, packs, missing_cards, rarity_to_row, is_set=False):

        pack_probs = {}
        prob_matrix = logic.calc_prob()
        for pack_info in packs:
            pack_name = pack_info[0]
            cards_in_pack = missing_cards[(missing_cards["pack"] == pack_name) | (missing_cards["pack"] == "Both")]
            prob_sum = 0.0
            for _, card in cards_in_pack.iterrows():
                rarity = card["rarity"]
                if rarity not in rarity_to_row:
                    continue
                row_idx = rarity_to_row[rarity]
                if row_idx >= len(prob_matrix):
                    continue
                row_p = prob_matrix[row_idx]
                prob = 1 - np.prod(1 - np.array(row_p))
                if is_set: 
                    rarity_set = self.df[self.df.index.isin(self.set)]
                else:
                    rarity_set = self.df[self.df.index.isin(self.df.index)]
                
                prob_rar = prob * (1 / rarity_set[rarity_set['rarity'] == rarity].shape[0])
                prob_sum += prob_rar

            pack_probs[pack_name] = prob_sum 
        return pack_probs

    def _display_pack_suggestion(self, pack_probs, is_set=False):
        
        max_prob = max(pack_probs.values())
        best_packs = [p for p, v in pack_probs.items() if abs(v - max_prob) < 1e-8]
        def fmt_prob(p): return f"{100*p:.2f}%"
        suggestion = ""
        if len(best_packs) == 1:
            suggestion += f"Suggestion: Open '{best_packs[0]}' (probability to get a missing card: {fmt_prob(max_prob)})\n"
        else:
            suggestion += f"Suggestion: Open any of {', '.join(best_packs)} (probability: {fmt_prob(max_prob)})\n"
        other_packs = [(p, v) for p, v in pack_probs.items() if p not in best_packs]
        if other_packs:
            suggestion += "\nOther packs:\n"
            for p, v in sorted(other_packs, key=lambda x: -x[1]):
                suggestion += f"  {p}: {fmt_prob(v)}\n"
        self._set_suggestion_label(suggestion.strip(), is_set)


if __name__ == "__main__":
    df = importer.read_json_file()
    df = importer.clean_db(df)
    app = DataFrameViewer(df)
    app.mainloop()