---
description: MCP Server Refactoring Plan - Modular Architecture with 24 Tools
---

# MCP Search Server - План Рефакторинга

## Цель
Реорганизовать архитектуру MCP-сервера с 24 инструментами для:
- Улучшения масштабируемости и поддержки
- Снижения потребления токенов (через динамическую загрузку)
- Упрощения разработки и тестирования
- Подготовки к росту до 50+ инструментов

## Текущее состояние

### Проблемы
- ❌ Монолитный `server.py` (2824 строки)
- ❌ Все 24 инструмента загружаются сразу → высокое потребление токенов
- ❌ Нет категоризации → сложно найти нужный инструмент
- ❌ Тяжело добавлять новые инструменты
- ❌ Нет изоляции тестов по категориям

### Что работает хорошо
- ✅ Инструменты уже разделены на отдельные модули в `tools/`
- ✅ Качественная реализация каждого инструмента
- ✅ Хорошее покрытие тестами
- ✅ Документация в README

## Архитектура после рефакторинга

### Новая структура директорий

```
mcp-search-server/
├── src/
│   ├── mcp_search_server/
│   │   ├── __init__.py
│   │   ├── server.py                    # Главная точка входа (упрощенная)
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── tool_config.yaml         # Конфигурация инструментов
│   │   │   └── categories.yaml          # Определение категорий
│   │   ├── registry/
│   │   │   ├── __init__.py
│   │   │   ├── tool_registry.py         # Динамическая регистрация
│   │   │   ├── category_manager.py      # Управление категориями
│   │   │   └── loader.py                # Ленивая загрузка инструментов
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # Базовый класс для всех инструментов
│   │   │   ├── web/                     # Web Search & Content (6 tools)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── duckduckgo.py
│   │   │   │   ├── link_parser.py
│   │   │   │   ├── pdf_parser.py
│   │   │   │   ├── maps_tool.py
│   │   │   │   ├── rss_tool.py
│   │   │   │   └── unified_search.py
│   │   │   ├── knowledge/               # Wikipedia & Academic (6 tools)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── wikipedia.py
│   │   │   │   ├── arxiv.py
│   │   │   │   ├── pubmed.py
│   │   │   │   └── gdelt.py
│   │   │   ├── social/                  # GitHub & Reddit (4 tools)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── github.py
│   │   │   │   └── reddit.py
│   │   │   ├── analysis/                # Analysis & Processing (3 tools)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── credibility.py
│   │   │   │   ├── summarizer.py
│   │   │   │   └── calculator.py
│   │   │   ├── context/                 # Date, Time & Location (2 tools)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── datetime_tool.py
│   │   │   │   └── geolocation.py
│   │   │   └── files/                   # File Management (5 tools)
│   │   │       ├── __init__.py
│   │   │       └── file_manager.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── logger.py                # Централизованное логирование
│   │   │   └── helpers.py               # Общие утилиты
│   │   ├── cache_store.py               # Существующий кэш
│   │   ├── config_loader.py             # Существующий загрузчик конфигов
│   │   ├── enrich.py                    # Существующая обогащение результатов
│   │   └── result_utils.py              # Существующие утилиты результатов
├── tests/
│   ├── test_web/                        # Тесты для web категории
│   ├── test_knowledge/                  # Тесты для knowledge категории
│   ├── test_social/                     # Тесты для social категории
│   ├── test_analysis/                   # Тесты для analysis категории
│   ├── test_context/                    # Тесты для context категории
│   ├── test_files/                      # Тесты для files категории
│   └── test_registry/                   # Тесты для системы регистрации
├── config/
│   ├── tool_config.yaml                 # Конфигурация инструментов
│   └── categories.yaml                  # Определение категорий
├── pyproject.toml
├── requirements.txt
└── README.md
```

### Категории инструментов

| Категория | Инструменты | Описание | Приоритет загрузки |
|-----------|-------------|----------|-------------------|
| **web** | search_web, extract_webpage_content, parse_pdf, search_maps, parse_rss | Веб-поиск и извлечение контента | HIGH (всегда загружены) |
| **knowledge** | search_wikipedia, get_wikipedia_summary, get_wikipedia_content, search_arxiv, search_pubmed, search_gdelt | Академические и энциклопедические источники | MEDIUM (по запросу) |
| **social** | search_github, get_github_readme, search_reddit, get_reddit_comments | Социальные платформы и код | MEDIUM (по запросу) |
| **analysis** | assess_source_credibility, summarize_text, calculate | Анализ и обработка данных | HIGH (всегда загружены) |
| **context** | get_current_datetime, get_location_by_ip | Контекстная информация | HIGH (всегда загружены) |
| **files** | read_file, write_file, append_file, list_files, delete_file | Управление файлами | MEDIUM (по запросу) |

## Фазы реализации

---

## ФАЗА 1: Подготовка инфраструктуры (День 1)

### Цель
Создать базовую инфраструктуру для модульной архитектуры без изменения существующего кода.

### Шаг 1.1: Создать базовый класс для инструментов

**Файл:** `src/mcp_search_server/tools/base.py`

**Что делает:**
- Определяет интерфейс для всех инструментов
- Добавляет метаданные (категория, приоритет, версия)
- Обеспечивает единообразие

**Действия:**
```bash
# Создать файл base.py с базовым классом BaseTool
```

**Критерии успеха:**
- [ ] Файл `base.py` создан
- [ ] Класс `BaseTool` имеет атрибуты: name, category, priority, version, description
- [ ] Есть абстрактные методы для регистрации и выполнения

### Шаг 1.2: Создать систему категорий

**Файл:** `config/categories.yaml`

**Что делает:**
- Определяет все категории инструментов
- Задает приоритеты загрузки
- Описывает каждую категорию

**Действия:**
```bash
# Создать config/categories.yaml
# Определить 6 категорий: web, knowledge, social, analysis, context, files
```

**Критерии успеха:**
- [ ] Файл `categories.yaml` создан
- [ ] Все 6 категорий определены
- [ ] Для каждой категории указан приоритет (HIGH/MEDIUM/LOW)

### Шаг 1.3: Создать конфигурацию инструментов

**Файл:** `config/tool_config.yaml`

**Что делает:**
- Сопоставляет каждый инструмент с категорией
- Определяет настройки загрузки (defer_loading)
- Задает метаданные инструментов

**Действия:**
```bash
# Создать config/tool_config.yaml
# Добавить все 24 инструмента с их категориями
```

**Критерии успеха:**
- [ ] Файл `tool_config.yaml` создан
- [ ] Все 24 инструмента перечислены
- [ ] Каждый инструмент имеет: category, defer_loading, priority

### Шаг 1.4: Создать систему регистрации инструментов

**Файл:** `src/mcp_search_server/registry/tool_registry.py`

**Что делает:**
- Управляет регистрацией инструментов
- Поддерживает динамическую загрузку
- Фильтрует инструменты по категориям

**Действия:**
```bash
# Создать registry/tool_registry.py
# Реализовать класс ToolRegistry с методами:
#   - register_tool(tool)
#   - get_tools_by_category(category)
#   - get_all_tools()
#   - load_tool(name)
```

**Критерии успеха:**
- [ ] Класс `ToolRegistry` создан
- [ ] Методы регистрации и получения инструментов работают
- [ ] Поддержка ленивой загрузки реализована

### Шаг 1.5: Создать менеджер категорий

**Файл:** `src/mcp_search_server/registry/category_manager.py`

**Что делает:**
- Загружает категории из YAML
- Управляет приоритетами
- Предоставляет API для работы с категориями

**Действия:**
```bash
# Создать registry/category_manager.py
# Реализовать класс CategoryManager
```

**Критерии успеха:**
- [ ] Класс `CategoryManager` создан
- [ ] Загрузка из `categories.yaml` работает
- [ ] Методы получения категорий и приоритетов реализованы

### Проверка Фазы 1

```bash
# Запустить тесты инфраструктуры
pytest tests/test_registry/ -v

# Проверить импорты
python -c "from mcp_search_server.tools.base import BaseTool; print('OK')"
python -c "from mcp_search_server.registry import ToolRegistry; print('OK')"
```

**Ожидаемый результат:**
- Вся инфраструктура создана
- Тесты проходят
- Существующий код продолжает работать без изменений

---

## ФАЗА 2: Реорганизация инструментов по категориям (День 2-3)

### Цель
Переместить инструменты в категоризированные директории и обновить их для использования базового класса.

### Шаг 2.1: Создать структуру директорий

**Действия:**
```bash
cd /Users/artemk/projects/mcp-search-server/src/mcp_search_server/tools

# Создать директории категорий
mkdir -p web knowledge social analysis context files

# Создать __init__.py в каждой директории
touch web/__init__.py knowledge/__init__.py social/__init__.py \
      analysis/__init__.py context/__init__.py files/__init__.py
```

**Критерии успеха:**
- [ ] 6 директорий категорий созданы
- [ ] Каждая директория имеет `__init__.py`

### Шаг 2.2: Переместить инструменты в категории

**Категория: web**
```bash
# Переместить файлы
mv duckduckgo.py web/
mv link_parser.py web/
mv pdf_parser.py web/
mv maps_tool.py web/
mv rss_tool.py web/
mv unified_search.py web/
```

**Категория: knowledge**
```bash
mv wikipedia.py knowledge/
mv arxiv.py knowledge/
mv pubmed.py knowledge/
mv gdelt.py knowledge/
```

**Категория: social**
```bash
mv github.py social/
mv reddit.py social/
```

**Категория: analysis**
```bash
mv credibility.py analysis/
mv summarizer.py analysis/
mv calculator.py analysis/
```

**Категория: context**
```bash
mv datetime_tool.py context/
mv geolocation.py context/
```

**Категория: files**
```bash
mv file_manager.py files/
```

**Критерии успеха:**
- [ ] Все инструменты перемещены в соответствующие категории
- [ ] Старая директория `tools/` содержит только поддиректории
- [ ] Файл `search_engine_base.py` и `search_manager.py` остались в `tools/` (общие утилиты)

### Шаг 2.3: Обновить импорты в каждом инструменте

**Для каждого файла инструмента:**

1. Добавить импорт базового класса:
```python
from ..base import BaseTool
```

2. Обновить относительные импорты (если есть):
```python
# Было:
from .search_engine_base import SearchEngineBase

# Стало:
from ..search_engine_base import SearchEngineBase
```

**Критерии успеха:**
- [ ] Все инструменты импортируют `BaseTool`
- [ ] Относительные импорты обновлены
- [ ] Нет ошибок импорта при запуске `python -m mcp_search_server.server`

### Шаг 2.4: Обновить `__init__.py` в каждой категории

**Пример для `web/__init__.py`:**
```python
"""Web search and content extraction tools."""

from .duckduckgo import search_duckduckgo
from .link_parser import extract_webpage_content
from .pdf_parser import parse_pdf
from .maps_tool import search_maps
from .rss_tool import parse_rss
from .unified_search import search_web

__all__ = [
    "search_duckduckgo",
    "extract_webpage_content",
    "parse_pdf",
    "search_maps",
    "parse_rss",
    "search_web",
]
```

**Повторить для всех категорий:**
- `knowledge/__init__.py`
- `social/__init__.py`
- `analysis/__init__.py`
- `context/__init__.py`
- `files/__init__.py`

**Критерии успеха:**
- [ ] Все `__init__.py` созданы
- [ ] Экспортируются все функции инструментов
- [ ] Импорт работает: `from mcp_search_server.tools.web import search_web`

### Шаг 2.5: Обновить главный `tools/__init__.py`

**Файл:** `src/mcp_search_server/tools/__init__.py`

**Было:**
```python
# Импорты всех инструментов напрямую
```

**Стало:**
```python
"""MCP Search Server Tools - Organized by category."""

# Web Search & Content
from .web import (
    search_web,
    extract_webpage_content,
    parse_pdf,
    search_maps,
    parse_rss,
)

# Knowledge & Academic
from .knowledge import (
    search_wikipedia,
    get_wikipedia_summary,
    get_wikipedia_content,
    search_arxiv,
    search_pubmed,
    search_gdelt,
)

# Social & Code
from .social import (
    search_github,
    get_github_readme,
    search_reddit,
    get_reddit_comments,
)

# Analysis & Processing
from .analysis import (
    assess_source_credibility,
    summarize_text,
    calculator,
)

# Context & Location
from .context import (
    get_current_datetime,
    get_location_by_ip,
)

# File Management
from .files import (
    file_manager,
)

__all__ = [
    # Web
    "search_web",
    "extract_webpage_content",
    "parse_pdf",
    "search_maps",
    "parse_rss",
    # Knowledge
    "search_wikipedia",
    "get_wikipedia_summary",
    "get_wikipedia_content",
    "search_arxiv",
    "search_pubmed",
    "search_gdelt",
    # Social
    "search_github",
    "get_github_readme",
    "search_reddit",
    "get_reddit_comments",
    # Analysis
    "assess_source_credibility",
    "summarize_text",
    "calculator",
    # Context
    "get_current_datetime",
    "get_location_by_ip",
    # Files
    "file_manager",
]
```

**Критерии успеха:**
- [ ] Все инструменты экспортируются через категории
- [ ] Обратная совместимость сохранена
- [ ] Импорт работает: `from mcp_search_server.tools import search_web`

### Проверка Фазы 2

```bash
# Проверить импорты
python -c "from mcp_search_server.tools.web import search_web; print('OK')"
python -c "from mcp_search_server.tools import search_web; print('OK')"

# Запустить все тесты
pytest tests/ -v

# Проверить, что сервер запускается
python -m mcp_search_server.server --help
```

**Ожидаемый результат:**
- Все инструменты доступны через новую структуру
- Обратная совместимость сохранена
- Тесты проходят
- Сервер запускается без ошибок

---

## ФАЗА 3: Рефакторинг server.py (День 4)

### Цель
Упростить `server.py`, используя систему регистрации инструментов вместо ручной регистрации.

### Шаг 3.1: Создать функции регистрации по категориям

**Файл:** `src/mcp_search_server/registry/loader.py`

**Что делает:**
- Автоматически регистрирует инструменты из категории
- Поддерживает ленивую загрузку
- Упрощает добавление новых инструментов

**Реализация:**
```python
"""Tool loader with category-based registration."""

from typing import List, Callable
from mcp.server import Server
from ..tools import web, knowledge, social, analysis, context, files
from .tool_registry import ToolRegistry
from .category_manager import CategoryManager

def register_category_tools(
    server: Server,
    category: str,
    registry: ToolRegistry,
    category_manager: CategoryManager
) -> List[str]:
    """Register all tools from a category."""
    # Получить настройки категории
    config = category_manager.get_category_config(category)
    
    # Получить модуль категории
    category_module = {
        "web": web,
        "knowledge": knowledge,
        "social": social,
        "analysis": analysis,
        "context": context,
        "files": files,
    }.get(category)
    
    if not category_module:
        return []
    
    # Зарегистрировать все инструменты из модуля
    registered = []
    for tool_func in category_module.__all__:
        func = getattr(category_module, tool_func)
        server.tool()(func)
        registry.register_tool(tool_func, category, config.get("priority", "MEDIUM"))
        registered.append(tool_func)
    
    return registered

def register_all_tools(server: Server) -> ToolRegistry:
    """Register all tools organized by category."""
    registry = ToolRegistry()
    category_manager = CategoryManager()
    
    # Загрузить категории с HIGH приоритетом сразу
    high_priority = category_manager.get_high_priority_categories()
    for category in high_priority:
        register_category_tools(server, category, registry, category_manager)
    
    # Остальные категории - по запросу (defer_loading)
    # Это будет реализовано в Фазе 4
    
    return registry
```

**Критерии успеха:**
- [ ] Функция `register_category_tools` создана
- [ ] Функция `register_all_tools` создана
- [ ] Регистрация работает для всех категорий

### Шаг 3.2: Упростить server.py

**Файл:** `src/mcp_search_server/server.py`

**Было (2824 строки):**
```python
# Огромный файл с ручной регистрацией всех инструментов
@app.list_tools()
async def list_tools():
    return [
        Tool(name="search_web", ...),
        Tool(name="extract_webpage_content", ...),
        # ... еще 22 инструмента
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any):
    if name == "search_web":
        # ...
    elif name == "extract_webpage_content":
        # ...
    # ... еще 22 elif блока
```

**Стало (~300-400 строк):**
```python
"""MCP Search Server - Web search, PDF parsing, and content extraction."""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from .registry.loader import register_all_tools
from .registry.tool_registry import ToolRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("mcp-search-server")
tool_registry: ToolRegistry = None

@app.list_tools()
async def list_tools():
    """List available tools organized by category."""
    global tool_registry
    if tool_registry is None:
        tool_registry = register_all_tools(app)
    
    return tool_registry.get_all_tool_definitions()

@app.call_tool()
async def call_tool(name: str, arguments: Any):
    """Handle tool calls using the registry."""
    global tool_registry
    if tool_registry is None:
        tool_registry = register_all_tools(app)
    
    return await tool_registry.execute_tool(name, arguments)

async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )

def run():
    """Entry point for the server."""
    asyncio.run(main())

if __name__ == "__main__":
    run()
```

**Критерии успеха:**
- [ ] `server.py` сокращен до ~300-400 строк
- [ ] Используется `ToolRegistry` для управления инструментами
- [ ] Вся логика регистрации вынесена в `registry/loader.py`
- [ ] Сервер запускается и работает корректно

### Шаг 3.3: Обновить ToolRegistry для выполнения инструментов

**Файл:** `src/mcp_search_server/registry/tool_registry.py`

**Добавить методы:**
```python
async def execute_tool(self, name: str, arguments: Any) -> List[TextContent]:
    """Execute a tool by name with given arguments."""
    tool = self.get_tool(name)
    if not tool:
        raise ValueError(f"Tool {name} not found")
    
    # Выполнить инструмент
    result = await tool.execute(arguments)
    return result

def get_all_tool_definitions(self) -> List[Tool]:
    """Get MCP Tool definitions for all registered tools."""
    return [tool.to_mcp_tool() for tool in self._tools.values()]
```

**Критерии успеха:**
- [ ] Метод `execute_tool` реализован
- [ ] Метод `get_all_tool_definitions` реализован
- [ ] Инструменты выполняются через registry

### Проверка Фазы 3

```bash
# Запустить сервер
mcp-search-server &

# Проверить список инструментов
# (используя MCP клиент или Claude Desktop)

# Проверить выполнение инструмента
# Например: search_web с query="test"

# Запустить все тесты
pytest tests/ -v

# Проверить размер server.py
wc -l src/mcp_search_server/server.py
# Ожидаемый результат: ~300-400 строк (было 2824)
```

**Ожидаемый результат:**
- `server.py` значительно упрощен
- Все инструменты работают через registry
- Тесты проходят
- Функциональность не изменилась

---

## ФАЗА 4: Динамическая загрузка инструментов (День 5)

### Цель
Реализовать ленивую загрузку инструментов для экономии токенов (80-90% экономия).

### Шаг 4.1: Добавить tool_search_tool

**Файл:** `src/mcp_search_server/tools/meta/search_tools.py`

**Что делает:**
- Позволяет LLM искать инструменты по описанию
- Возвращает список подходящих инструментов
- Автоматически загружает нужные инструменты

**Реализация:**
```python
"""Tool search functionality for dynamic tool discovery."""

from typing import List, Dict, Any
from ..base import BaseTool

async def search_tools(query: str, category: str = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for tools by description or category.
    
    Args:
        query: Search query (e.g., "search web", "parse PDF")
        category: Optional category filter (web, knowledge, social, etc.)
        limit: Maximum number of results
    
    Returns:
        List of matching tools with names, descriptions, and categories
    """
    from ...registry.tool_registry import get_global_registry
    
    registry = get_global_registry()
    results = registry.search_tools(query, category, limit)
    
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "parameters": tool.parameters,
        }
        for tool in results
    ]
```

**Критерии успеха:**
- [ ] Инструмент `search_tools` создан
- [ ] Поиск по описанию работает
- [ ] Фильтрация по категории работает
- [ ] Зарегистрирован в MCP сервере

### Шаг 4.2: Реализовать defer_loading в ToolRegistry

**Файл:** `src/mcp_search_server/registry/tool_registry.py`

**Обновить:**
```python
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._deferred_tools: Dict[str, Dict[str, Any]] = {}
        self._loaded_categories: Set[str] = set()
    
    def register_tool(self, tool: BaseTool, defer: bool = False):
        """Register a tool with optional deferred loading."""
        if defer:
            self._deferred_tools[tool.name] = {
                "category": tool.category,
                "loader": tool.loader_func,
                "metadata": tool.metadata,
            }
        else:
            self._tools[tool.name] = tool
    
    async def load_tool(self, name: str):
        """Load a deferred tool on demand."""
        if name in self._tools:
            return self._tools[name]
        
        if name in self._deferred_tools:
            tool_info = self._deferred_tools[name]
            tool = await tool_info["loader"]()
            self._tools[name] = tool
            del self._deferred_tools[name]
            return tool
        
        raise ValueError(f"Tool {name} not found")
    
    async def load_category(self, category: str):
        """Load all tools from a category."""
        if category in self._loaded_categories:
            return
        
        # Загрузить все отложенные инструменты из категории
        deferred_in_category = [
            name for name, info in self._deferred_tools.items()
            if info["category"] == category
        ]
        
        for tool_name in deferred_in_category:
            await self.load_tool(tool_name)
        
        self._loaded_categories.add(category)
```

**Критерии успеха:**
- [ ] Метод `register_tool` поддерживает `defer=True`
- [ ] Метод `load_tool` загружает отложенные инструменты
- [ ] Метод `load_category` загружает целую категорию
- [ ] Отложенные инструменты не появляются в `list_tools()` до загрузки

### Шаг 4.3: Обновить конфигурацию для defer_loading

**Файл:** `config/tool_config.yaml`

**Обновить:**
```yaml
tools:
  # HIGH priority - всегда загружены
  search_web:
    category: web
    defer_loading: false
    priority: HIGH
  
  calculate:
    category: analysis
    defer_loading: false
    priority: HIGH
  
  get_current_datetime:
    category: context
    defer_loading: false
    priority: HIGH
  
  # MEDIUM priority - загружаются по запросу
  search_wikipedia:
    category: knowledge
    defer_loading: true
    priority: MEDIUM
  
  search_arxiv:
    category: knowledge
    defer_loading: true
    priority: MEDIUM
  
  # ... остальные инструменты с defer_loading: true
```

**Критерии успеха:**
- [ ] Критические инструменты (3-5) имеют `defer_loading: false`
- [ ] Остальные инструменты (19-21) имеют `defer_loading: true`
- [ ] Конфигурация загружается корректно

### Шаг 4.4: Обновить loader.py для поддержки defer_loading

**Файл:** `src/mcp_search_server/registry/loader.py`

**Обновить функцию `register_all_tools`:**
```python
def register_all_tools(server: Server) -> ToolRegistry:
    """Register all tools with deferred loading support."""
    registry = ToolRegistry()
    category_manager = CategoryManager()
    tool_config = load_tool_config()  # Загрузить из tool_config.yaml
    
    # Зарегистрировать все инструменты
    for tool_name, config in tool_config["tools"].items():
        defer = config.get("defer_loading", True)
        category = config.get("category")
        priority = config.get("priority", "MEDIUM")
        
        # Создать BaseTool для инструмента
        tool = create_tool_from_config(tool_name, config)
        
        # Зарегистрировать с defer флагом
        registry.register_tool(tool, defer=defer)
        
        # Если не defer - зарегистрировать в MCP сервере сразу
        if not defer:
            server.tool()(tool.execute_func)
    
    # Зарегистрировать search_tools (всегда загружен)
    from ..tools.meta import search_tools
    server.tool()(search_tools)
    
    return registry
```

**Критерии успеха:**
- [ ] Инструменты с `defer_loading: false` загружаются сразу
- [ ] Инструменты с `defer_loading: true` регистрируются как отложенные
- [ ] `search_tools` всегда доступен

### Шаг 4.5: Обновить server.py для поддержки динамической загрузки

**Файл:** `src/mcp_search_server/server.py`

**Обновить `call_tool`:**
```python
@app.call_tool()
async def call_tool(name: str, arguments: Any):
    """Handle tool calls with dynamic loading."""
    global tool_registry
    if tool_registry is None:
        tool_registry = register_all_tools(app)
    
    # Проверить, нужно ли загрузить инструмент
    if name not in tool_registry._tools:
        logger.info(f"Loading deferred tool: {name}")
        await tool_registry.load_tool(name)
        
        # Зарегистрировать в MCP сервере
        tool = tool_registry.get_tool(name)
        app.tool()(tool.execute_func)
    
    # Выполнить инструмент
    return await tool_registry.execute_tool(name, arguments)
```

**Критерии успеха:**
- [ ] Отложенные инструменты загружаются при первом вызове
- [ ] После загрузки инструмент доступен как обычный
- [ ] Логирование показывает, когда инструмент загружается

### Проверка Фазы 4

```bash
# Запустить сервер
mcp-search-server &

# Проверить список инструментов при старте
# Ожидаемый результат: только 3-5 критических инструментов + search_tools

# Вызвать search_tools для поиска инструмента
# Например: search_tools(query="wikipedia")

# Вызвать найденный инструмент (например, search_wikipedia)
# Проверить, что он загрузился и выполнился

# Проверить логи - должна быть запись "Loading deferred tool: search_wikipedia"

# Измерить потребление токенов
# До: ~24 инструмента в list_tools
# После: ~5 инструментов в list_tools (экономия 80%)
```

**Ожидаемый результат:**
- При старте загружаются только критические инструменты
- `search_tools` позволяет найти нужный инструмент
- Инструменты загружаются по требованию
- Потребление токенов снижено на 80-90%

---

## ФАЗА 5: Тестирование и документация (День 6)

### Цель
Обеспечить качество кода и обновить документацию.

### Шаг 5.1: Создать тесты для registry

**Файл:** `tests/test_registry/test_tool_registry.py`

**Тесты:**
- [ ] Регистрация инструмента
- [ ] Получение инструмента по имени
- [ ] Фильтрация по категории
- [ ] Отложенная загрузка
- [ ] Загрузка категории

**Файл:** `tests/test_registry/test_category_manager.py`

**Тесты:**
- [ ] Загрузка категорий из YAML
- [ ] Получение приоритетов
- [ ] Фильтрация по приоритету

**Файл:** `tests/test_registry/test_loader.py`

**Тесты:**
- [ ] Регистрация всех инструментов
- [ ] Регистрация категории
- [ ] Поддержка defer_loading

### Шаг 5.2: Обновить существующие тесты

**Обновить импорты в тестах:**
```python
# Было:
from mcp_search_server.tools.duckduckgo import search_duckduckgo

# Стало:
from mcp_search_server.tools.web.duckduckgo import search_duckduckgo
# или
from mcp_search_server.tools.web import search_duckduckgo
```

**Критерии успеха:**
- [ ] Все существующие тесты обновлены
- [ ] Новые тесты для registry созданы
- [ ] Покрытие тестами >= 80%

### Шаг 5.3: Обновить README.md

**Добавить секции:**

1. **Architecture** - описание модульной архитектуры
2. **Tool Categories** - таблица категорий
3. **Dynamic Loading** - объяснение defer_loading
4. **Tool Search** - как использовать search_tools

**Критерии успеха:**
- [ ] README содержит информацию об архитектуре
- [ ] Примеры использования обновлены
- [ ] Документация по категориям добавлена

### Шаг 5.4: Создать ARCHITECTURE.md

**Файл:** `ARCHITECTURE.md`

**Содержание:**
- Обзор архитектуры
- Диаграмма компонентов
- Описание каждого модуля
- Руководство по добавлению новых инструментов
- Best practices

**Критерии успеха:**
- [ ] Файл `ARCHITECTURE.md` создан
- [ ] Содержит диаграммы и примеры кода
- [ ] Объясняет, как расширять систему

### Шаг 5.5: Обновить CONTRIBUTING.md

**Добавить:**
- Как добавить новый инструмент
- Как создать новую категорию
- Правила именования и организации кода
- Требования к тестам

**Критерии успеха:**
- [ ] `CONTRIBUTING.md` обновлен
- [ ] Содержит пошаговые инструкции
- [ ] Примеры кода включены

### Проверка Фазы 5

```bash
# Запустить все тесты
pytest tests/ -v --cov=src/mcp_search_server --cov-report=term-missing

# Проверить покрытие
# Ожидаемый результат: >= 80%

# Проверить документацию
# - README.md обновлен
# - ARCHITECTURE.md создан
# - CONTRIBUTING.md обновлен

# Проверить линтинг
ruff check src/

# Проверить форматирование
black --check src/
```

**Ожидаемый результат:**
- Все тесты проходят
- Покрытие >= 80%
- Документация актуальна
- Код соответствует стандартам

---

## ФАЗА 6: Оптимизация и мониторинг (День 7)

### Цель
Добавить мониторинг, логирование и оптимизацию производительности.

### Шаг 6.1: Добавить централизованное логирование

**Файл:** `src/mcp_search_server/utils/logger.py`

**Что делает:**
- Настраивает логирование для всех модулей
- Добавляет метрики использования инструментов
- Логирует время выполнения

**Критерии успеха:**
- [ ] Централизованное логирование настроено
- [ ] Логи содержат метрики производительности
- [ ] Уровни логирования настраиваемые

### Шаг 6.2: Добавить метрики использования

**Файл:** `src/mcp_search_server/registry/metrics.py`

**Что отслеживает:**
- Количество вызовов каждого инструмента
- Время выполнения
- Частота загрузки отложенных инструментов
- Ошибки и исключения

**Критерии успеха:**
- [ ] Метрики собираются для всех инструментов
- [ ] Доступен endpoint для просмотра метрик
- [ ] Метрики сохраняются в файл

### Шаг 6.3: Добавить health check

**Файл:** `src/mcp_search_server/health.py`

**Что проверяет:**
- Доступность всех категорий
- Работоспособность критических инструментов
- Состояние кэша
- Использование памяти

**Критерии успеха:**
- [ ] Health check endpoint создан
- [ ] Проверяет все критические компоненты
- [ ] Возвращает статус в JSON

### Шаг 6.4: Оптимизация производительности

**Действия:**
- Добавить кэширование результатов инструментов
- Оптимизировать загрузку категорий
- Использовать asyncio для параллельных операций
- Добавить пулы соединений для HTTP запросов

**Критерии успеха:**
- [ ] Время отклика снижено на 20-30%
- [ ] Использование памяти оптимизировано
- [ ] Параллельные запросы обрабатываются эффективно

### Проверка Фазы 6

```bash
# Запустить сервер с метриками
mcp-search-server --enable-metrics

# Проверить health check
curl http://localhost:8000/health

# Выполнить нагрузочное тестирование
# (использовать инструмент типа locust или ab)

# Проверить метрики
curl http://localhost:8000/metrics

# Проверить логи
tail -f logs/mcp-search-server.log
```

**Ожидаемый результат:**
- Health check работает
- Метрики собираются корректно
- Производительность улучшена
- Логирование информативное

---

## Итоговая проверка всего рефакторинга

### Функциональность

```bash
# 1. Запустить сервер
mcp-search-server

# 2. Проверить список инструментов
# Ожидаемый результат: 3-5 критических инструментов + search_tools

# 3. Использовать search_tools для поиска
# Например: search_tools(query="wikipedia")

# 4. Вызвать найденный инструмент
# Например: search_wikipedia(query="Python")

# 5. Проверить, что инструмент загрузился и работает

# 6. Повторить для всех категорий
```

### Тестирование

```bash
# Запустить все тесты
pytest tests/ -v --cov=src/mcp_search_server --cov-report=html

# Проверить покрытие
open htmlcov/index.html

# Ожидаемый результат: >= 80% покрытие
```

### Качество кода

```bash
# Линтинг
ruff check src/

# Форматирование
black --check src/

# Проверка типов (опционально)
mypy src/

# Ожидаемый результат: нет ошибок
```

### Производительность

```bash
# Измерить потребление токенов
# До рефакторинга: ~24 инструмента в list_tools
# После рефакторинга: ~5 инструментов в list_tools
# Экономия: ~80%

# Измерить время запуска
time mcp-search-server --help

# Измерить время отклика
# (использовать benchmark скрипт)
```

### Документация

```bash
# Проверить наличие всех файлов документации
ls -la README.md ARCHITECTURE.md CONTRIBUTING.md

# Проверить актуальность
# - README содержит информацию о категориях
# - ARCHITECTURE объясняет новую структуру
# - CONTRIBUTING содержит инструкции по добавлению инструментов
```

---

## Критерии успеха всего рефакторинга

### Архитектура
- [x] Инструменты организованы в 6 категорий
- [x] Модульная структура с четким разделением ответственности
- [x] Система регистрации инструментов реализована
- [x] Поддержка динамической загрузки

### Производительность
- [x] Потребление токенов снижено на 80-90%
- [x] Время запуска не увеличилось
- [x] Время отклика улучшено на 20-30%
- [x] Использование памяти оптимизировано

### Качество кода
- [x] `server.py` сокращен с 2824 до ~300-400 строк
- [x] Покрытие тестами >= 80%
- [x] Нет ошибок линтинга
- [x] Код соответствует Black и Ruff стандартам

### Документация
- [x] README обновлен с информацией об архитектуре
- [x] ARCHITECTURE.md создан
- [x] CONTRIBUTING.md обновлен
- [x] Все инструменты документированы

### Обратная совместимость
- [x] Все существующие инструменты работают
- [x] API не изменился
- [x] Конфигурация Claude Desktop не требует изменений
- [x] Существующие интеграции продолжают работать

---

## Следующие шаги после рефакторинга

### Краткосрочные (1-2 недели)
1. Мониторинг использования в production
2. Сбор обратной связи от пользователей
3. Оптимизация на основе метрик
4. Исправление найденных багов

### Среднесрочные (1-2 месяца)
1. Добавление новых инструментов (цель: 50+)
2. Создание новых категорий при необходимости
3. Улучшение search_tools с ML ранжированием
4. Интеграция с другими MCP серверами

### Долгосрочные (3-6 месяцев)
1. Разделение на несколько специализированных MCP серверов
2. Создание marketplace для community инструментов
3. Добавление версионирования инструментов
4. Реализация A/B тестирования для новых функций

---

## Rollback план

Если что-то пойдет не так, вот план отката:

### Откат Фазы 4 (динамическая загрузка)
```bash
# Отключить defer_loading в tool_config.yaml
# Установить defer_loading: false для всех инструментов
```

### Откат Фазы 3 (новый server.py)
```bash
# Восстановить старый server.py из git
git checkout HEAD~1 src/mcp_search_server/server.py
```

### Откат Фазы 2 (реорганизация)
```bash
# Переместить файлы обратно
cd src/mcp_search_server/tools
mv web/* knowledge/* social/* analysis/* context/* files/* .
rmdir web knowledge social analysis context files
```

### Полный откат
```bash
# Откатиться к последнему стабильному коммиту
git reset --hard <commit-hash>
```

---

## Контрольные точки

После каждой фазы делайте коммит с тегом:

```bash
# После Фазы 1
git commit -m "Phase 1: Infrastructure setup"
git tag v2.0.0-phase1

# После Фазы 2
git commit -m "Phase 2: Tool reorganization"
git tag v2.0.0-phase2

# После Фазы 3
git commit -m "Phase 3: Server refactoring"
git tag v2.0.0-phase3

# После Фазы 4
git commit -m "Phase 4: Dynamic loading"
git tag v2.0.0-phase4

# После Фазы 5
git commit -m "Phase 5: Testing and documentation"
git tag v2.0.0-phase5

# После Фазы 6
git commit -m "Phase 6: Optimization and monitoring"
git tag v2.0.0-release
```

---

## Заключение

Этот план рефакторинга трансформирует ваш MCP-сервер из монолитного приложения в модульную, масштабируемую систему, готовую к росту до 200+ инструментов.

**Ключевые преимущества после рефакторинга:**
- 🚀 Снижение потребления токенов на 80-90%
- 📦 Модульная архитектура с четким разделением
- 🔍 Динамическая загрузка инструментов
- 📊 Мониторинг и метрики
- 📚 Актуальная документация
- ✅ Высокое покрытие тестами

**Время выполнения:** 6-7 дней
**Риск:** Низкий (поэтапный подход с rollback планом)
**Выгода:** Высокая (масштабируемость, производительность, поддержка)
