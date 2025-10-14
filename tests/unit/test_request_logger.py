"""Tests for request logging functionality."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from aws_mcp_server.request_logger import RequestLogger


class TestRequestLogger:
    """Test suite for RequestLogger."""

    def test_initialization(self, tmp_path):
        """Test logger initialization."""
        log_file = tmp_path / "test.log"
        logger = RequestLogger(str(log_file))
        
        assert logger.log_file == log_file
        assert log_file.parent.exists()

    def test_log_request_creates_file(self, tmp_path):
        """Test that logging creates the log file."""
        log_file = tmp_path / "test.log"
        logger = RequestLogger(str(log_file))
        
        logger.log_request(
            tool_name="test_tool",
            input_params={"param1": "value1"},
            output={"result": "success"},
            status="success",
            duration_ms=123.45,
        )
        
        assert log_file.exists()

    def test_log_request_format(self, tmp_path):
        """Test that log entries are in correct JSON format."""
        log_file = tmp_path / "test.log"
        logger = RequestLogger(str(log_file))
        
        logger.log_request(
            tool_name="test_tool",
            input_params={"param1": "value1", "param2": 42},
            output={"result": "success", "data": [1, 2, 3]},
            status="success",
            duration_ms=123.45,
            error=None,
            metadata={"key": "value"},
        )
        
        # Read and parse the log entry
        with open(log_file, "r", encoding="utf-8") as f:
            line = f.readline()
            entry = json.loads(line)
        
        # Verify structure
        assert entry["event_type"] == "mcp_tool_call"
        assert entry["tool_name"] == "test_tool"
        assert entry["input"]["param1"] == "value1"
        assert entry["input"]["param2"] == 42
        assert entry["output"]["result"] == "success"
        assert entry["output"]["data"] == [1, 2, 3]
        assert entry["status"] == "success"
        assert entry["duration_ms"] == 123.45
        assert entry["error"] is None
        assert entry["metadata"]["key"] == "value"
        assert "timestamp" in entry
        assert entry["timestamp"].endswith("Z")

    def test_log_request_with_error(self, tmp_path):
        """Test logging with error status."""
        log_file = tmp_path / "test.log"
        logger = RequestLogger(str(log_file))
        
        logger.log_request(
            tool_name="test_tool",
            input_params={"command": "invalid"},
            output={"error": "Command failed"},
            status="error",
            duration_ms=50.0,
            error="Command validation error",
        )
        
        with open(log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        
        assert entry["status"] == "error"
        assert entry["error"] == "Command validation error"

    def test_multiple_log_entries(self, tmp_path):
        """Test multiple log entries in JSONL format."""
        log_file = tmp_path / "test.log"
        logger = RequestLogger(str(log_file))
        
        # Log multiple entries
        for i in range(3):
            logger.log_request(
                tool_name=f"tool_{i}",
                input_params={"index": i},
                output={"result": i},
                status="success",
                duration_ms=float(i * 100),
            )
        
        # Read and verify all entries
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        
        for i, line in enumerate(lines):
            entry = json.loads(line)
            assert entry["tool_name"] == f"tool_{i}"
            assert entry["input"]["index"] == i
            assert entry["output"]["result"] == i

    def test_sanitize_for_json_dict(self, tmp_path):
        """Test sanitization of dictionary objects."""
        log_file = tmp_path / "test.log"
        logger = RequestLogger(str(log_file))
        
        nested_dict = {
            "level1": {
                "level2": {
                    "value": "test"
                }
            }
        }
        
        logger.log_request(
            tool_name="test_tool",
            input_params=nested_dict,
            output=nested_dict,
            status="success",
            duration_ms=100.0,
        )
        
        with open(log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        
        assert entry["input"]["level1"]["level2"]["value"] == "test"

    def test_sanitize_for_json_list(self, tmp_path):
        """Test sanitization of list objects."""
        log_file = tmp_path / "test.log"
        logger = RequestLogger(str(log_file))
        
        test_list = [1, "two", {"three": 3}, [4, 5]]
        
        logger.log_request(
            tool_name="test_tool",
            input_params={"data": test_list},
            output={"result": test_list},
            status="success",
            duration_ms=100.0,
        )
        
        with open(log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        
        assert entry["input"]["data"] == test_list
        assert entry["output"]["result"] == test_list

    def test_sanitize_for_json_primitives(self, tmp_path):
        """Test sanitization of primitive types."""
        log_file = tmp_path / "test.log"
        logger = RequestLogger(str(log_file))
        
        primitives = {
            "string": "test",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
        }
        
        logger.log_request(
            tool_name="test_tool",
            input_params=primitives,
            output=primitives,
            status="success",
            duration_ms=100.0,
        )
        
        with open(log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        
        assert entry["input"]["string"] == "test"
        assert entry["input"]["int"] == 42
        assert entry["input"]["float"] == 3.14
        assert entry["input"]["bool"] is True
        assert entry["input"]["none"] is None

    def test_sanitize_for_json_custom_object(self, tmp_path):
        """Test sanitization of custom objects with __dict__."""
        log_file = tmp_path / "test.log"
        logger = RequestLogger(str(log_file))
        
        class CustomObject:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42
        
        obj = CustomObject()
        
        logger.log_request(
            tool_name="test_tool",
            input_params={"obj": obj},
            output={"obj": obj},
            status="success",
            duration_ms=100.0,
        )
        
        with open(log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        
        assert entry["input"]["obj"]["attr1"] == "value1"
        assert entry["input"]["obj"]["attr2"] == 42

    def test_log_file_append_mode(self, tmp_path):
        """Test that logging appends to existing file."""
        log_file = tmp_path / "test.log"
        
        # Create file with initial content
        with open(log_file, "w", encoding="utf-8") as f:
            f.write('{"existing": "entry"}\n')
        
        logger = RequestLogger(str(log_file))
        logger.log_request(
            tool_name="test_tool",
            input_params={},
            output={},
            status="success",
            duration_ms=100.0,
        )
        
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        assert json.loads(lines[0])["existing"] == "entry"
        assert json.loads(lines[1])["tool_name"] == "test_tool"

    def test_unicode_handling(self, tmp_path):
        """Test handling of unicode characters."""
        log_file = tmp_path / "test.log"
        logger = RequestLogger(str(log_file))
        
        unicode_data = {
            "emoji": "🎉🚀",
            "chinese": "你好世界",
            "arabic": "مرحبا",
            "special": "Ñoño™®©"
        }
        
        logger.log_request(
            tool_name="test_tool",
            input_params=unicode_data,
            output=unicode_data,
            status="success",
            duration_ms=100.0,
        )
        
        with open(log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        
        assert entry["input"]["emoji"] == "🎉🚀"
        assert entry["input"]["chinese"] == "你好世界"
        assert entry["input"]["arabic"] == "مرحبا"
        assert entry["input"]["special"] == "Ñoño™®©"
