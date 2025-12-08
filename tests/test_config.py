"""Tests for config module - path resolution and configuration loading."""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from cimflow.config import (
    expand_path,
    resolve_config_path,
    load_global_paths,
    validate_hardware_params,
    GlobalPaths,
    DEFAULT_GLOBAL_CONFIG_PATH,
)


class TestExpandPath:
    """Tests for expand_path function."""

    def test_expands_tilde(self, tmp_path):
        """Should expand ~ to user home directory."""
        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            result = expand_path("~/test/file.txt")
            assert str(result).startswith(str(tmp_path))
            assert "test/file.txt" in str(result)

    def test_resolves_relative_path_with_base_dir(self, tmp_path):
        """Should resolve relative path from base_dir."""
        base = tmp_path / "base"
        base.mkdir()

        result = expand_path("subdir/file.txt", base_dir=base)
        assert result == (base / "subdir/file.txt").resolve()

    def test_resolves_relative_path_without_base_dir(self):
        """Should resolve relative path from CWD when no base_dir."""
        result = expand_path("relative/path.txt")
        assert result == (Path.cwd() / "relative/path.txt").resolve()

    def test_absolute_path_unchanged(self, tmp_path):
        """Should keep absolute paths absolute."""
        abs_path = tmp_path / "absolute/path.txt"
        result = expand_path(str(abs_path))
        assert result == abs_path.resolve()

    def test_absolute_path_ignores_base_dir(self, tmp_path):
        """Absolute path should ignore base_dir."""
        abs_path = tmp_path / "absolute.txt"
        base = tmp_path / "base"
        base.mkdir()

        result = expand_path(str(abs_path), base_dir=base)
        assert result == abs_path.resolve()


class TestResolveConfigPath:
    """Tests for resolve_config_path function."""

    def test_finds_existing_config(self, tmp_path):
        """Should find config file with matching T and B."""
        config_file = tmp_path / "config-mg8-b16.json"
        config_file.write_text("{}")

        result = resolve_config_path(tmp_path, t=8, b=16)
        assert result == config_file

    def test_raises_for_missing_config(self, tmp_path):
        """Should raise FileNotFoundError for missing config."""
        with pytest.raises(FileNotFoundError) as exc_info:
            resolve_config_path(tmp_path, t=8, b=16)

        assert "config-mg8-b16.json" in str(exc_info.value)

    def test_lists_available_configs_in_error(self, tmp_path):
        """Error message should list available configs."""
        # Create some configs
        (tmp_path / "config-mg4-b8.json").write_text("{}")
        (tmp_path / "config-mg16-b32.json").write_text("{}")

        with pytest.raises(FileNotFoundError) as exc_info:
            resolve_config_path(tmp_path, t=8, b=16)

        error_msg = str(exc_info.value)
        assert "config-mg4-b8.json" in error_msg
        assert "config-mg16-b32.json" in error_msg
        assert "Available configs" in error_msg

    def test_different_t_b_combinations(self, tmp_path):
        """Should handle various T and B values."""
        test_cases = [(4, 8), (8, 16), (16, 32), (32, 64)]

        for t, b in test_cases:
            config_file = tmp_path / f"config-mg{t}-b{b}.json"
            config_file.write_text("{}")

            result = resolve_config_path(tmp_path, t=t, b=b)
            assert result == config_file


class TestGlobalPaths:
    """Tests for GlobalPaths Pydantic model."""

    def test_valid_config(self, tmp_path):
        """Should validate correct configuration."""
        config_dir = tmp_path / "configs"
        config_dir.mkdir()

        paths = GlobalPaths(
            config_dir=config_dir,
            compiler_bin="cim-compiler",
            simulator_bin="cim-simulator",
        )

        assert paths.config_dir == config_dir
        assert paths.compiler_bin == "cim-compiler"
        assert paths.simulator_bin == "cim-simulator"
        assert paths.profiler_cfg is None

    def test_validates_config_dir_exists(self, tmp_path):
        """Should reject non-existent config_dir."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            GlobalPaths(
                config_dir=tmp_path / "nonexistent",
                compiler_bin="cim-compiler",
                simulator_bin="cim-simulator",
            )

        assert "does not exist" in str(exc_info.value)

    def test_optional_profiler_cfg(self, tmp_path):
        """Should allow None for profiler_cfg."""
        config_dir = tmp_path / "configs"
        config_dir.mkdir()

        paths = GlobalPaths(
            config_dir=config_dir,
            profiler_cfg=None,
        )

        assert paths.profiler_cfg is None

    def test_validates_profiler_cfg_exists(self, tmp_path):
        """Should reject non-existent profiler_cfg when provided."""
        from pydantic import ValidationError

        config_dir = tmp_path / "configs"
        config_dir.mkdir()

        with pytest.raises(ValidationError):
            GlobalPaths(
                config_dir=config_dir,
                profiler_cfg=tmp_path / "nonexistent.json",
            )


class TestLoadGlobalPaths:
    """Tests for load_global_paths function."""

    def test_loads_valid_config(self, tmp_path):
        """Should load valid tool_paths.json."""
        config_dir = tmp_path / "hw_configs"
        config_dir.mkdir()

        tool_paths = tmp_path / "tool_paths.json"
        tool_paths.write_text(json.dumps({
            "config_dir": str(config_dir),
            "compiler_bin": "cim-compiler",
            "simulator_bin": "cim-simulator",
        }))

        paths = load_global_paths(tool_paths)

        assert paths.config_dir == config_dir
        assert paths.compiler_bin == "cim-compiler"

    def test_raises_for_missing_file(self, tmp_path):
        """Should raise FileNotFoundError for missing config."""
        with pytest.raises(FileNotFoundError):
            load_global_paths(tmp_path / "nonexistent.json")

    def test_expands_relative_paths(self, tmp_path):
        """Should expand relative paths relative to config file."""
        config_dir = tmp_path / "hw_configs"
        config_dir.mkdir()

        tool_paths = tmp_path / "tool_paths.json"
        tool_paths.write_text(json.dumps({
            "config_dir": "hw_configs",  # Relative path
            "compiler_bin": "cim-compiler",
            "simulator_bin": "cim-simulator",
        }))

        paths = load_global_paths(tool_paths)

        # Should resolve relative to tool_paths.json location
        assert paths.config_dir == config_dir

    def test_expands_tilde_in_paths(self, tmp_path):
        """Should expand ~ in path values."""
        # Create a config with tilde path
        tool_paths = tmp_path / "tool_paths.json"

        # Create actual directory structure
        home_configs = tmp_path / "home_configs"
        home_configs.mkdir()

        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            tool_paths.write_text(json.dumps({
                "config_dir": "~/home_configs",
                "compiler_bin": "cim-compiler",
                "simulator_bin": "cim-simulator",
            }))

            paths = load_global_paths(tool_paths)
            assert paths.config_dir == home_configs

    def test_handles_path_style_simulator_bin(self, tmp_path):
        """Should expand path-style simulator_bin."""
        config_dir = tmp_path / "configs"
        config_dir.mkdir()

        sim_bin = tmp_path / "build" / "simulator"
        sim_bin.parent.mkdir()
        sim_bin.touch()

        tool_paths = tmp_path / "tool_paths.json"
        tool_paths.write_text(json.dumps({
            "config_dir": str(config_dir),
            "compiler_bin": "cim-compiler",
            "simulator_bin": "./build/simulator",  # Relative path
        }))

        paths = load_global_paths(tool_paths)

        # Should expand to absolute path
        assert Path(paths.simulator_bin).is_absolute()

    def test_default_path_used_when_none(self):
        """Should use DEFAULT_GLOBAL_CONFIG_PATH when no path given."""
        from pydantic import ValidationError

        # This test verifies the default path logic
        if not DEFAULT_GLOBAL_CONFIG_PATH.exists():
            # No config file - should raise FileNotFoundError
            with pytest.raises(FileNotFoundError):
                load_global_paths(None)
        else:
            # Config file exists - should either:
            # 1. Load successfully if paths are valid
            # 2. Raise ValidationError if paths in config don't exist
            # Both are acceptable - what matters is it reads the right file
            try:
                paths = load_global_paths(None)
                assert isinstance(paths, GlobalPaths)
            except ValidationError as e:
                # ValidationError means the file was read but paths don't exist
                # This is expected in CI where submodules aren't cloned
                assert "does not exist" in str(e)


class TestValidateHardwareParams:
    """Tests for validate_hardware_params function."""

    def _create_config(self, tmp_path, t: int, b: int) -> Path:
        """Helper to create a valid hardware config file."""
        config = {
            "chip_config": {
                "core_config": {
                    "cim_unit_config": {
                        "macro_group_size": t
                    }
                },
                "network_config": {
                    "bus_width_byte": b
                }
            }
        }
        config_path = tmp_path / f"config-mg{t}-b{b}.json"
        config_path.write_text(json.dumps(config))
        return config_path

    def test_valid_params_match(self, tmp_path):
        """Should pass when T/B match config."""
        config_path = self._create_config(tmp_path, t=8, b=16)
        result = validate_hardware_params(t=8, b=16, config_path=config_path)
        assert result is True

    def test_t_mismatch_exits(self, tmp_path):
        """Should exit when T doesn't match."""
        import typer
        config_path = self._create_config(tmp_path, t=8, b=16)

        with pytest.raises(typer.Exit):
            validate_hardware_params(t=16, b=16, config_path=config_path)

    def test_b_mismatch_exits(self, tmp_path):
        """Should exit when B doesn't match."""
        import typer
        config_path = self._create_config(tmp_path, t=8, b=16)

        with pytest.raises(typer.Exit):
            validate_hardware_params(t=8, b=32, config_path=config_path)

    def test_missing_config_exits(self, tmp_path):
        """Should exit when config file doesn't exist."""
        import typer

        with pytest.raises(typer.Exit):
            validate_hardware_params(t=8, b=16, config_path=tmp_path / "nonexistent.json")

    def test_invalid_json_exits(self, tmp_path):
        """Should exit when config file is invalid JSON."""
        import typer
        config_path = tmp_path / "invalid.json"
        config_path.write_text("{ invalid json }")

        with pytest.raises(typer.Exit):
            validate_hardware_params(t=8, b=16, config_path=config_path)

    def test_missing_macro_group_size_exits(self, tmp_path):
        """Should exit when macro_group_size is missing."""
        import typer
        config = {
            "chip_config": {
                "core_config": {
                    "cim_unit_config": {}  # Missing macro_group_size
                },
                "network_config": {
                    "bus_width_byte": 16
                }
            }
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config))

        with pytest.raises(typer.Exit):
            validate_hardware_params(t=8, b=16, config_path=config_path)

    def test_missing_bus_width_exits(self, tmp_path):
        """Should exit when bus_width_byte is missing."""
        import typer
        config = {
            "chip_config": {
                "core_config": {
                    "cim_unit_config": {
                        "macro_group_size": 8
                    }
                },
                "network_config": {}  # Missing bus_width_byte
            }
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config))

        with pytest.raises(typer.Exit):
            validate_hardware_params(t=8, b=16, config_path=config_path)

    def test_various_t_b_combinations(self, tmp_path):
        """Should work with various valid T/B combinations."""
        test_cases = [(4, 8), (8, 16), (12, 16), (16, 32)]

        for t, b in test_cases:
            config_path = self._create_config(tmp_path, t=t, b=b)
            result = validate_hardware_params(t=t, b=b, config_path=config_path)
            assert result is True
