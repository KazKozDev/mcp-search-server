"""Base class for all MCP tools with metadata and registration support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, List
from enum import Enum


class ToolPriority(Enum):
    """Tool loading priority levels."""

    HIGH = "HIGH"  # Always loaded (critical tools)
    MEDIUM = "MEDIUM"  # Load on demand (most tools)
    LOW = "LOW"  # Rarely used, load only when explicitly requested


class ToolCategory(Enum):
    """Tool categories for organization."""

    WEB = "web"  # Web search and content extraction
    KNOWLEDGE = "knowledge"  # Wikipedia, academic sources
    SOCIAL = "social"  # GitHub, Reddit
    ANALYSIS = "analysis"  # Credibility, summarization, calculation
    CONTEXT = "context"  # Date/time, geolocation
    FILES = "files"  # File management
    META = "meta"  # Tool discovery and management


@dataclass
class ToolMetadata:
    """Metadata for a tool."""

    name: str
    description: str
    category: ToolCategory
    priority: ToolPriority = ToolPriority.MEDIUM
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    defer_loading: bool = True  # Load on demand by default

    # MCP-specific metadata
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

    # Performance hints
    estimated_duration_ms: Optional[int] = None  # Estimated execution time
    requires_network: bool = False
    requires_filesystem: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority.value,
            "version": self.version,
            "tags": self.tags,
            "examples": self.examples,
            "defer_loading": self.defer_loading,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "estimated_duration_ms": self.estimated_duration_ms,
            "requires_network": self.requires_network,
            "requires_filesystem": self.requires_filesystem,
        }


class BaseTool(ABC):
    """
    Base class for all MCP tools.

    Provides:
    - Metadata management (category, priority, version)
    - Standardized registration interface
    - Execution wrapper with error handling
    - Performance tracking

    Usage:
        class MyTool(BaseTool):
            def __init__(self):
                metadata = ToolMetadata(
                    name="my_tool",
                    description="Does something useful",
                    category=ToolCategory.WEB,
                    priority=ToolPriority.HIGH,
                )
                super().__init__(metadata)

            async def execute(self, **kwargs) -> Any:
                # Tool implementation
                return result
    """

    def __init__(self, metadata: ToolMetadata):
        """
        Initialize tool with metadata.

        Args:
            metadata: Tool metadata including name, category, priority
        """
        self.metadata = metadata
        self._execution_count = 0
        self._total_duration_ms = 0
        self._error_count = 0

    @property
    def name(self) -> str:
        """Get tool name."""
        return self.metadata.name

    @property
    def description(self) -> str:
        """Get tool description."""
        return self.metadata.description

    @property
    def category(self) -> ToolCategory:
        """Get tool category."""
        return self.metadata.category

    @property
    def priority(self) -> ToolPriority:
        """Get tool priority."""
        return self.metadata.priority

    @property
    def version(self) -> str:
        """Get tool version."""
        return self.metadata.version

    @property
    def defer_loading(self) -> bool:
        """Check if tool should be loaded on demand."""
        return self.metadata.defer_loading

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given arguments.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            Tool-specific result

        Raises:
            ValueError: If arguments are invalid
            RuntimeError: If execution fails
        """
        pass

    async def execute_with_tracking(self, **kwargs) -> Any:
        """
        Execute tool with performance tracking and error handling.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            Tool execution result

        Raises:
            Exception: Re-raises any exception from execute()
        """
        import time

        start_time = time.time()
        try:
            result = await self.execute(**kwargs)
            self._execution_count += 1
            duration_ms = int((time.time() - start_time) * 1000)
            self._total_duration_ms += duration_ms
            return result
        except Exception:
            self._error_count += 1
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get tool execution statistics.

        Returns:
            Dictionary with execution stats
        """
        avg_duration = (
            self._total_duration_ms / self._execution_count if self._execution_count > 0 else 0
        )
        return {
            "name": self.name,
            "execution_count": self._execution_count,
            "total_duration_ms": self._total_duration_ms,
            "average_duration_ms": int(avg_duration),
            "error_count": self._error_count,
            "error_rate": (
                self._error_count / self._execution_count if self._execution_count > 0 else 0
            ),
        }

    def to_mcp_tool(self) -> Dict[str, Any]:
        """
        Convert to MCP Tool definition.

        Returns:
            MCP Tool definition dictionary
        """
        tool_def = {
            "name": self.name,
            "description": self.description,
        }

        if self.metadata.input_schema:
            tool_def["inputSchema"] = self.metadata.input_schema

        if self.metadata.output_schema:
            tool_def["outputSchema"] = self.metadata.output_schema

        return tool_def

    def matches_query(self, query: str) -> bool:
        """
        Check if tool matches a search query.

        Args:
            query: Search query string

        Returns:
            True if tool matches query
        """
        query_lower = query.lower()

        # Check name
        if query_lower in self.name.lower():
            return True

        # Check description
        if query_lower in self.description.lower():
            return True

        # Check tags
        for tag in self.metadata.tags:
            if query_lower in tag.lower():
                return True

        # Check category
        if query_lower in self.category.value.lower():
            return True

        return False

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<{self.__class__.__name__} "
            f"name={self.name} "
            f"category={self.category.value} "
            f"priority={self.priority.value}>"
        )


class FunctionTool(BaseTool):
    """
    Wrapper for function-based tools.

    Allows wrapping existing async functions as BaseTool instances.

    Usage:
        async def my_function(arg1: str, arg2: int) -> str:
            return f"Result: {arg1} {arg2}"

        metadata = ToolMetadata(
            name="my_function",
            description="Example function",
            category=ToolCategory.WEB,
        )

        tool = FunctionTool(metadata, my_function)
    """

    def __init__(self, metadata: ToolMetadata, func: Callable):
        """
        Initialize function-based tool.

        Args:
            metadata: Tool metadata
            func: Async function to wrap
        """
        super().__init__(metadata)
        self.func = func

        # Auto-generate schema if not provided
        if not self.metadata.input_schema:
            try:
                # Import here to avoid circular dependencies if any
                from ..registry.schema import generate_input_schema

                self.metadata.input_schema = generate_input_schema(func)
            except ImportError:
                # Fallback if registry not found/initialized
                pass
            except Exception:
                # Log but continue
                pass

    async def execute(self, **kwargs) -> Any:
        """Execute the wrapped function."""
        return await self.func(**kwargs)
