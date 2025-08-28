#!/usr/bin/env python3
"""
Test script to validate all config examples are syntactically correct
and contain required fields for FSS-Mini-RAG.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml


def validate_config_structure(config: Dict[str, Any], config_name: str) -> List[str]:
    """Validate that config has required structure."""
    errors = []

    # Required sections
    required_sections = ["chunking", "streaming", "files", "embedding", "search"]
    for section in required_sections:
        if section not in config:
            errors.append(f"{config_name}: Missing required section '{section}'")

    # Validate chunking section
    if "chunking" in config:
        chunking = config["chunking"]
        required_chunking = ["max_size", "min_size", "strategy"]
        for field in required_chunking:
            if field not in chunking:
                errors.append(f"{config_name}: Missing chunking.{field}")

        # Validate types and ranges
        if "max_size" in chunking and not isinstance(chunking["max_size"], int):
            errors.append(f"{config_name}: chunking.max_size must be integer")
        if "min_size" in chunking and not isinstance(chunking["min_size"], int):
            errors.append(f"{config_name}: chunking.min_size must be integer")
        if "strategy" in chunking and chunking["strategy"] not in ["semantic", "fixed"]:
            errors.append(f"{config_name}: chunking.strategy must be 'semantic' or 'fixed'")

    # Validate embedding section
    if "embedding" in config:
        embedding = config["embedding"]
        if "preferred_method" in embedding:
            valid_methods = ["ollama", "ml", "hash", "auto"]
            if embedding["preferred_method"] not in valid_methods:
                errors.append(
                    f"{config_name}: embedding.preferred_method must be one of {valid_methods}"
                )

    # Validate LLM section (if present)
    if "llm" in config:
        llm = config["llm"]
        if "synthesis_temperature" in llm:
            temp = llm["synthesis_temperature"]
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 1:
                errors.append(
                    f"{config_name}: llm.synthesis_temperature must be number between 0-1"
                )

    return errors


def test_config_file(config_path: Path) -> bool:
    """Test a single config file."""
    print(f"Testing {config_path.name}...")

    try:
        # Test YAML parsing
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        if not config:
            print(f"  ❌ {config_path.name}: Empty or invalid YAML")
            return False

        # Test structure
        errors = validate_config_structure(config, config_path.name)

        if errors:
            print(f"  ❌ {config_path.name}: Structure errors:")
            for error in errors:
                print(f"     • {error}")
            return False

        print(f"  ✅ {config_path.name}: Valid")
        return True

    except yaml.YAMLError as e:
        print(f"  ❌ {config_path.name}: YAML parsing error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ {config_path.name}: Unexpected error: {e}")
        return False


def main():
    """Test all config examples."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    examples_dir = project_root / "examples"

    if not examples_dir.exists():
        print(f"❌ Examples directory not found: {examples_dir}")
        sys.exit(1)

    # Find all config files
    config_files = list(examples_dir.glob("config*.yaml"))

    if not config_files:
        print(f"❌ No config files found in {examples_dir}")
        sys.exit(1)

    print(f"🧪 Testing {len(config_files)} config files...\n")

    all_passed = True
    for config_file in sorted(config_files):
        passed = test_config_file(config_file)
        if not passed:
            all_passed = False

    print(f"\n{'='*50}")
    if all_passed:
        print("✅ All config files are valid!")
        print("\n💡 To use any config:")
        print("   cp examples/config-NAME.yaml /path/to/project/.mini-rag/config.yaml")
        sys.exit(0)
    else:
        print("❌ Some config files have issues - please fix before release")
        sys.exit(1)


if __name__ == "__main__":
    main()
