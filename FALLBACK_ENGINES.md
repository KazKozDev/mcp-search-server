# Smart Fallback Search Engines

Система умного fallback для поиска с поддержкой нескольких движков.

## Поддерживаемые движки

### 1. DuckDuckGo (Основной) ✅
- **Статус**: Работает из коробки
- **Требования**: Нет
- **Скорость**: ~1-2 сек
- **Надежность**: Высокая
- **Поддержка**: Веб + Новости

### 2. Brave Search ⚡
- **Статус**: Требует Playwright для обхода anti-bot
- **Требования**: `playwright` (опционально)
- **Скорость**: ~3-5 сек (с browser)
- **Надежность**: Средняя
- **Поддержка**: Веб + Новости

### 3. Startpage 🔒
- **Статус**: Требует Playwright
- **Требования**: `playwright` (опционально)
- **Скорость**: ~3-5 сек (с browser)
- **Надежность**: Средняя
- **Поддержка**: Веб + Новости

### 4. Qwant 🇪🇺
- **Статус**: API заблокирован
- **Требования**: Нет
- **Скорость**: N/A
- **Надежность**: Низкая
- **Поддержка**: Веб + Новости

## Установка Playwright (опционально)

Для включения Brave и Startpage с browser rendering:

```bash
# Установить Playwright
pip install playwright

# Установить браузер Firefox (рекомендуется, более стабилен на macOS)
playwright install firefox

# Альтернатива: Chromium (может быть нестабилен на некоторых системах)
playwright install chromium
```

После установки Brave и Startpage автоматически начнут использовать браузер для обхода anti-bot защиты. Система автоматически пробует Firefox первым, затем Chromium как fallback.

## Использование

### Автоматический fallback (рекомендуется)

```python
# DuckDuckGo → Brave → Startpage
results = await search_with_fallback(
    query="Python programming",
    limit=10,
    use_fallback=True  # default
)
```

### Конкретный движок

```python
# Только DuckDuckGo
results = await search_with_fallback(
    query="Python programming",
    engine="duckduckgo",
    use_fallback=False
)

# Только Brave (если Playwright установлен)
results = await search_with_fallback(
    query="Python programming",
    engine="brave",
    use_fallback=False
)
```

### Через MCP API

```python
# Auto-fallback
await call_tool('search_web', {
    'query': 'test',
    'use_fallback': True
})

# Specific engine
await call_tool('search_web', {
    'query': 'test',
    'engine': 'brave'
})
```

## Fallback Logic

```
1. DuckDuckGo (primary)
   ↓ если < 3 результатов
2. Qwant (backup)
   ↓ если < 3 результатов
3. Brave (если Playwright установлен)
   ↓ если < 3 результатов
4. Startpage (если Playwright установлен)
```

## Производительность

| Движок     | Без Playwright | С Playwright |
|------------|---------------|--------------|
| DuckDuckGo | ~1-2 сек ✅   | N/A          |
| Brave      | ❌ Заблокирован | ~3-5 сек ✅  |
| Startpage  | ❌ Заблокирован | ~3-5 сек ✅  |
| Qwant      | ❌ Заблокирован | N/A          |

## Рекомендации

### Для максимальной скорости:
- Используйте только DuckDuckGo (`use_fallback=False`)
- Не устанавливайте Playwright

### Для максимальной надежности:
- Установите Playwright
- Используйте auto-fallback (`use_fallback=True`)

### Для production:
- DuckDuckGo обеспечивает 99% надежность
- Playwright добавляет fallback для критичных случаев
- Кеширование снижает нагрузку

## Новые файлы

- `tools/search_engine_base.py` - Базовый класс
- `tools/search_manager.py` - Менеджер fallback
- `tools/unified_search.py` - Унифицированный API
- `tools/browser_engine.py` - Playwright интеграция
- `tools/brave_search.py` - Brave движок (обновлен)
- `tools/startpage_search.py` - Startpage движок
- `tools/qwant_search.py` - Qwant движок

## API параметры

### search_web

- `query` (string, required) - Поисковый запрос
- `limit` (int, default: 10) - Максимум результатов
- `mode` (enum: "web", "news", default: "web") - Режим поиска
- `timelimit` (enum: "d", "w", "m", "y", null) - Фильтр времени
- `engine` (enum: "duckduckgo", "qwant", "brave", "startpage") - Конкретный движок
- `use_fallback` (bool, default: true) - Включить fallback
- `no_cache` (bool, default: false) - Отключить кеш

## Troubleshooting

### Playwright не работает

```bash
# Переустановить Firefox (рекомендуется)
playwright install --force firefox

# Если Firefox не работает, попробуйте Chromium
playwright install --force chromium

# Проверить установку
python -c "from playwright.async_api import async_playwright; print('OK')"
```

### Brave/Startpage все равно не работают

- Убедитесь что Playwright установлен
- Установите Firefox: `playwright install firefox`
- Проверьте логи: должно быть "Using Firefox browser" или "Using Chromium browser"
- Попробуйте увеличить timeout в browser_engine.py

### Медленная работа с browser

- Это нормально, browser rendering занимает 3-5 сек
- Используйте кеш (`no_cache=False`)
- Рассмотрите использование только DuckDuckGo
