# Qwen Code — Официальные требования к агентам, скиллам и расширениям

> Извлечено из официальной документации Qwen Code (2026-10-06)
> Источники: `sub-agents.md`, `skills.md`, `extension/introduction.md`, `extension/getting-started-extensions.md`

---

## 1. Агенты (Subagents)

### 1.1 Формат файла

Агенты хранятся как Markdown-файлы (`.md`) с YAML frontmatter.

**Места хранения (по приоритету):**
| Уровень | Путь |
|---------|------|
| Проектный | `.qwen/agents/` (наивысший приоритет) |
| Пользовательский | `~/.qwen/agents/` (fallback) |
| Расширение | `<extension>/agents/` |

### 1.2 Frontmatter — Таблица полей

#### Обязательные поля

| Поле | Тип | Описание | Валидация |
|------|-----|----------|-----------|
| `name` | string | Уникальный идентификатор агента | Non-empty string, `/^[\p{L}\p{N}_:.-]+$/u` |
| `description` | string | Описание назначения агента | Non-empty string; >1000 символов → warning |

#### Опциональные поля

| Поле | Тип | По умолчанию | Описание |
|------|-----|--------------|----------|
| `model` | enum/string | `inherit` | Модель: `inherit`, `fast`, `modelId`, `authType:modelId` |
| `approvalMode` | enum | наследуется | Режим прав: `default`, `plan`, `auto-edit`, `yolo`, `bubble` |
| `tools` | string[] | все инструменты | Allowlist — агент может использовать ТОЛЬКО перечисленные |
| `disallowedTools` | string[] | пусто | Blocklist — исключает из набора инструментов |
| `maxTurns` | positive integer | без лимита | Максимальное количество ходов агента |
| `background` | boolean | `true` | По умолчанию фоновое выполнение |
| `color` | enum | — | Цвет отображения: `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan` |
| `permissionMode` | enum | — | (CC-совместимость) Маппится на `approvalMode` |
| `mcpServers` | record | — | Per-agent MCP server overrides |
| `hooks` | record | — | Per-agent hooks (PreToolUse, PostToolUse, etc.) |

#### Поля для внешних исполнителей (Codex, Claude Code)

| Поле | Тип | Описание |
|------|-----|----------|
| `executor.kind` | string | `codex` или `acp` |
| `executor.command` | string | Команда запуска |
| `executor.args` | string[] | Аргументы (опционально) |

### 1.3 Базовая структура агента

```markdown
---
name: agent-name
description: Brief description of when and how to use this agent
model: inherit          # Optional
approvalMode: auto-edit # Optional
tools:                  # Optional: allowlist
  - tool1
  - tool2
disallowedTools:        # Optional: blocklist
  - tool3
---

System prompt content goes here.
Multiple paragraphs are supported.
```

### 1.4 Model Selection

| Значение | Поведение |
|----------|-----------|
| `inherit` (или поле отсутствует) | Использует модель основной сессии |
| `fast` | Использует `fastModel` из settings.json |
| `glm-5` | Конкретная модель по ID |
| `openai:gpt-4o` | Явный provider:model |

### 1.5 Approval Modes

| Режим | Поведение |
|-------|-----------|
| `default` | Интерактивное одобрение каждого вызова |
| `plan` | Только анализ, без изменений |
| `auto-edit` | Авто-одобрение (рекомендуется для агентов) |
| `yolo` | Все авто-одобрено, включая деструктивные |
| `bubble` | Одобрение через родительскую сессию |

**Наследование:** Если parent в `yolo`/`auto-edit` → агент наследует. Если parent в `plan` → агент остаётся в `plan`.

### 1.6 Tool Configuration

- **`tools` (allowlist):** Если указан — агент может использовать ТОЛЬКО эти инструменты
- **`disallowedTools` (blocklist):** Исключает инструменты из полного набора
- Если указаны оба — сначала применяется allowlist, потом blocklist
- MCP инструменты подчиняются тем же правилам
- `disallowedTools` поддерживает паттерны уровня сервера: `mcp__server` блокирует ВСЕ инструменты от этого сервера

### 1.7 Системный промпт

- Располагается после закрывающего `---` frontmatter
- Поддерживаются множественные параграфы
- Рекомендуется включать: специализацию, пошаговый подход, стандарты вывода
- >10,000 символов → warning

### 1.8 Ограничения агентов

| Ограничение | Описание |
|-------------|----------|
| Нет `ask_user_question` | Агенты не могут напрямую спрашивать пользователя |
| Нет контекста родителя | Именованные агенты стартуют без истории родительского разговора |
| Fork не может делегировать | Fork-потомки не могут запускать дальнейших подагентов |
| Нет worktree для fork | Fork разделяют рабочую директорию родителя |
| Soft limits | Description >1000 символов → warning; System prompt >10,000 → warning |
| External executors | Не поддерживают: model overrides, tool lists, hooks, maxTurns, fork history, teams, workflows |

### 1.9 Best Practices для агентов

1. **Single Responsibility** — каждый агент для одной чёткой задачи
2. **Clear Specialization** — конкретная экспертиза, не широкие способности
3. **Actionable Descriptions** — описание должно чётко указывать КОГДА использовать
4. **System Prompt:**
   - Конкретная экспертиза (список областей)
   - Пошаговый подход (нумерованные шаги)
   - Стандарты вывода (формат, качество)
5. **Tool Restrictions** — ограничивать инструменты для безопасности и фокуса
6. **Не включать секреты** — никогда не хранить credentials в конфигурации
7. **Включать "use PROACTIVELY"** в description для более активного делегирования

---

## 2. Скиллы (Skills)

### 2.1 Формат файла

Скилл — это директория с обязательным файлом `SKILL.md` внутри.

**Места хранения:**
| Уровень | Путь |
|---------|------|
| Пользовательский | `~/.qwen/skills/<skill-name>/SKILL.md` |
| Проектный | `.qwen/skills/<skill-name>/SKILL.md` |
| Расширение | `<extension>/skills/<skill-name>/SKILL.md` |
| Bundled | Поставляются с Qwen Code |

### 2.2 Frontmatter — Таблица полей

#### Обязательные поля

| Поле | Тип | Описание | Валидация |
|------|-----|----------|-----------|
| `name` | string | Имя скилла | Non-empty, `/^[\p{L}\p{N}_:.-]+$/u` |
| `description` | string | Описание что делает и когда использовать | Non-empty string |

#### Опциональные поля

| Поле | Тип | По умолчанию | Описание |
|------|-----|--------------|----------|
| `priority` | number | `0` | Приоритет в `/skills` listing (higher = раньше). Не влияет на `/` autocomplete |
| `paths` | string[] | — | Glob-паттерны для активации скилла только при работе с_matching_ файлами |
| `user-invocable` | boolean | `true` | Если `false` — скрыт от прямого вызова `/skill-name` |
| `disable-model-invocation` | boolean | `false` | Если `true` — скрыт от модели, но доступен пользователю |
| `hooks` | record | — | Детерминированные правила (PreToolUse hooks) |
| `allowedTools` | — | — | Расширение набора инструментов при вызове скилла |

### 2.3 Базовая структура SKILL.md

```markdown
---
name: your-skill-name
description: Brief description of what this Skill does and when to use it
priority: 10
---

# Your Skill Name

## Instructions
Provide clear, step-by-step guidance for Qwen Code.

## Examples
Show concrete examples of using this Skill.
```

### 2.4 Структура директории скилла

```
my-skill/
├── SKILL.md              (обязательно)
├── reference.md          (опционально)
├── examples.md           (опционально)
├── scripts/
│   └── helper.py         (опционально)
└── templates/
    └── template.txt      (опционально)
```

### 2.5 Именование скиллов из расширений

Скиллы из расширений регистрируются как `<extensionName>:<name>`:
- Скилл `pdf` в расширении `rust` → `rust:pdf`
- Вызов: `/rust:pdf`
- Модель вызывает: `Skill { skill: "rust:pdf" }`
- Префикс добавляется при загрузке, НЕ записывается в файл

### 2.6 Path Gating (`paths:`)

```yaml
---
name: tsx-helper
description: React TSX component helper
paths:
  - 'src/**/*.tsx'
  - 'packages/*/src/**/*.tsx'
---
```

- Скилл не виден модели, пока не затронут matching файл
- После активации — активен до конца сессии
- Globs через picomatch, относительно корня проекта
- Пользователь может вызвать через `/skill-name` независимо от активации

### 2.7 Hooks в скиллах

```yaml
---
name: gated-skill
description: Calls the downstream CLI
hooks:
  PreToolUse:
    - matcher: run_shell_command
      hooks:
        - type: command
          command: '"$QWEN_SKILL_ROOT/scripts/gate-session-id.sh"'
---
```

- Hooks — детерминированные правила, не зависят от модели
- `$QWEN_SKILL_ROOT` — путь к директории скилла
- Выход с кодом `2` → блокирует вызов инструмента
- Поддерживаются для project, user, bundled скиллов; **НЕ для extension скиллов**
- Регистрация идемпотентна
- Работают через shell: `bash` на Linux/macOS

### 2.8 Best Practices для скиллов

1. **Focused** — один скилл = одна способность
   - ✅ "PDF form filling", "Excel analysis"
   - ❌ "Document processing" (слишком широко)
2. **Specific Description** — включать ЧТО делает и КОГДА использовать
   - ✅ "Analyze Excel spreadsheets, create pivot tables, and generate charts. Use when working with Excel files, spreadsheets, or .xlsx data."
   - ❌ "Helps with documents"
3. **Тестирование** — проверять активацию, ясность инструкций, edge cases
4. **YAML синтаксис** — открывающий `---` на строке 1, закрывающий `---` перед Markdown, без tabs
5. **Поддержка файлов** — ссылаться на вспомогательные файлы из SKILL.md
6. **Prefer lowercase ASCII with hyphens** для shareable имён (e.g. `tsx-helper`)

### 2.9 Ограничения скиллов

| Ограничение | Описание |
|-------------|----------|
| `name` валидация | Только Unicode letters/digits, `_`, `:`, `.`, `-`. Без whitespace, slashes, brackets |
| Extension hooks | Extension-скиллы НЕ поддерживают `hooks:` — используйте manifest-level hooks |
| Path gating | Только для model discovery; пользователь может вызвать напрямую всегда |
| Auto-skill maintenance | Через 30 дней без использования → stale; через 90 дней → archived |

---

## 3. Расширения (Extensions)

### 3.1 Структура расширения

```
my-extension/
├── qwen-extension.json   (обязательно — манифест)
├── QWEN.md               (опционально — контекст)
├── commands/              (опционально — кастомные команды)
│   └── deploy.md
├── skills/                (опционально — кастомные скиллы)
│   └── pdf-processor/
│       └── SKILL.md
├── agents/                (опционально — кастомные агенты)
│   └── testing-expert.md
├── workflows/             (опционально — workflow скрипты)
│   └── deep-research.js
├── rules/                 (опционально — условные правила)
│   └── charting.md
└── dist/                  (опционально — скомпилированный код)
    └── example.js
```

### 3.2 `qwen-extension.json` — Формат

```json
{
  "name": "my-extension",
  "version": "1.0.0",
  "mcpServers": {
    "my-server": {
      "command": "node my-server.js"
    }
  },
  "channels": {
    "my-platform": {
      "entry": "dist/index.js",
      "displayName": "My Platform Channel"
    }
  },
  "contextFileName": "QWEN.md",
  "commands": "commands",
  "skills": "skills",
  "agents": "agents",
  "workflows": "workflows",
  "settings": [
    {
      "name": "API Key",
      "description": "Your API key for the service",
      "envVar": "MY_API_KEY",
      "sensitive": true
    }
  ]
}
```

#### Обязательные поля

| Поле | Тип | Описание | Валидация |
|------|-----|----------|-----------|
| `name` | string | Уникальное имя расширения | Lowercase/numbers, dashes (не underscores/spaces) |
| `version` | string | Версия | Семантическое версионирование |

#### Опциональные поля

| Поле | Тип | По умолчанию | Описание |
|------|-----|--------------|----------|
| `mcpServers` | record | — | MCP серверы (ключ = имя сервера) |
| `channels` | record | — | Кастомные channel adapters |
| `contextFileName` | string | `"QWEN.md"` | Имя файла контекста |
| `commands` | string | `"commands"` | Директория команд |
| `skills` | string | `"skills"` | Директория скиллов |
| `agents` | string | `"agents"` | Директория агентов |
| `workflows` | string/string[] | `"workflows"` | Директория workflow |
| `settings` | array | — | Настройки (API keys, credentials) |

### 3.3 Settings

Каждый элемент `settings[]`:

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Отображаемое имя |
| `description` | string | Описание назначения |
| `envVar` | string | Имя переменной окружения |
| `sensitive` | boolean | Скрыть значение (API keys, passwords) |

Уровни хранения:
- **User level** (default): `~/.qwen/.env`
- **Workspace level**: `.qwen/.env` (приоритет выше)

### 3.4 Как регистрируются агенты и скиллы

**Агенты:**
- Обнаруживаются из `agents/` директории расширения
- Формат: `.yaml` или `.md` файлы
- Появляются в `/agents manage` → "Extension Agents"
- Нельзя редактировать напрямую (только через исходник расширения)

**Скиллы:**
- Обнаруживаются из `skills/` директории расширения
- Регистрируются как `<extensionName>:<name>` (e.g. `gcp:pdf-processor`)
- Доступны через `/gcp:pdf-processor`
- Два расширения с одинаковым именем скилла → два отдельных скилла

**Команды:**
- Обнаруживаются из `commands/` директории
- `.md` файлы (TOML deprecated, но поддерживается)
- Именование: `/deploy` или `/gcs:sync` (по структуре файлов)

### 3.5 QWEN.md — Контекст расширения

> **ВАЖНО:** Это самое дорогое место для инструкций. Контекст добавляется в КАЖДЫЙ запрос КАЖДОЙ сессии.

**Рекомендации:**
- Хранить только факты, которые всегда истинны
- Идентичность расширения, словарь, жёсткие ограничения
- Сценарное руководство → в скилл, не в QWEN.md
- 9 расширений = ~9,989 токенов (21% контекста) в benchmark-сессии

### 3.6 Workflow скрипты

```js
export const meta = {
  name: 'deep-research',       // required: lowercase, digits, hyphens, ≤41 chars
  description: 'Researches...', // required: ≤500 chars
  whenToUse: 'When the user...', // optional: для model discovery
};
```

- Только `.js` файлы в корне `workflows/`
- Скрипты >256 KiB → пропущены
- Без валидного `meta` → пропущены
- `whenToUse` без него → модель не видит workflow

### 3.7 Rules (условные правила)

```markdown
---
description: How this project charts data
paths:
  - 'src/**/*.chart.ts'
---

Use the palette from `theme/charts.ts`.
```

- **Обязательно условные** — правило без `paths:` пропускается
- Появляются в промпте с меткой владельца: `my-extension:rules/charting.md`

---

## 4. Сводные таблицы

### 4.1 Обязательные поля для агентов

| Поле | Обязательность | Формат |
|------|---------------|--------|
| `name` | ✅ Обязательно | YAML frontmatter, regex `/^[\p{L}\p{N}_:.-]+$/u` |
| `description` | ✅ Обязательно | YAML frontmatter, non-empty string |
| System prompt | ✅ Обязательно | Markdown после `---` |

### 4.2 Обязательные поля для скиллов

| Поле | Обязательность | Формат |
|------|---------------|--------|
| `name` | ✅ Обязательно | YAML frontmatter, regex `/^[\p{L}\p{N}_:.-]+$/u` |
| `description` | ✅ Обязательно | YAML frontmatter, non-empty string |
| `SKILL.md` | ✅ Обязательно | Файл в директории скилла |

### 4.3 Обязательные поля для расширений

| Поле | Обязательность | Формат |
|------|---------------|--------|
| `name` | ✅ Обязательно | `qwen-extension.json`, lowercase + dashes |
| `version` | ✅ Обязательно | `qwen-extension.json`, semver |

---

## 5. Общие Best Practices

### Агенты
1. Single Responsibility — одна задача на агента
2. Clear Specialization — конкретная экспертиза
3. Actionable Descriptions — когда использовать
4. Ограничивать tools для безопасности
5. Не включать секреты в конфигурацию
6. Пошаговый подход в system prompt
7. Стандарты вывода в system prompt

### Скиллы
1. Один скилл = одна способность
2. Конкретное описание с триггерами
3. Тестировать активацию
4. Валидный YAML синтаксис
5. Lowercase ASCII + hyphens для shareable имён
6. Поддержка вспомогательными файлами

### Расширения
1. Короткий QWEN.md — только always-true факты
2. Сценарное руководство → в скиллы
3. `name` в lowercase + dashes
4. Настройки через `settings[]` с `sensitive: true`
5. `${extensionPath}` для путей в MCP серверах
6. Hooks только для project/user/bundled (не extension skills)

---

## 6. Примеры корректного формата

### 6.1 Корректный агент

```markdown
---
name: testing-expert
description: Writes comprehensive unit tests, integration tests, and handles test automation with best practices
model: inherit
approvalMode: auto-edit
tools:
  - read_file
  - write_file
  - run_shell_command
---

You are a testing specialist focused on creating high-quality, maintainable tests.

Your expertise includes:
- Unit testing with appropriate mocking and isolation
- Integration testing for component interactions
- Test-driven development practices

For each testing task:
1. Analyze the code structure and dependencies
2. Identify key functionality, edge cases, and error conditions
3. Create comprehensive test suites with descriptive names
4. Include proper setup/teardown and meaningful assertions

Always follow testing best practices for the detected language and framework.
```

### 6.2 Корректный скилл

```markdown
---
name: pdf-processor
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDFs, forms, or document extraction.
priority: 10
---

# PDF Processor

## Instructions
Provide clear, step-by-step guidance for working with PDF files.

## Examples
- "Extract text from this PDF"
- "Fill out this PDF form"
```

### 6.3 Корректное расширение (`qwen-extension.json`)

```json
{
  "name": "my-extension",
  "version": "1.0.0",
  "contextFileName": "QWEN.md",
  "commands": "commands",
  "skills": "skills",
  "agents": "agents",
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["${extensionPath}${/}dist${/}server.js"],
      "cwd": "${extensionPath}"
    }
  },
  "settings": [
    {
      "name": "API Key",
      "description": "Your API key for the service",
      "envVar": "MY_API_KEY",
      "sensitive": true
    }
  ]
}
```

---

## 7. Ключевые отличия: Агенты vs Скиллы

| Характеристика | Агент (Subagent) | Скилл (Skill) |
|----------------|-----------------|---------------|
| Формат | `.md` с frontmatter | Директория с `SKILL.md` |
| Вызов | Автоматическое делегирование или явное указание | Model-invoked (модель решает) или `/skill-name` |
| Контекст | Изолированный (своя история) | В контексте текущей сессии |
| Инструменты | Настраиваемый allowlist/blocklist | Наследует + может расширить через `allowedTools` |
| Выполнение | Автономное, фоновое или foreground | В рамках текущего разговора |
| Хуки | Per-agent hooks | Per-skill hooks (не для extension) |
| Best for | Специализированные задачи (тестирование, рефакторинг) | Модульные способности (PDF, Excel, Git) |

---

## 8. Переменные и шаблоны

| Переменная | Где используется | Описание |
|-----------|-----------------|----------|
| `${extensionPath}` | `qwen-extension.json` | Абсолютный путь к директории расширения |
| `${/}` | `qwen-extension.json` | Разделитель путей (кросс-платформенный) |
| `$QWEN_SKILL_ROOT` | Skill hooks | Путь к директории скилла |

---

*Документ создан на основе официальной документации Qwen Code.*
