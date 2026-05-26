#!/usr/bin/env python3
"""Simple Tkinter UI for Anki deck listing, export, and update workflows.

Features:
- List decks from `apy info`
- Export notes for selected deck or custom query via export_anki_notes.py
- Update notes from a selected markdown file or folder via update_anki_notes.py
"""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def parse_decks(apy_info: str) -> list[str]:
    decks: list[str] = []
    in_decks = False
    for raw_line in apy_info.splitlines():
        line = raw_line.rstrip("\n")
        if line.startswith("Decks:"):
            in_decks = True
            continue
        if in_decks and line.startswith("Model"):
            break
        if in_decks and line.startswith("  - "):
            decks.append(line.replace("  - ", "", 1).strip())
    return decks


class AnkiManagerUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Anki Manager UI")
        self.root.geometry("980x640")

        self.base_dir = Path(__file__).resolve().parent
        self.export_script = self.base_dir / "export_anki_notes.py"
        self.update_script = self.base_dir / "update_anki_notes.py"

        self.log_queue: queue.Queue[str] = queue.Queue()

        self._build_ui()
        self._poll_log_queue()
        self.refresh_decks()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(main)
        top.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(top, text="Output folder:").pack(side=tk.LEFT)
        self.output_var = tk.StringVar(value=str(self.base_dir / "anki-export"))
        self.output_entry = ttk.Entry(top, textvariable=self.output_var)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ttk.Button(top, text="Browse", command=self.pick_output_dir).pack(side=tk.LEFT)

        body = ttk.Panedwindow(main, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(body, padding=8)
        right = ttk.Frame(body, padding=8)
        body.add(left, weight=1)
        body.add(right, weight=2)

        ttk.Label(left, text="Decks").pack(anchor=tk.W)

        self.deck_list = tk.Listbox(left, height=20, exportselection=False)
        self.deck_list.pack(fill=tk.BOTH, expand=True)

        deck_buttons = ttk.Frame(left)
        deck_buttons.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(deck_buttons, text="Refresh Decks", command=self.refresh_decks).pack(
            side=tk.LEFT
        )
        ttk.Button(
            deck_buttons,
            text="Export Selected Deck",
            command=self.export_selected_deck,
        ).pack(side=tk.LEFT, padx=(8, 0))

        query_box = ttk.LabelFrame(right, text="Export")
        query_box.pack(fill=tk.X, pady=(0, 8))

        query_row = ttk.Frame(query_box, padding=8)
        query_row.pack(fill=tk.X)
        ttk.Label(query_row, text="Custom query:").pack(side=tk.LEFT)
        self.query_var = tk.StringVar(value="")
        self.query_entry = ttk.Entry(query_row, textvariable=self.query_var)
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ttk.Button(
            query_row,
            text="Export Query",
            command=self.export_custom_query,
        ).pack(side=tk.LEFT)

        update_box = ttk.LabelFrame(right, text="Update")
        update_box.pack(fill=tk.X, pady=(0, 8))

        update_row = ttk.Frame(update_box, padding=8)
        update_row.pack(fill=tk.X)
        self.update_target_var = tk.StringVar(value=self.output_var.get())
        ttk.Label(update_row, text="Target file/folder:").pack(side=tk.LEFT)
        self.update_entry = ttk.Entry(update_row, textvariable=self.update_target_var)
        self.update_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ttk.Button(update_row, text="Pick", command=self.pick_update_target).pack(side=tk.LEFT)

        update_buttons = ttk.Frame(update_box, padding=(8, 0, 8, 8))
        update_buttons.pack(fill=tk.X)
        ttk.Button(
            update_buttons,
            text="Update Notes",
            command=self.update_notes,
        ).pack(side=tk.LEFT)

        log_box = ttk.LabelFrame(right, text="Logs")
        log_box.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_box, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _append_log(self, text: str) -> None:
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def _poll_log_queue(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(line)
        self.root.after(150, self._poll_log_queue)

    def _run_in_thread(self, title: str, argv: list[str], on_success=None) -> None:
        def worker() -> None:
            self.log_queue.put(f"$ {' '.join(argv)}")
            try:
                result = subprocess.run(
                    argv,
                    cwd=str(self.base_dir),
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError as exc:
                self.log_queue.put(f"{title} failed: {exc}")
                return

            if result.stdout.strip():
                self.log_queue.put(result.stdout.rstrip())
            if result.stderr.strip():
                self.log_queue.put(result.stderr.rstrip())

            if result.returncode == 0:
                self.log_queue.put(f"{title} completed successfully.")
                if on_success:
                    self.root.after(0, on_success)
            else:
                self.log_queue.put(f"{title} failed with exit code {result.returncode}.")

        threading.Thread(target=worker, daemon=True).start()

    def pick_output_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_var.get() or str(self.base_dir))
        if selected:
            self.output_var.set(selected)
            if not self.update_target_var.get().strip():
                self.update_target_var.set(selected)

    def pick_update_target(self) -> None:
        initial = self.update_target_var.get().strip() or self.output_var.get().strip()
        initial_path = Path(initial) if initial else self.base_dir

        # macOS Tk dialogs are more reliable when initialdir points to an existing folder.
        if initial_path.exists() and initial_path.is_file():
            initial_dir = initial_path.parent
        elif initial_path.exists() and initial_path.is_dir():
            initial_dir = initial_path
        else:
            initial_dir = self.base_dir

        selected_dir = filedialog.askdirectory(initialdir=str(initial_dir))
        if selected_dir:
            self.update_target_var.set(selected_dir)
            return

        selected_file = filedialog.askopenfilename(
            initialdir=str(initial_dir),
            filetypes=[("Markdown", "*.md"), ("All files", "*.*")],
        )
        if selected_file:
            self.update_target_var.set(selected_file)

    def refresh_decks(self) -> None:
        try:
            result = subprocess.run(
                ["apy", "info"],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            messagebox.showerror("apy not found", "Could not find 'apy' on PATH.")
            return

        if result.returncode != 0:
            messagebox.showerror("Failed to load decks", result.stderr or result.stdout)
            return

        decks = parse_decks(result.stdout)
        self.deck_list.delete(0, tk.END)
        for deck in decks:
            self.deck_list.insert(tk.END, deck)

        self._append_log(f"Loaded {len(decks)} deck(s).")

    def _ensure_scripts(self) -> bool:
        if not self.export_script.exists() or not self.update_script.exists():
            messagebox.showerror(
                "Missing scripts",
                "Expected export_anki_notes.py and update_anki_notes.py next to this UI script.",
            )
            return False
        return True

    def _deck_query(self, deck_name: str) -> str:
        escaped = deck_name.replace('"', r'\"')
        return f'deck:"{escaped}"'

    def export_selected_deck(self) -> None:
        if not self._ensure_scripts():
            return

        selection = self.deck_list.curselection()
        if not selection:
            messagebox.showinfo("No deck selected", "Select a deck first.")
            return

        deck_name = self.deck_list.get(selection[0])
        query = self._deck_query(deck_name)
        self.query_var.set(query)
        self._run_export(query)

    def export_custom_query(self) -> None:
        if not self._ensure_scripts():
            return

        query = self.query_var.get().strip()
        if not query:
            messagebox.showinfo("Missing query", "Enter an Anki query.")
            return

        self._run_export(query)

    def _run_export(self, query: str) -> None:
        output_dir = self.output_var.get().strip()
        if not output_dir:
            messagebox.showinfo("Missing output folder", "Choose an output folder.")
            return

        cmd = [sys.executable, str(self.export_script), query, output_dir]

        def on_success() -> None:
            if not self.update_target_var.get().strip():
                self.update_target_var.set(output_dir)

        self._run_in_thread("Export", cmd, on_success=on_success)

    def update_notes(self) -> None:
        if not self._ensure_scripts():
            return

        target = self.update_target_var.get().strip()
        if not target:
            messagebox.showinfo("Missing target", "Choose a markdown file or folder to update.")
            return

        target_path = Path(target)
        if not target_path.exists():
            messagebox.showerror("Path not found", f"Target path does not exist:\n{target}")
            return

        cmd = [sys.executable, str(self.update_script), str(target_path)]
        self._run_in_thread("Update", cmd)


def main() -> int:
    root = tk.Tk()
    app = AnkiManagerUI(root)
    _ = app
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
