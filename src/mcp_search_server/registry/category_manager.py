"""Category manager for loading and managing tool categories."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

from ..tools.base import ToolCategory, ToolPriority

logger = logging.getLogger(__name__)


class CategoryManager:
    """
    Manages tool categories and their configurations.

    Features:
    - Load category definitions from YAML
    - Get category metadata (name, description, icon)
    - Filter categories by priority
    - Get loading strategy for categories

    Usage:
        manager = CategoryManager()

        # Get high priority categories
        high_priority = manager.get_high_priority_categories()

        # Get category config
        config = manager.get_category_config(ToolCategory.WEB)
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize category manager.

        Args:
            config_path: Path to categories.yaml (optional, auto-detected)
        """
        self._categories: Dict[str, Dict[str, Any]] = {}
        self._priorities: Dict[str, Dict[str, Any]] = {}
        self._loading_config: Dict[str, Any] = {}

        # Auto-detect config path if not provided
        if config_path is None:
            config_path = self._find_config_path()

        self._config_path = config_path

        # Load configuration
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
        else:
            logger.warning(f"Categories config not found at {config_path}, using defaults")
            self._load_defaults()

    def _find_config_path(self) -> str:
        """
        Auto-detect the categories.yaml config file.

        Returns:
            Path to categories.yaml
        """
        # Try multiple locations
        possible_paths = [
            # Relative to current working directory
            "config/categories.yaml",
            # Relative to this file
            Path(__file__).parent.parent.parent.parent / "config" / "categories.yaml",
            # Absolute path (for installed package)
            "/etc/mcp-search-server/categories.yaml",
        ]

        for path in possible_paths:
            path_str = str(path)
            if os.path.exists(path_str):
                logger.debug(f"Found categories config at {path_str}")
                return path_str

        # Default fallback
        return "config/categories.yaml"

    def _load_config(self, config_path: str) -> None:
        """
        Load categories configuration from YAML file.

        Args:
            config_path: Path to categories.yaml
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            self._categories = config.get("categories", {})
            self._priorities = config.get("priorities", {})
            self._loading_config = config.get("loading", {})

            logger.info(f"Loaded {len(self._categories)} categories from {config_path}")

        except Exception as e:
            logger.error(f"Failed to load categories config: {e}")
            self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default category configuration."""
        self._categories = {
            "web": {
                "name": "Web Search & Content",
                "priority": "HIGH",
                "defer_loading": False,
            },
            "knowledge": {
                "name": "Knowledge & Academic",
                "priority": "MEDIUM",
                "defer_loading": True,
            },
            "social": {
                "name": "Social & Code",
                "priority": "MEDIUM",
                "defer_loading": True,
            },
            "analysis": {
                "name": "Analysis & Processing",
                "priority": "HIGH",
                "defer_loading": False,
            },
            "context": {
                "name": "Context & Location",
                "priority": "HIGH",
                "defer_loading": False,
            },
            "files": {
                "name": "File Management",
                "priority": "MEDIUM",
                "defer_loading": True,
            },
            "meta": {
                "name": "Tool Discovery",
                "priority": "HIGH",
                "defer_loading": False,
            },
        }

        self._priorities = {
            "HIGH": {"load_immediately": True},
            "MEDIUM": {"load_immediately": False, "load_on_first_use": True},
            "LOW": {"load_immediately": False, "load_on_first_use": False},
        }

        self._loading_config = {
            "strategy": "category_based",
            "enable_defer_loading": True,
            "preload_categories": ["web", "analysis", "context", "meta"],
        }

    def get_category_config(self, category: ToolCategory) -> Dict[str, Any]:
        """
        Get configuration for a category.

        Args:
            category: Tool category

        Returns:
            Category configuration dictionary
        """
        return self._categories.get(category.value, {})

    def get_category_name(self, category: ToolCategory) -> str:
        """
        Get human-readable name for a category.

        Args:
            category: Tool category

        Returns:
            Category name
        """
        config = self.get_category_config(category)
        return config.get("name", category.value.title())

    def get_category_description(self, category: ToolCategory) -> str:
        """
        Get description for a category.

        Args:
            category: Tool category

        Returns:
            Category description
        """
        config = self.get_category_config(category)
        return config.get("description", "")

    def get_category_priority(self, category: ToolCategory) -> ToolPriority:
        """
        Get priority level for a category.

        Args:
            category: Tool category

        Returns:
            Priority level
        """
        config = self.get_category_config(category)
        priority_str = config.get("priority", "MEDIUM")

        try:
            return ToolPriority[priority_str]
        except KeyError:
            logger.warning(f"Invalid priority {priority_str}, using MEDIUM")
            return ToolPriority.MEDIUM

    def should_defer_loading(self, category: ToolCategory) -> bool:
        """
        Check if category should use deferred loading.

        Args:
            category: Tool category

        Returns:
            True if should defer loading
        """
        config = self.get_category_config(category)
        return config.get("defer_loading", True)

    def get_high_priority_categories(self) -> List[ToolCategory]:
        """
        Get all categories with HIGH priority.

        Returns:
            List of high priority categories
        """
        high_priority = []
        for cat_name, config in self._categories.items():
            if config.get("priority") == "HIGH":
                try:
                    category = ToolCategory[cat_name.upper()]
                    high_priority.append(category)
                except KeyError:
                    logger.warning(f"Unknown category: {cat_name}")

        return high_priority

    def get_preload_categories(self) -> List[ToolCategory]:
        """
        Get categories that should be preloaded at startup.

        Returns:
            List of categories to preload
        """
        preload_names = self._loading_config.get("preload_categories", [])
        categories = []

        for name in preload_names:
            try:
                category = ToolCategory[name.upper()]
                categories.append(category)
            except KeyError:
                logger.warning(f"Unknown preload category: {name}")

        return categories

    def get_all_categories(self) -> List[ToolCategory]:
        """
        Get all defined categories.

        Returns:
            List of all categories
        """
        categories = []
        for cat_name in self._categories.keys():
            try:
                category = ToolCategory[cat_name.upper()]
                categories.append(category)
            except KeyError:
                logger.warning(f"Unknown category: {cat_name}")

        return categories

    def is_defer_loading_enabled(self) -> bool:
        """
        Check if deferred loading is enabled globally.

        Returns:
            True if defer loading is enabled
        """
        return self._loading_config.get("enable_defer_loading", True)

    def get_loading_strategy(self) -> str:
        """
        Get the loading strategy.

        Returns:
            Loading strategy name
        """
        return self._loading_config.get("strategy", "category_based")

    def get_initial_tool_limit(self) -> int:
        """
        Get the maximum number of tools to show initially.

        Returns:
            Initial tool limit
        """
        return self._loading_config.get("initial_tool_limit", 10)

    def is_tool_search_enabled(self) -> bool:
        """
        Check if tool search is enabled.

        Returns:
            True if tool search is enabled
        """
        return self._loading_config.get("enable_tool_search", True)

    def get_category_icon(self, category: ToolCategory) -> str:
        """
        Get icon for a category.

        Args:
            category: Tool category

        Returns:
            Category icon (emoji)
        """
        config = self.get_category_config(category)
        return config.get("icon", "🔧")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get category manager statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_categories": len(self._categories),
            "high_priority_count": len(self.get_high_priority_categories()),
            "preload_count": len(self.get_preload_categories()),
            "defer_loading_enabled": self.is_defer_loading_enabled(),
            "loading_strategy": self.get_loading_strategy(),
            "config_path": self._config_path,
        }

    def reload_config(self) -> None:
        """Reload configuration from file."""
        if self._config_path and os.path.exists(self._config_path):
            logger.info(f"Reloading categories config from {self._config_path}")
            self._load_config(self._config_path)
        else:
            logger.warning("Cannot reload config, file not found")
