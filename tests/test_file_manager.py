"""Tests for file manager functionality."""

import os
import pytest
from pathlib import Path
import tempfile
import shutil

from mcp_search_server.tools.file_manager import file_manager


class TestFileManager:
    """Test suite for FileManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path)

    @pytest.mark.asyncio
    async def test_write_and_read_file(self):
        """Test writing and reading a text file."""
        test_content = "Hello, MCP Server!\nThis is a test file."
        test_filename = "test_write_read.txt"

        # Write file
        write_result = await file_manager.write_file(test_filename, test_content)
        assert write_result["exists"]
        assert write_result["size"] > 0
        assert "successfully" in write_result["message"].lower()

        # Read file
        read_result = await file_manager.read_file(test_filename)
        assert read_result["exists"]
        assert test_content in read_result["content"]

        # Cleanup
        await file_manager.delete_file(test_filename)

    @pytest.mark.asyncio
    async def test_append_file(self):
        """Test appending content to a file."""
        test_filename = "test_append.txt"
        initial_content = "Line 1\n"
        append_content = "Line 2\n"

        # Write initial content
        await file_manager.write_file(test_filename, initial_content)

        # Append content
        append_result = await file_manager.write_file(test_filename, append_content, append=True)
        assert append_result["exists"]

        # Read and verify
        read_result = await file_manager.read_file(test_filename)
        assert initial_content in read_result["content"]
        assert append_content in read_result["content"]

        # Cleanup
        await file_manager.delete_file(test_filename)

    @pytest.mark.asyncio
    async def test_list_directory(self):
        """Test listing directory contents."""
        # Create test files
        test_files = ["file1.txt", "file2.txt", "file3.txt"]
        for filename in test_files:
            await file_manager.write_file(filename, f"Content of {filename}")

        # List directory (empty string means default data/files directory)
        list_result = await file_manager.list_directory("")

        assert list_result["count"] >= len(test_files)
        assert len(list_result["items"]) >= len(test_files)

        # Verify our test files are in the listing
        file_names = [item["name"] for item in list_result["items"]]
        for test_file in test_files:
            assert test_file in file_names

        # Cleanup
        for filename in test_files:
            await file_manager.delete_file(filename)

    @pytest.mark.asyncio
    async def test_delete_file(self):
        """Test deleting a file."""
        test_filename = "test_delete.txt"

        # Create file
        await file_manager.write_file(test_filename, "This will be deleted")

        # Verify it exists
        read_result = await file_manager.read_file(test_filename)
        assert read_result["exists"]

        # Delete file
        delete_result = await file_manager.delete_file(test_filename)
        assert delete_result["success"]
        assert "successfully" in delete_result["message"].lower()

        # Verify it's deleted
        read_result = await file_manager.read_file(test_filename)
        assert not read_result["exists"]

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        result = await file_manager.read_file("nonexistent_file.txt")
        assert not result["exists"]
        assert "not found" in result["content"].lower()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self):
        """Test deleting a file that doesn't exist."""
        result = await file_manager.delete_file("nonexistent_file.txt")
        assert not result["success"]
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_path_normalization(self):
        """Test that paths are normalized correctly."""
        # Test with relative path (use os.sep for cross-platform compatibility)
        test_filename = os.path.join("subdir", "test_normalize.txt")
        content = "Testing path normalization"

        write_result = await file_manager.write_file(test_filename, content)
        assert write_result["exists"]
        # Check path contains 'data' and 'files' directories (cross-platform)
        assert "data" in write_result["path"] and "files" in write_result["path"]

        # Read it back
        read_result = await file_manager.read_file(test_filename)
        assert content in read_result["content"]

        # Cleanup
        await file_manager.delete_file(test_filename)

    @pytest.mark.asyncio
    async def test_large_file_handling(self):
        """Test handling of large files (within limits)."""
        test_filename = "test_large.txt"
        # Create content that's around 1MB
        large_content = "A" * (1024 * 1024)  # 1MB of 'A's

        write_result = await file_manager.write_file(test_filename, large_content)
        assert write_result["exists"]
        assert write_result["size"] >= 1024 * 1024

        # Read it back
        read_result = await file_manager.read_file(test_filename)
        assert len(read_result["content"]) >= 1024 * 1024

        # Cleanup
        await file_manager.delete_file(test_filename)

    @pytest.mark.asyncio
    async def test_special_characters_in_content(self):
        """Test handling of special characters in file content."""
        test_filename = "test_special_chars.txt"
        special_content = "Special chars: 你好世界 🌍 ñáéíóú \n\t"

        await file_manager.write_file(test_filename, special_content)
        read_result = await file_manager.read_file(test_filename)

        # Check main content (\r may be normalized to \n on some systems)
        assert "Special chars: 你好世界 🌍 ñáéíóú" in read_result["content"]

        # Cleanup
        await file_manager.delete_file(test_filename)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
