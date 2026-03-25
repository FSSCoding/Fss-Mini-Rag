"""Scrape Tracker dialog — domain metrics, whitelist, blacklist, and scraper settings."""

import tkinter as tk
from tkinter import ttk, simpledialog
from typing import Any, Dict

from mini_rag.scrape_registry import (
    get_domain_stats,
    load_domain_lists,
    add_to_whitelist,
    add_to_blacklist,
    remove_from_whitelist,
    remove_from_blacklist,
)
from mini_rag.gui.tooltip import ToolTip


_ROBOTS_EXPLANATION = (
    "robots.txt is a file websites use to tell web crawlers which pages "
    "they are allowed to access. When a site blocks our scraper via "
    "robots.txt, it means the site owner has asked automated tools not to "
    "access their content. We respect this by default.\n\n"
    "Domains that repeatedly block access via robots.txt are automatically "
    "added to the blacklist to avoid wasting time on future scrape attempts. "
    "You can remove a domain from the blacklist if you believe it was "
    "added in error, or add it to the whitelist to always allow scraping "
    "(though robots.txt will still be respected unless you disable it in Settings)."
)

_ROBOTS_TOGGLE_WARNING = (
    "Disabling robots.txt compliance means the scraper will ignore website "
    "owners' requests to not be crawled. This may violate terms of service "
    "and could get your IP blocked. Only disable this if you understand "
    "the implications and are running the scraper for personal research."
)

_UA_EXPLANATION = (
    "Many websites (including Wikipedia) require a descriptive user-agent "
    "with contact information before allowing automated access. Setting your "
    "details here builds a proper user-agent string that identifies you as "
    "a legitimate researcher rather than a generic bot.\n\n"
    "Format: AppName/Version (contact) — e.g.:\n"
    "FSS-Mini-RAG-Research/2.2 (bob@example.com)"
)


class ScrapeTrackerDialog(tk.Toplevel):
    """Four-tab dialog: Metrics, Whitelist, Blacklist, Settings."""

    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)
        self.title("Scrape Tracker")
        self.geometry("720x560")
        self.resizable(True, True)
        self.minsize(600, 400)
        self.transient(parent)
        self.grab_set()
        self.config_data = config
        self._build()

    def _build(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_metrics_tab()
        self._build_whitelist_tab()
        self._build_blacklist_tab()
        self._build_settings_tab()

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        refresh_btn = ttk.Button(btn_frame, text="Refresh", command=self._refresh_all)
        refresh_btn.pack(side=tk.LEFT)
        ToolTip(refresh_btn, "Reload all tabs from disk")
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT)

    # ─── Metrics Tab ───

    def _build_metrics_tab(self):
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="Domain Metrics")

        ttk.Label(
            tab,
            text="Scrape history per domain — right-click to whitelist or blacklist a domain.",
            foreground="#888888", font=("", 8, "italic"),
        ).pack(anchor=tk.W, pady=(0, 4))

        self._metrics_summary = ttk.Label(tab, text="", font=("", 9))
        self._metrics_summary.pack(anchor=tk.W, pady=(0, 6))

        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("domain", "total", "ok", "fail", "avg_words", "extractor", "errors")
        self._metrics_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")

        self._metrics_tree.heading("domain", text="Domain")
        self._metrics_tree.heading("total", text="Total")
        self._metrics_tree.heading("ok", text="OK")
        self._metrics_tree.heading("fail", text="Fail")
        self._metrics_tree.heading("avg_words", text="Avg Words")
        self._metrics_tree.heading("extractor", text="Extractor")
        self._metrics_tree.heading("errors", text="Last Error")

        self._metrics_tree.column("domain", width=180, minwidth=120)
        self._metrics_tree.column("total", width=50, anchor=tk.CENTER)
        self._metrics_tree.column("ok", width=40, anchor=tk.CENTER)
        self._metrics_tree.column("fail", width=40, anchor=tk.CENTER)
        self._metrics_tree.column("avg_words", width=70, anchor=tk.CENTER)
        self._metrics_tree.column("extractor", width=110)
        self._metrics_tree.column("errors", width=200)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._metrics_tree.yview)
        self._metrics_tree.configure(yscrollcommand=scroll.set)
        self._metrics_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._metrics_menu = tk.Menu(self, tearoff=0)
        self._metrics_menu.add_command(label="Add to Whitelist", command=self._metrics_to_whitelist)
        self._metrics_menu.add_command(label="Add to Blacklist", command=self._metrics_to_blacklist)
        self._metrics_tree.bind("<Button-3>", self._metrics_context_menu)

        self._load_metrics()

    def _load_metrics(self):
        self._metrics_tree.delete(*self._metrics_tree.get_children())
        stats = get_domain_stats()

        total_domains = len(stats)
        total_scrapes = sum(s["total"] for s in stats.values())
        total_ok = sum(s["success"] for s in stats.values())
        self._metrics_summary.config(
            text=f"{total_domains} domains tracked  |  {total_scrapes} total scrapes  |  {total_ok} successful"
        )

        for domain in sorted(stats, key=lambda d: stats[d]["total"], reverse=True):
            s = stats[domain]
            last_error = s["errors"][-1] if s["errors"] else ""
            self._metrics_tree.insert("", tk.END, values=(
                domain,
                s["total"],
                s["success"],
                s["fail"],
                s["avg_words"] if s["avg_words"] else "-",
                ", ".join(s["extractors"]),
                last_error[:60],
            ))

    def _metrics_context_menu(self, event):
        item = self._metrics_tree.identify_row(event.y)
        if item:
            self._metrics_tree.selection_set(item)
            self._metrics_menu.post(event.x_root, event.y_root)

    def _get_selected_domain(self, tree) -> str:
        sel = tree.selection()
        if not sel:
            return ""
        values = tree.item(sel[0], "values")
        return values[0] if values else ""

    def _metrics_to_whitelist(self):
        domain = self._get_selected_domain(self._metrics_tree)
        if domain:
            add_to_whitelist(domain, note="Added from metrics")
            self._refresh_all()

    def _metrics_to_blacklist(self):
        domain = self._get_selected_domain(self._metrics_tree)
        if domain:
            reason = simpledialog.askstring(
                "Blacklist Reason", f"Reason for blacklisting {domain}:",
                parent=self,
            )
            add_to_blacklist(domain, reason=reason or "Manual blacklist", auto=False)
            self._refresh_all()

    # ─── Whitelist Tab ───

    def _build_whitelist_tab(self):
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="Whitelist")

        desc = ttk.Label(
            tab, wraplength=660, justify=tk.LEFT,
            text=(
                "Whitelisted domains are always allowed for scraping (robots.txt is still "
                "respected unless disabled in Settings). Add domains here that you trust "
                "and want to ensure are never auto-blacklisted."
            ),
        )
        desc.pack(anchor=tk.W, pady=(0, 8))

        # Buttons first so they always stay visible at bottom
        btn_row = ttk.Frame(tab)
        btn_row.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        wl_add = ttk.Button(btn_row, text="Add Domain", command=self._wl_add)
        wl_add.pack(side=tk.LEFT, padx=2)
        ToolTip(wl_add, "Manually add a trusted domain to always allow scraping")
        wl_rm = ttk.Button(btn_row, text="Remove", command=self._wl_remove)
        wl_rm.pack(side=tk.LEFT, padx=2)
        ToolTip(wl_rm, "Remove selected domain from the whitelist")
        wl_bl = ttk.Button(btn_row, text="Move to Blacklist", command=self._wl_to_blacklist)
        wl_bl.pack(side=tk.LEFT, padx=2)
        ToolTip(wl_bl, "Move selected domain to the blacklist (blocks future scrapes)")

        # Tree + scrollbar in a frame that fills remaining space
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("domain", "added", "note")
        self._wl_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        self._wl_tree.heading("domain", text="Domain")
        self._wl_tree.heading("added", text="Added")
        self._wl_tree.heading("note", text="Note")
        self._wl_tree.column("domain", width=220)
        self._wl_tree.column("added", width=160)
        self._wl_tree.column("note", width=260)

        wl_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._wl_tree.yview)
        self._wl_tree.configure(yscrollcommand=wl_scroll.set)
        self._wl_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        wl_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._load_whitelist()

    def _load_whitelist(self):
        self._wl_tree.delete(*self._wl_tree.get_children())
        lists = load_domain_lists()
        for domain, info in sorted(lists["whitelist"].items()):
            self._wl_tree.insert("", tk.END, values=(
                domain,
                info.get("added", "")[:19],
                info.get("note", ""),
            ))

    def _wl_add(self):
        domain = simpledialog.askstring("Add to Whitelist", "Domain (e.g. example.com):", parent=self)
        if domain and domain.strip():
            note = simpledialog.askstring("Note", "Optional note:", parent=self) or ""
            add_to_whitelist(domain.strip(), note=note)
            self._refresh_all()

    def _wl_remove(self):
        domain = self._get_selected_domain(self._wl_tree)
        if domain:
            remove_from_whitelist(domain)
            self._refresh_all()

    def _wl_to_blacklist(self):
        domain = self._get_selected_domain(self._wl_tree)
        if domain:
            reason = simpledialog.askstring(
                "Blacklist Reason", f"Reason for blacklisting {domain}:",
                parent=self,
            )
            add_to_blacklist(domain, reason=reason or "Moved from whitelist", auto=False)
            self._refresh_all()

    # ─── Blacklist Tab ───

    def _build_blacklist_tab(self):
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="Blacklist")

        info_frame = ttk.LabelFrame(tab, text="How auto-blacklisting works", padding=8)
        info_frame.pack(fill=tk.X, pady=(0, 8))
        info_label = ttk.Label(
            info_frame, wraplength=640, justify=tk.LEFT, text=_ROBOTS_EXPLANATION,
        )
        info_label.pack(fill=tk.X)

        # Buttons first so they always stay visible at bottom
        btn_row = ttk.Frame(tab)
        btn_row.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        bl_add = ttk.Button(btn_row, text="Add Domain", command=self._bl_add)
        bl_add.pack(side=tk.LEFT, padx=2)
        ToolTip(bl_add, "Manually block a domain from all future scrapes")
        bl_rm = ttk.Button(btn_row, text="Remove", command=self._bl_remove)
        bl_rm.pack(side=tk.LEFT, padx=2)
        ToolTip(bl_rm, "Unblock selected domain — allows scraping again")
        bl_wl = ttk.Button(btn_row, text="Move to Whitelist", command=self._bl_to_whitelist)
        bl_wl.pack(side=tk.LEFT, padx=2)
        ToolTip(bl_wl, "Move selected domain to whitelist (trusted, always allowed)")

        # Tree + scrollbar in a frame that fills remaining space
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("domain", "reason", "auto", "added")
        self._bl_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        self._bl_tree.heading("domain", text="Domain")
        self._bl_tree.heading("reason", text="Reason")
        self._bl_tree.heading("auto", text="Auto")
        self._bl_tree.heading("added", text="Added")
        self._bl_tree.column("domain", width=180)
        self._bl_tree.column("reason", width=300)
        self._bl_tree.column("auto", width=50, anchor=tk.CENTER)
        self._bl_tree.column("added", width=140)

        bl_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._bl_tree.yview)
        self._bl_tree.configure(yscrollcommand=bl_scroll.set)
        self._bl_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bl_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._load_blacklist()

    def _load_blacklist(self):
        self._bl_tree.delete(*self._bl_tree.get_children())
        lists = load_domain_lists()
        for domain, info in sorted(lists["blacklist"].items()):
            self._bl_tree.insert("", tk.END, values=(
                domain,
                info.get("reason", ""),
                "Yes" if info.get("auto") else "No",
                info.get("added", "")[:19],
            ))

    def _bl_add(self):
        domain = simpledialog.askstring("Add to Blacklist", "Domain (e.g. example.com):", parent=self)
        if domain and domain.strip():
            reason = simpledialog.askstring("Reason", "Reason for blocking:", parent=self) or ""
            add_to_blacklist(domain.strip(), reason=reason, auto=False)
            self._refresh_all()

    def _bl_remove(self):
        domain = self._get_selected_domain(self._bl_tree)
        if domain:
            remove_from_blacklist(domain)
            self._refresh_all()

    def _bl_to_whitelist(self):
        domain = self._get_selected_domain(self._bl_tree)
        if domain:
            note = simpledialog.askstring(
                "Whitelist Note", f"Note for whitelisting {domain}:",
                parent=self,
            )
            add_to_whitelist(domain, note=note or "Moved from blacklist")
            self._refresh_all()

    # ─── Settings Tab ───

    def _build_settings_tab(self):
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="Settings")

        # User-Agent section
        ua_frame = ttk.LabelFrame(tab, text="User-Agent Identity", padding=10)
        ua_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            ua_frame, wraplength=640, justify=tk.LEFT, text=_UA_EXPLANATION,
        ).pack(fill=tk.X, pady=(0, 8))

        fields = ttk.Frame(ua_frame)
        fields.pack(fill=tk.X)

        ttk.Label(fields, text="Application Name:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=3)
        self._ua_var = tk.StringVar(value=self.config_data.get("scraper_user_agent", "FSS-Mini-RAG-Research/2.2"))
        ua_entry = ttk.Entry(fields, textvariable=self._ua_var, width=40)
        ua_entry.grid(row=0, column=1, sticky=tk.W, padx=4, pady=3)
        ToolTip(ua_entry, "App name and version sent in HTTP requests — identifies your scraper to websites")

        ttk.Label(fields, text="Contact (email/URL):").grid(row=1, column=0, sticky=tk.W, padx=4, pady=3)
        self._contact_var = tk.StringVar(value=self.config_data.get("scraper_contact", ""))
        contact_entry = ttk.Entry(fields, textvariable=self._contact_var, width=40)
        contact_entry.grid(row=1, column=1, sticky=tk.W, padx=4, pady=3)
        ToolTip(contact_entry, "Contact info included in the User-Agent — helps sites reach you if needed")

        # Preview
        preview_frame = ttk.Frame(ua_frame)
        preview_frame.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(preview_frame, text="Resulting User-Agent:", font=("", 9, "bold")).pack(anchor=tk.W)
        self._ua_preview = ttk.Label(preview_frame, text="", font=("", 9), foreground="#888888")
        self._ua_preview.pack(anchor=tk.W)

        self._ua_var.trace_add("write", lambda *_: self._update_ua_preview())
        self._contact_var.trace_add("write", lambda *_: self._update_ua_preview())
        self._update_ua_preview()

        # robots.txt section
        robots_frame = ttk.LabelFrame(tab, text="robots.txt Compliance", padding=10)
        robots_frame.pack(fill=tk.X, pady=(0, 10))

        self._robots_var = tk.BooleanVar(value=self.config_data.get("scraper_respect_robots", True))
        robots_check = ttk.Checkbutton(
            robots_frame, text="Respect robots.txt (recommended)",
            variable=self._robots_var, command=self._on_robots_toggle,
        )
        robots_check.pack(anchor=tk.W)
        ToolTip(robots_check, "When enabled, the scraper honours website crawl rules — disable only for personal research")

        self._robots_warning = ttk.Label(
            robots_frame, wraplength=640, justify=tk.LEFT,
            text=_ROBOTS_TOGGLE_WARNING, foreground="#cc6600",
        )
        # Only show warning if already disabled
        if not self._robots_var.get():
            self._robots_warning.pack(fill=tk.X, pady=(6, 0))

        # Save button
        save_frame = ttk.Frame(tab)
        save_frame.pack(fill=tk.X, pady=(10, 0))
        save_btn = ttk.Button(save_frame, text="Save Settings", command=self._save_settings, style="Accent.TButton")
        save_btn.pack(side=tk.RIGHT)
        ToolTip(save_btn, "Save user-agent and robots.txt settings to disk")
        self._settings_status = ttk.Label(save_frame, text="", foreground="#888888")
        self._settings_status.pack(side=tk.LEFT)

    def _build_ua_string(self) -> str:
        """Build the full user-agent string from app name and contact."""
        ua = self._ua_var.get().strip() or "FSS-Mini-RAG-Research/2.2"
        contact = self._contact_var.get().strip()
        if contact:
            return f"{ua} ({contact})"
        return ua

    def _update_ua_preview(self):
        self._ua_preview.config(text=self._build_ua_string())

    def _on_robots_toggle(self):
        if not self._robots_var.get():
            self._robots_warning.pack(fill=tk.X, pady=(6, 0))
        else:
            self._robots_warning.pack_forget()

    def _save_settings(self):
        from mini_rag.gui.config_store import save_config

        self.config_data["scraper_user_agent"] = self._build_ua_string()
        self.config_data["scraper_contact"] = self._contact_var.get().strip()
        self.config_data["scraper_respect_robots"] = self._robots_var.get()
        save_config(self.config_data)

        # Propagate to research service if accessible via parent app
        app = self.master
        if hasattr(app, "research_service"):
            app.research_service.scraper_user_agent = self.config_data["scraper_user_agent"]
            app.research_service.scraper_respect_robots = self.config_data["scraper_respect_robots"]

        self._settings_status.config(text="Settings saved.", foreground="#4a9")

    # ─── Refresh ───

    def _refresh_all(self):
        self._load_metrics()
        self._load_whitelist()
        self._load_blacklist()
