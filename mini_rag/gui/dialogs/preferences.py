"""Preferences dialog for endpoint and model configuration."""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict

from ..config_store import PRESETS
from ..events import EventBus


class PreferencesDialog(tk.Toplevel):
    """Settings dialog for embedding/LLM endpoints and profiles."""

    def __init__(self, parent, config: Dict[str, Any], event_bus: EventBus):
        super().__init__(parent)
        self.title("Preferences")
        self.config_data = dict(config)
        self.bus = event_bus
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 5}
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Preset selector
        ttk.Label(frame, text="Preset:").grid(row=0, column=0, sticky=tk.W, **pad)
        self.preset_var = tk.StringVar(value=self.config_data.get("preset", "lmstudio"))
        preset_names = list(PRESETS.keys()) + list(self.config_data.get("custom_presets", {}).keys())
        preset_combo = ttk.Combobox(frame, textvariable=self.preset_var, values=preset_names, width=20)
        preset_combo.grid(row=0, column=1, sticky=tk.W, **pad)
        preset_combo.bind("<<ComboboxSelected>>", self._on_preset_changed)

        # Embedding section
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=10)
        ttk.Label(frame, text="Embedding", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, **pad)

        ttk.Label(frame, text="URL:").grid(row=3, column=0, sticky=tk.W, **pad)
        self.emb_url_var = tk.StringVar(value=self.config_data.get("embedding_url", ""))
        ttk.Entry(frame, textvariable=self.emb_url_var, width=35).grid(row=3, column=1, **pad)

        ttk.Label(frame, text="Model:").grid(row=4, column=0, sticky=tk.W, **pad)
        self.emb_model_var = tk.StringVar(value=self.config_data.get("embedding_model", "auto"))
        ttk.Entry(frame, textvariable=self.emb_model_var, width=35).grid(row=4, column=1, **pad)

        ttk.Label(frame, text="Profile:").grid(row=5, column=0, sticky=tk.W, **pad)
        profile_frame = ttk.Frame(frame)
        profile_frame.grid(row=5, column=1, sticky=tk.W, **pad)
        self.profile_var = tk.StringVar(value=self.config_data.get("embedding_profile", "precision"))
        ttk.Radiobutton(profile_frame, text="Precision", variable=self.profile_var, value="precision").pack(side=tk.LEFT)
        ttk.Radiobutton(profile_frame, text="Conceptual", variable=self.profile_var, value="conceptual").pack(side=tk.LEFT, padx=10)

        # LLM section
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=10)
        ttk.Label(frame, text="LLM (Synthesis)", font=("", 10, "bold")).grid(row=7, column=0, sticky=tk.W, **pad)

        ttk.Label(frame, text="URL:").grid(row=8, column=0, sticky=tk.W, **pad)
        self.llm_url_var = tk.StringVar(value=self.config_data.get("llm_url", ""))
        ttk.Entry(frame, textvariable=self.llm_url_var, width=35).grid(row=8, column=1, **pad)

        ttk.Label(frame, text="Model:").grid(row=9, column=0, sticky=tk.W, **pad)
        self.llm_model_var = tk.StringVar(value=self.config_data.get("llm_model", "auto"))
        ttk.Entry(frame, textvariable=self.llm_model_var, width=35).grid(row=9, column=1, **pad)

        # Query expansion
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=10, column=0, columnspan=2, sticky=tk.EW, pady=10)
        self.expand_var = tk.BooleanVar(value=self.config_data.get("expand_queries", False))
        ttk.Checkbutton(frame, text="Enable query expansion (LLM)", variable=self.expand_var).grid(
            row=11, column=0, columnspan=2, sticky=tk.W, **pad
        )

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=12, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Save Custom", command=self._save_custom).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reset", command=self._reset).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.RIGHT, padx=5)

    def _on_preset_changed(self, event):
        preset_name = self.preset_var.get()
        if preset_name in PRESETS:
            preset = PRESETS[preset_name]
            self.emb_url_var.set(preset["embedding_url"])
            self.llm_url_var.set(preset["llm_url"])

    def _save_custom(self):
        name = f"custom_{len(self.config_data.get('custom_presets', {})) + 1}"
        custom = self.config_data.setdefault("custom_presets", {})
        custom[name] = {
            "embedding_url": self.emb_url_var.get(),
            "llm_url": self.llm_url_var.get(),
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

    def _on_ok(self):
        self.config_data["preset"] = self.preset_var.get()
        self.config_data["embedding_url"] = self.emb_url_var.get()
        self.config_data["embedding_model"] = self.emb_model_var.get()
        self.config_data["embedding_profile"] = self.profile_var.get()
        self.config_data["llm_url"] = self.llm_url_var.get()
        self.config_data["llm_model"] = self.llm_model_var.get()
        self.config_data["expand_queries"] = self.expand_var.get()
        self.bus.emit("settings:changed", self.config_data)
        self.destroy()
