"""Tests for GUI observable state, cost tracker, env manager, and event wiring."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mini_rag.gui.events import EventBus
from mini_rag.gui.state import ObservableState
from mini_rag.gui.cost_tracker import CostTracker


# ──────────────────────────────────────────────────────────
# ObservableState
# ──────────────────────────────────────────────────────────

class TestObservableState:
    """Test state field changes emit events correctly."""

    def test_field_change_emits_event(self):
        bus = EventBus()
        state = ObservableState(bus)
        received = []
        bus.on("state:operation", lambda d: received.append(d))
        state.operation = "searching"
        assert len(received) == 1
        assert received[0]["old"] == "idle"
        assert received[0]["new"] == "searching"

    def test_same_value_no_emit(self):
        bus = EventBus()
        state = ObservableState(bus)
        received = []
        bus.on("state:operation", lambda d: received.append(d))
        state.operation = "idle"  # same as default
        assert len(received) == 0

    def test_multiple_fields_independent(self):
        bus = EventBus()
        state = ObservableState(bus)
        ops = []
        hints = []
        bus.on("state:operation", lambda d: ops.append(d["new"]))
        bus.on("state:hint", lambda d: hints.append(d["new"]))
        state.operation = "indexing"
        state.hint = "Indexing..."
        assert ops == ["indexing"]
        assert hints == ["Indexing..."]

    def test_set_operation_clears_error(self):
        bus = EventBus()
        state = ObservableState(bus)
        state.error = "something broke"
        assert state.error == "something broke"
        state.set_operation("searching", "Looking...")
        assert state.error is None
        assert state.operation == "searching"
        assert state.hint == "Looking..."

    def test_list_field_always_emits(self):
        """Lists always emit because == comparison is unreliable for mutation."""
        bus = EventBus()
        state = ObservableState(bus)
        received = []
        bus.on("state:results", lambda d: received.append(True))
        state.results = []  # same empty list, but should still emit
        assert len(received) == 1

    def test_private_attrs_bypass_observation(self):
        bus = EventBus()
        state = ObservableState(bus)
        received = []
        bus.on("state:_internal", lambda d: received.append(d))
        state._internal = "test"
        assert len(received) == 0
        assert state._internal == "test"

    def test_no_bus_doesnt_crash(self):
        state = ObservableState()
        state.operation = "searching"  # should not raise
        assert state.operation == "searching"

    def test_set_bus_late(self):
        state = ObservableState()
        bus = EventBus()
        received = []
        bus.on("state:operation", lambda d: received.append(d))
        state.set_bus(bus)
        state.operation = "indexing"
        assert len(received) == 1


# ──────────────────────────────────────────────────────────
# CostTracker
# ──────────────────────────────────────────────────────────

class TestCostTracker:
    """Test token usage accumulation and cost calculation."""

    def test_accumulates_tokens(self):
        bus = EventBus()
        tracker = CostTracker(bus)
        updates = []
        bus.on("cost:updated", lambda d: updates.append(d))

        bus.emit("llm:usage", {"prompt_tokens": 100, "completion_tokens": 50})
        assert len(updates) == 1
        assert updates[0]["session_tokens_in"] == 100
        assert updates[0]["session_tokens_out"] == 50

        bus.emit("llm:usage", {"prompt_tokens": 200, "completion_tokens": 100})
        assert updates[1]["session_tokens_in"] == 300
        assert updates[1]["session_tokens_out"] == 150

    def test_cost_calculation(self):
        bus = EventBus()
        tracker = CostTracker(bus)
        tracker.cost_per_1m_input = 2.50
        tracker.cost_per_1m_output = 10.00

        updates = []
        bus.on("cost:updated", lambda d: updates.append(d))

        bus.emit("llm:usage", {"prompt_tokens": 1000, "completion_tokens": 500})
        cost = updates[0]["session_cost"]
        expected = (1000 * 2.50 / 1_000_000) + (500 * 10.00 / 1_000_000)
        assert abs(cost - expected) < 0.0001

    def test_zero_tokens_ignored(self):
        bus = EventBus()
        tracker = CostTracker(bus)
        updates = []
        bus.on("cost:updated", lambda d: updates.append(d))

        bus.emit("llm:usage", {"prompt_tokens": 0, "completion_tokens": 0})
        assert len(updates) == 0

    def test_reset(self):
        bus = EventBus()
        tracker = CostTracker(bus)
        bus.emit("llm:usage", {"prompt_tokens": 100, "completion_tokens": 50})
        assert tracker.session_tokens_in == 100

        updates = []
        bus.on("cost:updated", lambda d: updates.append(d))
        tracker.reset()
        assert tracker.session_tokens_in == 0
        assert tracker.session_cost == 0.0
        assert updates[-1]["session_cost"] == 0.0

    def test_settings_update_rates(self):
        bus = EventBus()
        tracker = CostTracker(bus)
        assert tracker.cost_per_1m_input == 0.0

        bus.emit("settings:changed", {"cost_per_1m_input": 5.0, "cost_per_1m_output": 15.0})
        assert tracker.cost_per_1m_input == 5.0
        assert tracker.cost_per_1m_output == 15.0

    def test_format_tokens(self):
        assert CostTracker.format_tokens(500) == "500"
        assert CostTracker.format_tokens(1500) == "1.5K"
        assert CostTracker.format_tokens(1_500_000) == "1.5M"

    def test_format_cost(self):
        assert CostTracker.format_cost(0) == "$0.00"
        assert CostTracker.format_cost(0.005) == "$0.0050"
        assert CostTracker.format_cost(1.50) == "$1.50"

    def test_local_endpoint_zero_cost(self):
        """Local endpoints should accumulate tokens but $0.00 cost."""
        bus = EventBus()
        tracker = CostTracker(bus)
        # Rates stay at 0.0 (default for local)

        updates = []
        bus.on("cost:updated", lambda d: updates.append(d))

        bus.emit("llm:usage", {"prompt_tokens": 1000, "completion_tokens": 500})
        assert updates[0]["session_cost"] == 0.0
        assert updates[0]["session_tokens_in"] == 1000


# ──────────────────────────────────────────────────────────
# EnvManager
# ──────────────────────────────────────────────────────────

class TestEnvManager:
    """Test .env file read/write and key masking."""

    def test_mask_key(self):
        from mini_rag.gui.env_manager import mask_key
        assert mask_key(None) == "(not set)"
        assert mask_key("") == "(not set)"
        assert mask_key("abc") == "••••"
        assert mask_key("sk-abc123456789") == "••••6789"

    def test_save_and_load(self):
        from mini_rag.gui import env_manager

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            # Patch the module-level constants
            with patch.object(env_manager, "ENV_FILE", env_file), \
                 patch.object(env_manager, "ENV_DIR", Path(tmpdir)):

                env_manager.save_env({
                    "TAVILY_API_KEY": "tvly-test123",
                    "LLM_API_KEY": "sk-test456",
                })

                loaded = env_manager.load_env()
                assert loaded["TAVILY_API_KEY"] == "tvly-test123"
                assert loaded["LLM_API_KEY"] == "sk-test456"

                # Check file permissions (0600)
                import stat
                mode = env_file.stat().st_mode
                assert mode & 0o777 == 0o600

    def test_preserves_comments(self):
        from mini_rag.gui import env_manager

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("# My config\nUNRELATED=foo\nTAVILY_API_KEY=old\n")

            with patch.object(env_manager, "ENV_FILE", env_file), \
                 patch.object(env_manager, "ENV_DIR", Path(tmpdir)):

                env_manager.save_env({"TAVILY_API_KEY": "new-key"})
                content = env_file.read_text()
                assert "# My config" in content
                assert "UNRELATED=foo" in content
                assert "TAVILY_API_KEY=new-key" in content
                assert "old" not in content

    def test_delete_key(self):
        from mini_rag.gui import env_manager

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("TAVILY_API_KEY=test123\nBRAVE_API_KEY=brave456\n")

            with patch.object(env_manager, "ENV_FILE", env_file), \
                 patch.object(env_manager, "ENV_DIR", Path(tmpdir)):

                # Save without TAVILY — it should be removed
                env_manager.save_env({"BRAVE_API_KEY": "brave456"})
                content = env_file.read_text()
                assert "TAVILY" not in content
                assert "BRAVE_API_KEY=brave456" in content

    def test_get_key_checks_environ_first(self):
        from mini_rag.gui import env_manager

        with patch.dict(os.environ, {"LLM_API_KEY": "from-env"}, clear=False):
            assert env_manager.get_key("LLM_API_KEY") == "from-env"

    def test_unmanaged_key_rejected(self):
        from mini_rag.gui import env_manager
        # Should log a warning but not crash
        env_manager.set_key("RANDOM_KEY", "value")


# ──────────────────────────────────────────────────────────
# Config Store
# ──────────────────────────────────────────────────────────

class TestConfigStore:
    """Test preset expansion and config management."""

    def test_presets_have_cost_rates(self):
        from mini_rag.gui.config_store import PRESETS
        for name, preset in PRESETS.items():
            assert "cost_per_1m_input" in preset, f"Preset {name} missing cost_per_1m_input"
            assert "cost_per_1m_output" in preset, f"Preset {name} missing cost_per_1m_output"
            assert "needs_api_key" in preset, f"Preset {name} missing needs_api_key"

    def test_apply_preset_copies_cost_rates(self):
        from mini_rag.gui.config_store import apply_preset
        config = {"preset": "lmstudio", "cost_per_1m_input": 0.0, "cost_per_1m_output": 0.0}
        apply_preset(config, "openai")
        assert config["cost_per_1m_input"] == 2.50
        assert config["cost_per_1m_output"] == 10.00
        assert config["needs_api_key"] is True

    def test_apply_preset_local_has_zero_cost(self):
        from mini_rag.gui.config_store import apply_preset
        config = {"preset": "openai", "cost_per_1m_input": 2.50, "cost_per_1m_output": 10.0}
        apply_preset(config, "lmstudio")
        assert config["cost_per_1m_input"] == 0.0
        assert config["needs_api_key"] is False

    def test_openai_preset_urls(self):
        from mini_rag.gui.config_store import PRESETS
        assert PRESETS["openai"]["llm_url"] == "https://api.openai.com/v1"
        assert PRESETS["openai"]["embedding_url"] == "https://api.openai.com/v1"

    def test_custom_remote_preset(self):
        from mini_rag.gui.config_store import PRESETS
        remote = PRESETS["custom-remote"]
        assert "example.com" in remote["llm_url"]
        assert remote["needs_api_key"] is True
        assert remote["cost_per_1m_input"] == 0.0  # self-hosted = free


# ──────────────────────────────────────────────────────────
# Event Wiring Integration
# ──────────────────────────────────────────────────────────

class TestEventWiring:
    """Test that state changes propagate through the event system."""

    def test_operation_change_reaches_subscribers(self):
        bus = EventBus()
        state = ObservableState(bus)
        operations = []
        bus.on("state:operation", lambda d: operations.append(d["new"]))

        state.set_operation("searching", "Looking...")
        state.set_operation("idle", "Done")

        assert operations == ["searching", "idle"]

    def test_cost_tracker_wired_to_settings(self):
        bus = EventBus()
        tracker = CostTracker(bus)

        # Simulate settings change from preferences dialog
        bus.emit("settings:changed", {
            "cost_per_1m_input": 0.15,
            "cost_per_1m_output": 0.60,
        })

        # Now emit usage — should use new rates
        updates = []
        bus.on("cost:updated", lambda d: updates.append(d))
        bus.emit("llm:usage", {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000})

        expected = 0.15 + 0.60
        assert abs(updates[0]["session_cost"] - expected) < 0.01

    def test_error_cleared_by_new_operation(self):
        bus = EventBus()
        state = ObservableState(bus)
        errors = []
        bus.on("state:error", lambda d: errors.append(d["new"]))

        state.error = "broken"
        state.set_operation("searching")  # should clear error

        assert errors == ["broken", None]
