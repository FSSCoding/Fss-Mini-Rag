"""Preferences dialog with tabbed layout: Endpoints, API Keys, Connection & Cost."""

import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict

from ..config_store import PRESETS
from ..events import EventBus
from ..services.model_discovery import discover_models
from ..env_manager import load_env, save_env, mask_key, get_key
from ..tooltip import ToolTip


class PreferencesDialog(tk.Toplevel):
    """Settings dialog for endpoints, API keys, and cost configuration."""

    def __init__(self, parent, config: Dict[str, Any], event_bus: EventBus):
        super().__init__(parent)
        self.title("Preferences")
        self.config_data = dict(config)
        self.bus = event_bus
        self.geometry("580x640")
        self.resizable(True, True)
        self.minsize(560, 580)
        self.transient(parent)
        self.grab_set()
        self._build()
        # Auto-refresh models when dialog opens
        self.after(200, self._refresh_models)

        # Track saved values for change detection
        self._saved_values = {
            "embedding_url": self.config_data.get("embedding_url", ""),
            "embedding_model": self.config_data.get("embedding_model", "auto"),
            "llm_url": self.config_data.get("llm_url", ""),
            "llm_model": self.config_data.get("llm_model", "auto"),
            "preset": self.config_data.get("preset", "lmstudio"),
        }
        # Monitor changes
        for var in [self.emb_url_var, self.emb_model_var, self.llm_url_var,
                    self.llm_model_var, self.preset_var]:
            var.trace_add("write", lambda *_: self._check_unsaved())

    def _build(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_endpoints_tab()
        self._build_keys_tab()
        self._build_connection_tab()

        # Bottom buttons — Save is primary action
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        save_custom_btn = ttk.Button(btn_frame, text="Save Custom Preset", command=self._save_custom)
        save_custom_btn.pack(side=tk.LEFT, padx=3)
        ToolTip(save_custom_btn, "Save current endpoint URLs and cost rates as a reusable preset")
        save_btn = ttk.Button(btn_frame, text="Save", command=self._on_save, style="Accent.TButton")
        save_btn.pack(side=tk.RIGHT, padx=3)
        ToolTip(save_btn, "Apply all changes and close")
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=3)
        ToolTip(cancel_btn, "Discard changes and close")

        self._save_status = ttk.Label(main, text="", foreground="#888888")
        self._save_status.pack(fill=tk.X, pady=(4, 0))

    # ─── Tab 1: Endpoints ───

    def _build_endpoints_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Endpoints")
        pad = {"padx": 8, "pady": 4}

        # Preset selector
        ttk.Label(tab, text="Preset:").grid(row=0, column=0, sticky=tk.W, **pad)
        self.preset_var = tk.StringVar(value=self.config_data.get("preset", "lmstudio"))
        preset_names = list(PRESETS.keys()) + list(self.config_data.get("custom_presets", {}).keys())
        preset_combo = ttk.Combobox(tab, textvariable=self.preset_var, values=preset_names, width=22)
        preset_combo.grid(row=0, column=1, sticky=tk.W, **pad)
        preset_combo.bind("<<ComboboxSelected>>", self._on_preset_changed)
        ToolTip(preset_combo, "Quick-fill endpoints from a known provider (LM Studio, vLLM, OpenAI, etc.)")

        # Embedding section
        ttk.Separator(tab, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=8)
        ttk.Label(tab, text="Embedding", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, **pad)
        ttk.Label(tab, text="Converts text into vectors for semantic search",
                  foreground="#888888", font=("", 8, "italic")).grid(row=2, column=1, columnspan=2, sticky=tk.W, **pad)

        ttk.Label(tab, text="URL:").grid(row=3, column=0, sticky=tk.W, **pad)
        self.emb_url_var = tk.StringVar(value=self.config_data.get("embedding_url", ""))
        emb_url_entry = ttk.Entry(tab, textvariable=self.emb_url_var, width=38)
        emb_url_entry.grid(row=3, column=1, **pad)
        ToolTip(emb_url_entry, "OpenAI-compatible embedding endpoint (e.g. http://localhost:1234/v1)")

        ttk.Label(tab, text="Model:").grid(row=4, column=0, sticky=tk.W, **pad)
        self.emb_model_var = tk.StringVar(value=self.config_data.get("embedding_model", "auto"))
        self.emb_model_combo = ttk.Combobox(tab, textvariable=self.emb_model_var, width=36)
        self.emb_model_combo.grid(row=4, column=1, **pad)
        ToolTip(self.emb_model_combo, "'auto' picks the first available embedding model from the server")

        ttk.Label(tab, text="Profile:").grid(row=5, column=0, sticky=tk.W, **pad)
        profile_frame = ttk.Frame(tab)
        profile_frame.grid(row=5, column=1, sticky=tk.W, **pad)
        self.profile_var = tk.StringVar(value=self.config_data.get("embedding_profile", "precision"))
        rb_precision = ttk.Radiobutton(profile_frame, text="Precision", variable=self.profile_var, value="precision")
        rb_precision.pack(side=tk.LEFT)
        rb_conceptual = ttk.Radiobutton(profile_frame, text="Conceptual", variable=self.profile_var, value="conceptual")
        rb_conceptual.pack(side=tk.LEFT, padx=10)
        ToolTip(rb_precision, "Exact keyword and code matching — best for technical/code search")
        ToolTip(rb_conceptual, "Broader semantic matching — best for natural language and research queries")

        # LLM section
        ttk.Separator(tab, orient=tk.HORIZONTAL).grid(row=6, column=0, columnspan=3, sticky=tk.EW, pady=8)
        ttk.Label(tab, text="LLM (Synthesis)", font=("", 10, "bold")).grid(row=7, column=0, sticky=tk.W, **pad)
        ttk.Label(tab, text="Generates answers, analysis, and research briefings",
                  foreground="#888888", font=("", 8, "italic")).grid(row=7, column=1, columnspan=2, sticky=tk.W, **pad)

        ttk.Label(tab, text="URL:").grid(row=8, column=0, sticky=tk.W, **pad)
        self.llm_url_var = tk.StringVar(value=self.config_data.get("llm_url", ""))
        llm_url_entry = ttk.Entry(tab, textvariable=self.llm_url_var, width=38)
        llm_url_entry.grid(row=8, column=1, **pad)
        ToolTip(llm_url_entry, "OpenAI-compatible chat completions endpoint")

        ttk.Label(tab, text="Model:").grid(row=9, column=0, sticky=tk.W, **pad)
        self.llm_model_var = tk.StringVar(value=self.config_data.get("llm_model", "auto"))
        self.llm_model_combo = ttk.Combobox(tab, textvariable=self.llm_model_var, width=36)
        self.llm_model_combo.grid(row=9, column=1, **pad)
        ToolTip(self.llm_model_combo, "'auto' picks the first available chat model from the server")

        # Query expansion
        ttk.Separator(tab, orient=tk.HORIZONTAL).grid(row=10, column=0, columnspan=3, sticky=tk.EW, pady=8)
        self.expand_var = tk.BooleanVar(value=self.config_data.get("expand_queries", False))
        expand_check = ttk.Checkbutton(tab, text="Enable query expansion (LLM)", variable=self.expand_var)
        expand_check.grid(row=11, column=0, columnspan=2, sticky=tk.W, **pad)
        ToolTip(expand_check, "Rewrites your search query using the LLM to find more relevant results (adds latency)")
        ttk.Label(tab, text="Uses an LLM call to rephrase queries before search — improves recall at the cost of speed",
                  foreground="#888888", font=("", 8, "italic")).grid(row=12, column=0, columnspan=3, sticky=tk.W, padx=28, pady=(0, 4))

        # Action buttons row
        action_frame = ttk.Frame(tab)
        action_frame.grid(row=13, column=0, columnspan=3, sticky=tk.W, **pad)

        refresh_btn = ttk.Button(action_frame, text="Refresh Models", command=self._refresh_models)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(refresh_btn, "Query both endpoints for available models")
        test_btn = ttk.Button(action_frame, text="Quick Test", command=self._quick_test_endpoints)
        test_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(test_btn, "Ping both endpoints to check connectivity")

        self.endpoint_test_label = ttk.Label(tab, text="", foreground="#888888")
        self.endpoint_test_label.grid(row=14, column=0, columnspan=3, sticky=tk.W, **pad)

    # ─── Tab 2: API Keys ───

    def _build_keys_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="API Keys")

        ttk.Label(
            tab, text="Keys are stored in ~/.config/fss-mini-rag/.env — never in project files",
            foreground="#888888", font=("", 9, "italic"),
        ).pack(anchor=tk.W, pady=(0, 10))

        env = load_env()
        self._key_vars = {}
        self._key_entries = {}

        keys = [
            ("LLM_API_KEY", "LLM / OpenAI API Key",
             "Used for chat completions and synthesis — required for cloud LLM providers"),
            ("EMBEDDING_API_KEY", "Embedding API Key",
             "Separate key for embedding endpoint — leave blank to use the LLM key"),
            ("OPENAI_API_KEY", "OpenAI API Key (fallback)",
             "Fallback if LLM_API_KEY is not set — used by some SDKs automatically"),
            ("TAVILY_API_KEY", "Tavily Search API Key",
             "Enables Tavily as a web search engine for deep research (tavily.com)"),
            ("BRAVE_API_KEY", "Brave Search API Key",
             "Enables Brave Search for web research (brave.com/search/api)"),
            ("SERPER_API_KEY", "Serper (Google) API Key",
             "Enables Serper (Google search) for web research (serper.dev)"),
        ]

        for key_name, label, description in keys:
            frame = ttk.LabelFrame(tab, text=label, padding=5)
            frame.pack(fill=tk.X, pady=3)

            current = env.get(key_name, "")
            var = tk.StringVar(value=current)
            self._key_vars[key_name] = var

            entry = ttk.Entry(frame, textvariable=var, show="*", width=45)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            self._key_entries[key_name] = entry
            ToolTip(entry, description)

            # Show/Hide toggle
            show_var = tk.BooleanVar(value=False)
            def _toggle(e=entry, sv=show_var):
                e.config(show="" if sv.get() else "*")
            ttk.Checkbutton(frame, text="Show", variable=show_var, command=_toggle).pack(side=tk.RIGHT)

            # Status indicator
            status = mask_key(current) if current else "(not set)"
            ttk.Label(frame, text=status, foreground="#888888", font=("", 8)).pack(side=tk.RIGHT, padx=5)

    # ─── Tab 3: Connection & Cost ───

    def _build_connection_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Connection & Cost")

        # Connection test section
        test_frame = ttk.LabelFrame(tab, text="Connection Test", padding=8)
        test_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            test_frame,
            text="Runs a 3-step round-trip test: list models, generate an embedding, and call the LLM.",
            foreground="#888888", font=("", 8, "italic"),
        ).pack(anchor=tk.W, pady=(0, 6))

        test_conn_btn = ttk.Button(
            test_frame, text="Test Connection", command=self._test_connections,
            style="Accent.TButton",
        )
        test_conn_btn.pack(anchor=tk.W, pady=(0, 8))
        ToolTip(test_conn_btn, "Runs all 3 tests sequentially — takes ~10 seconds")

        self.test_step1 = ttk.Label(test_frame, text="1. Models: not tested", foreground="#888888")
        self.test_step1.pack(anchor=tk.W, padx=10)
        self.test_step2 = ttk.Label(test_frame, text="2. Embedding: not tested", foreground="#888888")
        self.test_step2.pack(anchor=tk.W, padx=10)
        self.test_step3 = ttk.Label(test_frame, text="3. LLM: not tested", foreground="#888888")
        self.test_step3.pack(anchor=tk.W, padx=10)

        # Cost rates section
        cost_frame = ttk.LabelFrame(tab, text="Cost Tracking", padding=8)
        cost_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            cost_frame,
            text="Token pricing for estimating API costs. Set both to 0 for local/free endpoints.",
            foreground="#888888", font=("", 8, "italic"),
        ).pack(anchor=tk.W, pady=(0, 6))

        row = ttk.Frame(cost_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Input:  $").pack(side=tk.LEFT)
        self.cost_input_var = tk.StringVar(value=str(self.config_data.get("cost_per_1m_input", 0.0)))
        cost_in = ttk.Entry(row, textvariable=self.cost_input_var, width=10)
        cost_in.pack(side=tk.LEFT, padx=(0, 20))
        ToolTip(cost_in, "Cost per 1 million input tokens (prompt tokens sent to the API)")
        ttk.Label(row, text="Output: $").pack(side=tk.LEFT)
        self.cost_output_var = tk.StringVar(value=str(self.config_data.get("cost_per_1m_output", 0.0)))
        cost_out = ttk.Entry(row, textvariable=self.cost_output_var, width=10)
        cost_out.pack(side=tk.LEFT)
        ToolTip(cost_out, "Cost per 1 million output tokens (completion tokens from the API)")

        ttk.Label(
            cost_frame, text="Rates update automatically when you switch presets.",
            foreground="#888888", font=("", 8, "italic"),
        ).pack(anchor=tk.W, pady=(4, 0))

        # Session stats
        stats_frame = ttk.LabelFrame(tab, text="Session Statistics", padding=8)
        stats_frame.pack(fill=tk.X)

        ttk.Label(
            stats_frame,
            text="Tracks all API calls made during this session.",
            foreground="#888888", font=("", 8, "italic"),
        ).pack(anchor=tk.W, pady=(0, 4))

        self.stats_label = ttk.Label(stats_frame, text="No API calls this session", foreground="#888888")
        self.stats_label.pack(anchor=tk.W)

        self.bus.on("cost:updated", lambda d: self.after(0, lambda: self._update_stats(d)))

        reset_session_btn = ttk.Button(stats_frame, text="Reset Session", command=self._reset_session)
        reset_session_btn.pack(anchor=tk.W, pady=(5, 0))
        ToolTip(reset_session_btn, "Clear session token counts and cost — does not affect API keys or settings")

        # Reset to defaults (danger zone)
        ttk.Separator(tab, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(tab, text="Danger Zone", font=("", 9, "bold"), foreground="#cc3333").pack(anchor=tk.W, pady=(0, 4))
        reset_btn = tk.Button(
            tab, text="Reset All to Defaults", command=self._reset_to_defaults,
            fg="white", bg="#cc3333", activebackground="#aa2222",
            relief=tk.RAISED, padx=10, pady=4,
        )
        reset_btn.pack(anchor=tk.W)
        ToolTip(reset_btn, "Clears all endpoints, models, cost rates, and deletes stored API keys")
        ttk.Label(
            tab, text="Resets endpoints, models, cost rates, and removes all API keys from the local keystore.",
            foreground="#888888", font=("", 8, "italic"),
        ).pack(anchor=tk.W, pady=(2, 0))

    # ─── Handlers ───

    def _quick_test_endpoints(self):
        """Quick curl-style test of both endpoints from the Endpoints tab."""
        self.endpoint_test_label.config(text="Testing...", foreground="#888888")

        def _run():
            import requests
            api_key = self._key_vars.get("LLM_API_KEY", tk.StringVar()).get() or get_key("LLM_API_KEY") or get_key("OPENAI_API_KEY")
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            results = []

            # Test embedding endpoint
            emb_url = self.emb_url_var.get().rstrip("/")
            try:
                r = requests.get(f"{emb_url}/models" if emb_url.endswith("/v1") else emb_url,
                                 headers=headers, timeout=5)
                results.append(f"Embed: {'OK' if r.status_code == 200 else f'HTTP {r.status_code}'}")
            except Exception as e:
                results.append(f"Embed: FAIL ({e})")

            # Test LLM endpoint
            llm_url = self.llm_url_var.get().rstrip("/")
            try:
                r = requests.get(f"{llm_url}/models", headers=headers, timeout=5)
                if r.status_code == 200:
                    count = len(r.json().get("data", []))
                    results.append(f"LLM: OK ({count} models)")
                else:
                    results.append(f"LLM: HTTP {r.status_code}")
            except Exception as e:
                results.append(f"LLM: FAIL ({e})")

            self.after(0, lambda: self.endpoint_test_label.config(
                text=" | ".join(results),
                foreground="green" if all("OK" in r for r in results) else "red",
            ))

        threading.Thread(target=_run, daemon=True).start()

    def _on_preset_changed(self, event):
        preset_name = self.preset_var.get()
        if preset_name in PRESETS:
            preset = PRESETS[preset_name]
            self.emb_url_var.set(preset["embedding_url"])
            self.llm_url_var.set(preset["llm_url"])
            self.cost_input_var.set(str(preset.get("cost_per_1m_input", 0.0)))
            self.cost_output_var.set(str(preset.get("cost_per_1m_output", 0.0)))

    def _refresh_models(self):
        def _discover():
            emb_url = self.emb_url_var.get()
            llm_url = self.llm_url_var.get()
            api_key = self._key_vars.get("LLM_API_KEY", tk.StringVar()).get() or get_key("LLM_API_KEY")
            emb_models = discover_models(emb_url, api_key=api_key)
            llm_models = discover_models(llm_url, api_key=api_key) if llm_url != emb_url else emb_models
            all_emb = ["auto"] + emb_models.get("embedding", [])
            all_llm = ["auto"] + (llm_models.get("llm", []) or llm_models.get("embedding", []))
            self.after(0, lambda: self._apply_models(all_emb, all_llm))

        threading.Thread(target=_discover, daemon=True).start()

    def _apply_models(self, emb_models, llm_models):
        self.emb_model_combo["values"] = emb_models
        self.llm_model_combo["values"] = llm_models
        count = len(emb_models) + len(llm_models) - 2
        self.test_step1.config(text=f"1. Models: found {count}", foreground="green")

    def _test_connections(self):
        """Full round-trip connection test in background thread."""
        self.test_step1.config(text="1. Models: testing...", foreground="#888888")
        self.test_step2.config(text="2. Embedding: waiting...", foreground="#888888")
        self.test_step3.config(text="3. LLM: waiting...", foreground="#888888")

        def _run():
            import requests

            emb_url = self.emb_url_var.get().rstrip("/")
            llm_url = self.llm_url_var.get().rstrip("/")
            api_key = self._key_vars.get("LLM_API_KEY", tk.StringVar()).get() or get_key("LLM_API_KEY") or get_key("OPENAI_API_KEY")

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            # Step 1: List models
            try:
                r = requests.get(f"{llm_url}/models", headers=headers, timeout=10)
                if r.status_code == 200:
                    models = r.json().get("data", [])
                    count = len(models)
                    self.after(0, lambda: self.test_step1.config(
                        text=f"1. Models: {count} available", foreground="green"
                    ))
                else:
                    self.after(0, lambda: self.test_step1.config(
                        text=f"1. Models: HTTP {r.status_code}", foreground="red"
                    ))
            except Exception as e:
                self.after(0, lambda: self.test_step1.config(
                    text=f"1. Models: {e}", foreground="red"
                ))

            # Step 2: Test embedding
            self.after(0, lambda: self.test_step2.config(text="2. Embedding: testing...", foreground="#888888"))
            try:
                emb_model = self.emb_model_var.get()
                if emb_url.endswith("/v1"):
                    r = requests.post(
                        f"{emb_url}/embeddings", headers=headers,
                        json={"model": emb_model if emb_model != "auto" else "default", "input": "test embedding"},
                        timeout=15,
                    )
                else:
                    r = requests.post(emb_url, json={"text": "test embedding"}, timeout=15)

                if r.status_code == 200:
                    data = r.json()
                    dim = "?"
                    if "data" in data and data["data"]:
                        dim = len(data["data"][0].get("embedding", []))
                    self.after(0, lambda: self.test_step2.config(
                        text=f"2. Embedding: OK (dim={dim})", foreground="green"
                    ))
                else:
                    self.after(0, lambda: self.test_step2.config(
                        text=f"2. Embedding: HTTP {r.status_code}", foreground="red"
                    ))
            except Exception as e:
                self.after(0, lambda: self.test_step2.config(
                    text=f"2. Embedding: {e}", foreground="red"
                ))

            # Step 3: Test LLM completion
            self.after(0, lambda: self.test_step3.config(text="3. LLM: testing...", foreground="#888888"))
            try:
                llm_model = self.llm_model_var.get()
                r = requests.post(
                    f"{llm_url}/chat/completions", headers=headers,
                    json={
                        "model": llm_model if llm_model != "auto" else "default",
                        "messages": [{"role": "user", "content": "What is 2+2? Reply with just the number."}],
                        "max_tokens": 10,
                        "temperature": 0,
                    },
                    timeout=30,
                )
                if r.status_code == 200:
                    data = r.json()
                    reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()[:50]
                    usage = data.get("usage", {})
                    tok = usage.get("total_tokens", "?")
                    self.after(0, lambda: self.test_step3.config(
                        text=f"3. LLM: \"{reply}\" ({tok} tokens)", foreground="green"
                    ))
                else:
                    self.after(0, lambda: self.test_step3.config(
                        text=f"3. LLM: HTTP {r.status_code}", foreground="red"
                    ))
            except Exception as e:
                self.after(0, lambda: self.test_step3.config(
                    text=f"3. LLM: {e}", foreground="red"
                ))

        threading.Thread(target=_run, daemon=True).start()

    def _update_stats(self, data):
        tok_in = data.get("session_tokens_in", 0)
        tok_out = data.get("session_tokens_out", 0)
        cost = data.get("session_cost", 0.0)
        queries = data.get("query_count", 0)
        cost_str = f"${cost:.4f}" if cost < 1 else f"${cost:.2f}"
        self.stats_label.config(
            text=f"{queries} queries | {tok_in:,} in + {tok_out:,} out tokens | {cost_str}",
            foreground="" if cost > 0 else "#888888",
        )

    def _reset_session(self):
        self.bus.emit("cost:reset", {})
        self.stats_label.config(text="Session reset", foreground="#888888")

    def _save_custom(self):
        name = f"custom_{len(self.config_data.get('custom_presets', {})) + 1}"
        custom = self.config_data.setdefault("custom_presets", {})
        custom[name] = {
            "embedding_url": self.emb_url_var.get(),
            "llm_url": self.llm_url_var.get(),
            "needs_api_key": bool(self._key_vars.get("LLM_API_KEY", tk.StringVar()).get()),
            "cost_per_1m_input": float(self.cost_input_var.get() or 0),
            "cost_per_1m_output": float(self.cost_output_var.get() or 0),
        }
        self.preset_var.set(name)

    def _reset(self):
        self.emb_url_var.set("http://localhost:1234/v1")
        self.llm_url_var.set("http://localhost:1234/v1")
        self.emb_model_var.set("auto")
        self.llm_model_var.set("auto")
        self.profile_var.set("precision")
        self.expand_var.set(False)
        self.preset_var.set("lmstudio")
        self.cost_input_var.set("0.0")
        self.cost_output_var.set("0.0")

    def _check_unsaved(self):
        """Update save status label when field values differ from saved."""
        current = {
            "embedding_url": self.emb_url_var.get(),
            "embedding_model": self.emb_model_var.get(),
            "llm_url": self.llm_url_var.get(),
            "llm_model": self.llm_model_var.get(),
            "preset": self.preset_var.get(),
        }
        has_changes = any(current[k] != self._saved_values.get(k) for k in current)
        if has_changes:
            self._save_status.config(text="Unsaved changes", foreground="orange")
        else:
            self._save_status.config(text="")

    def _on_save(self):
        """Save all settings — endpoints, models, keys, cost rates."""
        # Save endpoint config
        self.config_data["preset"] = self.preset_var.get()
        self.config_data["embedding_url"] = self.emb_url_var.get()
        self.config_data["embedding_model"] = self.emb_model_var.get()
        self.config_data["embedding_profile"] = self.profile_var.get()
        self.config_data["llm_url"] = self.llm_url_var.get()
        self.config_data["llm_model"] = self.llm_model_var.get()
        self.config_data["expand_queries"] = self.expand_var.get()
        self.config_data["cost_per_1m_input"] = float(self.cost_input_var.get() or 0)
        self.config_data["cost_per_1m_output"] = float(self.cost_output_var.get() or 0)

        # Save API keys to .env (never to gui.json)
        keys = {}
        for key_name, var in self._key_vars.items():
            value = var.get().strip()
            if value:
                keys[key_name] = value
        if keys:
            save_env(keys)

        self.bus.emit("settings:changed", self.config_data)

        # Update saved values snapshot so change detection resets
        self._saved_values = {
            "embedding_url": self.emb_url_var.get(),
            "embedding_model": self.emb_model_var.get(),
            "llm_url": self.llm_url_var.get(),
            "llm_model": self.llm_model_var.get(),
            "preset": self.preset_var.get(),
        }

        # Confirm to user
        self._save_status.config(
            text="Settings saved successfully",
            foreground="green",
        )
        self.after(3000, lambda: self._save_status.config(text=""))

    def _reset_to_defaults(self):
        """Reset ALL settings to factory defaults. Warns about key deletion."""
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Reset to Defaults",
            "This will reset all endpoints, models, and cost rates to defaults.\n\n"
            "API keys stored in .env will be DELETED from our system.\n"
            "(Your keys are not deleted from any other system.)\n\n"
            "Continue?",
            icon="warning",
        ):
            return

        # Reset endpoints and models
        self._reset()

        # Delete managed keys from .env
        from .env_manager import load_env
        env = load_env()
        if env:
            save_env({})  # Write empty — removes all managed keys

        # Clear key fields in UI
        for var in self._key_vars.values():
            var.set("")

        self._save_status.config(text="Reset to defaults", foreground="orange")
