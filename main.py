import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

MAX_XP   = 100_000
ADD_XP   = 100_000_000
HOTBAR   = range(0, 8)
BACKPACK = range(8, 32)
RUNES    = range(32, 56)

SKILL_NAMES = {
    "4pefO9k": "Attack",
    "Wf3i7Ha": "Artisan",
    "waK-8Ey": "Construction",
    "Tn7t6DQ": "Cooking",
    "0hreSMR": "Magic",
    "jqX0Gh6": "Mining",
    "heq7u88": "Ranged",
    "NOqC-z-": "Runecrafting",
    "4zYUGF5": "Woodcutting"
}

class DragonWilderApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        master.title("DragonWilder v0.1")
        master.geometry("1000x1000")
        master.minsize(800, 500)  # ensure save button fits
        style = ttk.Style(master)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        # auto‐load items.json
        try:
            with open("items.json", "r", encoding="utf-8") as f:
                items = json.load(f)
            self.items_by_name = {itm["name"]: itm for itm in items}
            self.item_names = sorted(self.items_by_name)
            self.items_loaded = True
        except Exception:
            messagebox.showwarning("Warning", "Could not load items.json; hotbar/backpack disabled.")
            self.items_by_name = {}
            self.item_names = []
            self.items_loaded = False

        # auto‐load runes.json
        try:
            with open("runes.json", "r", encoding="utf-8") as f:
                runes = json.load(f)
            self.runes_by_name = {r["name"]: r for r in runes}
            self.rune_names = sorted(self.runes_by_name)
            self.runes_loaded = True
        except Exception:
            messagebox.showwarning("Warning", "Could not load runes.json; runes disabled.")
            self.runes_by_name = {}
            self.rune_names = []
            self.runes_loaded = False

        self.file_path = None
        self.data = None

        # Top controls
        top = ttk.Frame(self)
        top.pack(side="top", fill="x", pady=(0,10))
        ttk.Button(top, text="Choose character", command=self.choose_file).pack(side="left", padx=5)
        self.name_var = tk.StringVar(value="No file loaded")
        ttk.Label(top, textvariable=self.name_var, font=("TkDefaultFont", 12, "bold")).pack(side="left", padx=20)

        # Main editor area
        self.editor = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        self.editor.pack(side="top", fill="both", expand=True)

        # Save button at bottom
        save_frame = ttk.Frame(self)
        save_frame.pack(side="bottom", fill="x", pady=5)
        ttk.Button(save_frame, text="Save file", command=self.save_file).pack()

        self.pack(fill="both", expand=True)

    def choose_file(self):
        default = os.path.join(
            os.environ.get("LOCALAPPDATA",""),
            "RSDragonwilds", "Saved", "SaveCharacters"
        )
        folder = default if os.path.isdir(default) else os.getcwd()
        path = filedialog.askopenfilename(
            title="Select character JSON",
            initialdir=folder,
            filetypes=[("JSON Files","*.json")],
            defaultextension=".json"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load JSON:\n{e}")
            return

        self.file_path = path
        name = self.data.get("meta_data", {}).get("char_name", "<unknown>")
        self.name_var.set(f"Chosen character: {name}")
        self.build_editor()

    def update_inventory(self, slot, name, count):
        key = str(slot)
        if not name:
            self.data["Inventory"].pop(key, None)
            return
        lookup = self.runes_by_name if slot in RUNES else self.items_by_name
        itm = lookup.get(name)
        if not itm:
            return
        self.data["Inventory"][key] = {
            "GUID": itm["GUID"],
            "ItemData": itm["ItemData"],
            "Count": count
        }

    def build_editor(self):
        # clear previous panes
        for p in self.editor.panes():
            self.editor.forget(p)

        # --- Skills pane ---
        skills_frame = ttk.Labelframe(self.editor, text="Skills", padding=5)
        self.editor.add(skills_frame, weight=1)
        for i, skill in enumerate(self.data["Skills"]["Skills"]):
            sid = skill.get("Id", "")
            label = next(
                (n for p,n in SKILL_NAMES.items() if sid.startswith(p)),
                f"Skill {i+1}"
            )
            ttk.Label(skills_frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=2)

            xp_var = tk.IntVar(value=skill.get("Xp", 0))
            ttk.Label(skills_frame, textvariable=xp_var, width=8).grid(row=i, column=1, padx=5)

            # update only the Xp value, preserve the original Id
            def mk_set(idx, var, val):
                def _set():
                    self.data["Skills"]["Skills"][idx]["Xp"] = val
                    var.set(val)
                return _set

            def mk_add(idx, var, amt):
                def _add():
                    entry = self.data["Skills"]["Skills"][idx]
                    entry["Xp"] = entry.get("Xp", 0) + amt
                    var.set(entry["Xp"])
                return _add

            # Button order: 50, +100m xp, Reset
            ttk.Button(skills_frame, text="50",      command=mk_set(i, xp_var,     MAX_XP)).grid(row=i, column=2, padx=5)
            ttk.Button(skills_frame, text="+100m xp",command=mk_add(i, xp_var, ADD_XP  )).grid(row=i, column=3, padx=5)
            ttk.Button(skills_frame, text="Reset",   command=mk_set(i, xp_var,         0)).grid(row=i, column=4, padx=5)

        # --- Inventory notebook ---
        inv_nb = ttk.Notebook(self.editor)
        self.editor.add(inv_nb, weight=1)

        def make_tab(title, slots, names, loaded, lookup):
            frame = ttk.Frame(inv_nb, padding=5)
            inv_nb.add(frame, text=title)
            for r, s in enumerate(slots):
                ttk.Label(frame, text=f"Slot {s}").grid(row=r, column=0, sticky="w", padx=5, pady=2)

                # Item dropdown
                cbv = tk.StringVar()
                cb = ttk.Combobox(
                    frame,
                    values=names,
                    textvariable=cbv,
                    state="readonly" if loaded else "disabled",
                    width=20
                )
                cb.grid(row=r, column=1, padx=5)

                # Count spinbox
                cntv = tk.IntVar(
                    value=self.data["Inventory"]
                              .get(str(s), {})
                              .get("Count", 0)
                )
                sb = ttk.Spinbox(
                    frame,
                    from_=0,
                    to=(lookup[names[0]]["max"] if loaded and names else 0),
                    increment=1,
                    textvariable=cntv,
                    width=6
                )
                sb.grid(row=r, column=2, padx=5)

                # Max button
                def make_max(s=s, cbv=cbv, cv=cntv):
                    def fn():
                        itm = lookup.get(cbv.get())
                        if itm:
                            cv.set(itm["max"])
                            self.update_inventory(s, cbv.get(), itm["max"])
                    return fn
                ttk.Button(frame, text="Max", command=make_max()).grid(row=r, column=3, padx=5)

                # Prefill existing
                ent = self.data["Inventory"].get(str(s))
                if ent and loaded:
                    for nm, itm in lookup.items():
                        if itm["GUID"] == ent.get("GUID"):
                            cbv.set(nm)
                            sb.config(to=itm["max"])
                            cntv.set(ent.get("Count", 0))
                            break

                # Update on select
                def on_select(event, s=s, cbv=cbv, cv=cntv, sb=sb):
                    itm = lookup.get(cbv.get(), {})
                    sb.config(to=itm.get("max", 0))
                    if cv.get() > itm.get("max", 0):
                        cv.set(itm.get("max", 0))
                    self.update_inventory(s, cbv.get(), cv.get())
                cb.bind("<<ComboboxSelected>>", on_select)

                # Trace count changes
                cntv.trace_add("write", lambda *a, s=s, cbv=cbv, cv=cntv:
                               self.update_inventory(s, cbv.get(), cv.get()))

        make_tab("Hotbar",   HOTBAR,   self.item_names, self.items_loaded, self.items_by_name)
        make_tab("Backpack", BACKPACK, self.item_names, self.items_loaded, self.items_by_name)
        make_tab("Runes",    RUNES,    self.rune_names, self.runes_loaded, self.runes_by_name)

    def save_file(self):
        if not self.file_path or not self.data:
            messagebox.showwarning("No file", "Load a file first!")
            return
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            messagebox.showinfo("Saved", f"Wrote back to:\n{self.file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    DragonWilderApp(root)
    root.mainloop()
