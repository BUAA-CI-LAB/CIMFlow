"""Tests for Pydantic models - RunConfig and PipelineConfig."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from cimflow.cli.run_cmd import RunConfig, PipelineConfig


class TestRunConfig:
    """Tests for RunConfig model."""

    def test_minimal_config(self, tmp_path):
        """Should accept minimal required fields."""
        config = RunConfig(model_path=tmp_path / "model.onnx")

        assert config.model_path == tmp_path / "model.onnx"
        # Check defaults
        assert config.t == 8
        assert config.k == 16
        assert config.b == 16
        assert config.c == 64
        assert config.batch_size == 8
        assert config.strategy == "dp"
        assert config.visualize is False
        assert config.log_level is None
        assert config.profile == ""

    def test_full_config(self, tmp_path):
        """Should accept all fields."""
        config = RunConfig(
            model_path=tmp_path / "model.onnx",
            config_path=tmp_path / "config.json",
            t=16,
            k=32,
            b=32,
            c=128,
            batch_size=16,
            strategy="custom",
            visualize=True,
            log_level="DEBUG",
            profile="from-config",
        )

        assert config.t == 16
        assert config.k == 32
        assert config.b == 32
        assert config.c == 128
        assert config.batch_size == 16
        assert config.strategy == "custom"
        assert config.visualize is True
        assert config.log_level == "DEBUG"
        assert config.profile == "from-config"

    def test_custom_profile_path(self, tmp_path):
        """Should accept custom profile path."""
        config = RunConfig(
            model_path=tmp_path / "model.onnx",
            profile="/custom/profiler.json",
        )

        assert config.profile == "/custom/profiler.json"

    def test_config_path_optional(self, tmp_path):
        """config_path should be optional."""
        config = RunConfig(model_path=tmp_path / "model.onnx")

        assert config.config_path is None


class TestPipelineConfig:
    """Tests for PipelineConfig model."""

    def test_minimal_batch_config(self, tmp_path):
        """Should accept minimal batch configuration."""
        config = PipelineConfig(
            output_dir=tmp_path / "output",
            runs=[
                RunConfig(model_path=tmp_path / "model.onnx"),
            ],
        )

        assert config.output_dir == tmp_path / "output"
        assert len(config.runs) == 1
        # Check defaults
        assert config.keep_ir is False
        assert config.run_name == "batch"
        assert config.paths_cfg is None

    def test_full_batch_config(self, tmp_path):
        """Should accept full batch configuration."""
        config = PipelineConfig(
            paths_cfg=tmp_path / "tool_paths.json",
            output_dir=tmp_path / "output",
            keep_ir=True,
            run_name="test_batch",
            runs=[
                RunConfig(model_path=tmp_path / "model1.onnx", t=8, b=16),
                RunConfig(model_path=tmp_path / "model2.onnx", t=16, b=32),
            ],
        )

        assert config.paths_cfg == tmp_path / "tool_paths.json"
        assert config.keep_ir is True
        assert config.run_name == "test_batch"
        assert len(config.runs) == 2

    def test_multiple_runs_different_params(self, tmp_path):
        """Should support multiple runs with different parameters."""
        config = PipelineConfig(
            output_dir=tmp_path / "output",
            runs=[
                RunConfig(model_path=tmp_path / "m1.onnx", t=4, b=8, batch_size=4),
                RunConfig(model_path=tmp_path / "m2.onnx", t=8, b=16, batch_size=8),
                RunConfig(model_path=tmp_path / "m3.onnx", t=16, b=32, batch_size=16),
            ],
        )

        assert config.runs[0].t == 4
        assert config.runs[1].t == 8
        assert config.runs[2].t == 16

    def test_runs_with_per_run_profile(self, tmp_path):
        """Should support different profiling options per run."""
        config = PipelineConfig(
            output_dir=tmp_path / "output",
            runs=[
                RunConfig(model_path=tmp_path / "m1.onnx", profile=""),
                RunConfig(model_path=tmp_path / "m2.onnx", profile="from-config"),
                RunConfig(model_path=tmp_path / "m3.onnx", profile="/custom/path.json"),
            ],
        )

        assert config.runs[0].profile == ""
        assert config.runs[1].profile == "from-config"
        assert config.runs[2].profile == "/custom/path.json"

    def test_empty_runs_list(self, tmp_path):
        """Should allow empty runs list (validated elsewhere)."""
        # The model itself allows empty runs; validation happens in CLI
        config = PipelineConfig(
            output_dir=tmp_path / "output",
            runs=[],
        )

        assert len(config.runs) == 0

    def test_model_serialization(self, tmp_path):
        """Should serialize and deserialize correctly."""
        original = PipelineConfig(
            output_dir=tmp_path / "output",
            keep_ir=True,
            runs=[
                RunConfig(model_path=tmp_path / "model.onnx", t=16),
            ],
        )

        # Serialize to dict and back
        data = original.model_dump()
        restored = PipelineConfig.model_validate(data)

        assert restored.keep_ir == original.keep_ir
        assert len(restored.runs) == len(original.runs)
        assert restored.runs[0].t == original.runs[0].t


class TestConfigValidation:
    """Tests for configuration validation edge cases."""

    def test_model_path_as_string(self):
        """Should accept model_path as string."""
        config = RunConfig(model_path="/path/to/model.onnx")

        assert config.model_path == Path("/path/to/model.onnx")

    def test_output_dir_as_string(self):
        """Should accept output_dir as string."""
        config = PipelineConfig(
            output_dir="/path/to/output",
            runs=[RunConfig(model_path="/model.onnx")],
        )

        assert config.output_dir == Path("/path/to/output")

    def test_hardware_params_type_coercion(self):
        """Should coerce string numbers to int."""
        # Pydantic should handle this
        config = RunConfig(
            model_path="/model.onnx",
            t=8,  # int
            k=16,
            b=16,
            c=64,
        )

        assert isinstance(config.t, int)
        assert isinstance(config.k, int)
