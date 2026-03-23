

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

AUTOMATION_DIR = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid/98_Automation")
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

import query_bible_study as qbs


class BibleStudySearchApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bible Study Aid")
        self.geometry("1200x760")
        self.minsize(950, 600)

        self.results_data = []
        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)

        top = ttk.Frame(outer)
        top.pack(fill="x")

        ttk.Label(top, text="Search:").pack(side="left", padx=(0, 8))

        self.query_var = tk.StringVar()
        self.query_entry = ttk.Entry(top, textvariable=self.query_var)
        self.query_entry.pack(side="left", fill="x", expand=True)
        self.query_entry.bind("<Return>", lambda event: self.run_search())

        self.search_button = ttk.Button(top, text="Search", command=self.run_search)
        self.search_button.pack(side="left", padx=(8, 0))

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(outer, textvariable=self.status_var).pack(fill="x", pady=(8, 8))

        main = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main, padding=5)
        right = ttk.Frame(main, padding=5)
        main.add(left, weight=1)
        main.add(right, weight=2)

        ttk.Label(left, text="Results").pack(anchor="w")

        left_inner = ttk.Frame(left)
        left_inner.pack(fill="both", expand=True)

        self.results_list = tk.Listbox(left_inner, exportselection=False)
        self.results_list.pack(side="left", fill="both", expand=True)
        self.results_list.bind("<<ListboxSelect>>", self.on_result_selected)

        results_scroll = ttk.Scrollbar(left_inner, orient="vertical", command=self.results_list.yview)
        results_scroll.pack(side="right", fill="y")
        self.results_list.config(yscrollcommand=results_scroll.set)

        ttk.Label(right, text="Preview").pack(anchor="w")

        right_inner = ttk.Frame(right)
        right_inner.pack(fill="both", expand=True)

        self.preview_text = tk.Text(right_inner, wrap="word")
        self.preview_text.pack(side="left", fill="both", expand=True)
        self.preview_text.config(state="disabled")

        preview_scroll = ttk.Scrollbar(right_inner, orient="vertical", command=self.preview_text.yview)
        preview_scroll.pack(side="right", fill="y")
        self.preview_text.config(yscrollcommand=preview_scroll.set)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(8, 0))

        self.copy_button = ttk.Button(actions, text="Copy Preview", command=self.copy_preview)
        self.copy_button.pack(side="left")

        self.open_path_button = ttk.Button(actions, text="Show Path", command=self.show_selected_path)
        self.open_path_button.pack(side="left", padx=(8, 0))

    def run_search(self):
        query = self.query_var.get().strip()
        if not query:
            messagebox.showinfo("Search", "Please enter a search query.")
            return

        self.results_list.delete(0, tk.END)
        self.results_data = []
        self._set_preview("")
        self.status_var.set(f"Searching for: {query}")
        self.update_idletasks()

        try:
            results = qbs.run_query(query, limit=30)
        except Exception as e:
            messagebox.showerror("Search Error", str(e))
            self.status_var.set("Search failed.")
            return

        self.results_data = results

        for item in results:
            display = f"[{item['score']}] ({item['source_type']}) {item['path']}"
            self.results_list.insert(tk.END, display)

        self.status_var.set(f"Found {len(results)} result(s).")

        if results:
            self.results_list.selection_set(0)
            self.results_list.event_generate("<<ListboxSelect>>")

    def on_result_selected(self, event=None):
        selection = self.results_list.curselection()
        if not selection:
            return

        index = selection[0]
        item = self.results_data[index]

        preview = (
            f"Title:\n{item['title']}\n\n"
            f"Source Type:\n{item['source_type']}\n\n"
            f"Path:\n{item['path']}\n\n"
            f"Score:\n{item['score']}\n\n"
            f"Snippet:\n{item['snippet']}"
        )
        self._set_preview(preview)

    def copy_preview(self):
        text = self.preview_text.get("1.0", tk.END).strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("Preview copied to clipboard.")

    def show_selected_path(self):
        selection = self.results_list.curselection()
        if not selection:
            return
        item = self.results_data[selection[0]]
        messagebox.showinfo("Result Path", item["path"])

    def _set_preview(self, text: str):
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", text)
        self.preview_text.config(state="disabled")


if __name__ == "__main__":
    app = BibleStudySearchApp()
    app.mainloop()