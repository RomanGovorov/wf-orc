# Claude Code — Официальные требования к агентам, скиллам и расширениям

> Извлечено из официальной документации Claude Code (2026-10-06)
> Источники: code.claude.com/docs/en/skills, code.claude.com/docs/en/sub-agents, code.claude.com/docs/en/plugins/overview, code.claude.com/docs/en/plugins/manifest-reference

---

## 1. Агенты (Subagents)

### 1.1 Формат файла

Агенты хранятся как Markdown-файлы (`.md`) с YAML frontmatter.

**Места хранения (по приоритету):**
| Приоритет | Уровень | Путь |
|-----------|---------|------|
| 1 (высший) | Managed settings | `.claude/agents/` в директории managed settings |
| 2 | CLI flag | `--agents` (JSON при запуске) |
| 3 | Проектный | `.claude/agents/` |
| 4 | Пользовательский | `~/.claude/agents/` |
| 5 (низший) | Плагин | `<plugin>/agents/` |

### 1.2 Frontmatter — Таблица полей

#### Обязательные поля

| Поле | Тип | Описание | Валидация |
|------|-----|----------|-----------|
| `name` | string | Уникальный идентификатор агента | Не может содержать `:`, не может начинаться с `-` |
| `description` | string | Когда Claude должен делегировать задачи этому агенту | Non-empty string |

**Важно:** Файлы без `name` или без `description` пропускаются с записью в debug log.

#### Опциональные поля

| Поле | Тип | По умолчанию | Описание |
|------|-----|--------------|----------|
| `tools` | string \| string[] | все доступные | Allowlist — comma-separated или YAML list. Если список пуст — агент не запускается |
| `disallowedTools` | string \| string[] | пусто | Blocklist — исключает из унаследованного/заданного набора |
| `model` | string | inherit | `sonnet`, `opus`, `haiku`, `fable`, полный ID модели, или `inherit` |
| `permissionMode` | string | наследуется | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns` | integer | без лимита | Максимальное количество ходов. При достижении — partial output |
| `skills` | string[] | пусто | Skills для предзагрузки в контекст агента |
| `mcpServers` | array | пусто | MCP серверы (inline определения или ссылки). Игнорируется для plugin-агентов |
| `hooks` | object | пусто | Lifecycle hooks. Игнорируется для plugin-агентов |
| `memory` | string | — | `user`, `project`, или `local` — cross-session обучение |
| `background` | boolean | `false` | `true` — всегда в фоне, даже если Claude просит foreground |
| `omitClaudeMd` | boolean | `false` | Запуск без CLAUDE.md файлов (v2.1.271+) |
| `effort` | string | inherit | `low`, `medium`, `high`, `xhigh`, `max` |
| `isolation` | string | — | `worktree` — запуск в изолированном git worktree |
| `color` | string | — | `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan` |
| `initialPrompt` | string | — | Авто-отправка как первый user turn (только для `--agent`) |
| `experimental` | object | — | `cacheTtl`: `5m` или `1h` для prompt cache lifetime (v2.1.248+) |

### 1.3 Базовая структура агента

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. When invoked, analyze the code and provide
specific, actionable feedback on quality, security, and best practices.
```

### 1.4 Model Selection

| Значение | Поведение |
|----------|-----------|
| `inherit` (или поле отсутствует) | Использует модель основной сессии |
| `sonnet`, `opus`, `haiku`, `fable` | Алиас модели |
| `claude-opus-5-5` | Полный ID модели |
| `inherit` | Явно наследует модель сессии |

**Порядок резолвинга модели:**
1. Per-invocation `model` параметр
2. Frontmatter `model` агента
3. `CLAUDE_CODE_SUBAGENT_MODEL` env var
4. Модель основного разговора

### 1.5 Permission Modes

| Режим | Поведение |
|-------|-----------|
| `default` | Стандартное интерактивное одобрение |
| `acceptEdits` | Авто-одобрение редактирования |
| `auto` | Полная автоматизация через classifier |
| `dontAsk` | Не запрашивать подтверждения |
| `bypassPermissions` | Обход всех проверок |
| `plan` | Только анализ, без изменений |

**Наследование:** Если основной разговор в `bypassPermissions`, `acceptEdits` или `auto` — агент наследует этот режим, игнорируя `permissionMode`.

### 1.6 Tool Configuration

**Доступные инструменты для субагентов:**
- **Foreground:** все встроенные + MCP инструменты
- **Background:** ограниченный набор: `Read`, `Grep`, `Glob`, `LSP`, `Bash`, `PowerShell`, `Edit`, `Write`, `NotebookEdit`, `WebFetch`, `WebSearch`, `TodoWrite`, `Skill`, `ToolSearch`, `EnterWorktree`, `ExitWorktree`, `Monitor`, `TaskStop`, `SendMessage`, `Artifact`

**Всегда удаляются из субагентов:**
- `Agent` (на depth limit)
- `AskUserQuestion`
- `EndConversation`
- `EnterPlanMode`
- `ExitPlanMode` (кроме `permissionMode: plan`)
- `ScheduleWakeup`
- `WaitForMcpServers`
- `Workflow`

**Паттерны MCP:** `mcp__<server>` или `mcp__<server>__*` — все инструменты от сервера.

### 1.7 Best Practices для агентов

1. **Описание:** пишите чёткое описание, чтобы Claude знал, когда делегировать задачи
2. **Краткость описаний:** суммарно не более 15,000 tokens для всех пользовательских агентов (иначе warning при старте)
3. **Специализация:** создавайте агентов для конкретных задач с фокусированными system prompts
4. **Инструменты:** ограничивайте `tools` для безопасности (read-only для исследовательских агентов)
5. **Модели:** используйте `haiku` для простых задач, `sonnet` для стандартных, `opus` для сложных
6. **Isolation:** используйте `isolation: worktree` для агентов, которые могут модифицировать файлы
7. **Рекурсия:** агенты могут порождать субагенты (с depth limit)
8. **Memory:** используйте `memory` для cross-session обучения

### 1.8 Ограничения агентов

- Субагенты НЕ могут спрашивать пользователя напрямую (`AskUserQuestion` удалён)
- Плагин-агенты НЕ поддерживают `hooks`, `mcpServers`, `permissionMode`
- Background субагенты имеют ограниченный набор инструментов
- `name` не может содержать `:` (зарезервировано для plugin-scoped identifiers)
- Файлы без `name` или `description` пропускаются
- YAML должен парситься — иначе файл пропускается

---

## 2. Скиллы (Skills)

### 2.1 Формат файла

Скиллы хранятся как директория с файлом `SKILL.md` внутри.

**Места хранения:**
| Уровень | Путь | Загружается в |
|---------|------|---------------|
| Enterprise | `.claude/skills/<name>/SKILL.md` в managed settings | Все пользователи |
| Personal | `~/.claude/skills/<name>/SKILL.md` | Все проекты |
| Project | `.claude/skills/<name>/SKILL.md` | Текущий репозиторий |
| Nested | `<subdir>/.claude/skills/<name>/SKILL.md` | Сессии в subdir |
| Additional dir | `.claude/skills/<name>/SKILL.md` в `--add-dir` | Текущая сессия |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Где включён плагин |
| claude.ai | synced skills | Cowork, cloud, terminal sessions |

**Стандарт:** Claude Code skills следуют открытому стандарту [Agent Skills](https://agentskills.io).

### 2.2 Frontmatter — Таблица полей

**Все поля опциональны.** Рекомендуется только `description`.

| Поле | Обязательность | Тип | Описание |
|------|----------------|-----|----------|
| `name` | Нет | string | Имя команды в `/` меню. По умолчанию — имя директории |
| `description` | Рекомендуется | string | Что делает скилл и когда использовать. Claude решает, когда загружать автоматически. Макс 1,536 символов (вместе с `when_to_use`) |
| `when_to_use` | Нет | string | Дополнительный контекст для авто-вызова. Добавляется к `description` |
| `argument-hint` | Нет | string | Подсказка для autocomplete: `[issue-number]` |
| `arguments` | Нет | string \| string[] | Именованные позиционные аргументы для `$name` подстановки |
| `disable-model-invocation` | Нет | boolean | `true` — запретить Claude авто-вызов. Default: `false` |
| `user-invocable` | Нет | boolean | `false` — только Claude может вызывать. Default: `true` |
| `allowed-tools` | Нет | string \| string[] | Инструменты, которые можно использовать без запроса разрешения |
| `disallowed-tools` | Нет | string \| string[] | Инструменты, удалённые из пула на время выполнения скилла |
| `model` | Нет | string | Модель для этого скилла. С `context: fork` — модель fork-агента |
| `effort` | Нет | string | `low`, `medium`, `high`, `xhigh`, `max` |
| `context` | Нет | string | `fork` — запуск в изолированном субагенте |
| `agent` | Нет | string | Тип субагента при `context: fork` |
| `background` | Нет | boolean | Только с `context: fork`. `false` — ждать результат. Default: `true` (v2.1.218+) |
| `hooks` | Нет | object | Hooks, регистрируемые при вызове скилла |
| `paths` | Нет | string \| string[] | Glob паттерны для ограничения активации |
| `shell` | Нет | string | `bash` (default) или `powershell` для inline shell commands |
| `metadata` | Нет | object | Free-form key-value данные для внешних инструментов |
| `license` | Нет | string | Лицензия (Agent Skills spec) |
| `compatibility` | Нет | string | Требования к окружению (Agent Skills spec, макс 500 символов) |

### 2.3 Базовая структура скилла

```yaml
---
name: my-skill
description: What this skill does and when to use it
disable-model-invocation: true
allowed-tools: Read Grep
---

## Instructions

Your skill instructions here...
```

### 2.4 Структура директории скилла

```
my-skill/
├── SKILL.md              (обязательно — инструкции)
├── reference.md          (опционально — справочные материалы)
├── examples.md           (опционально — примеры)
└── scripts/
    └── helper.py         (опционально — утилиты)
```

### 2.5 Динамический контекст (Dynamic Context Injection)

Синтаксис `` !`<command>` `` выполняет shell-команды перед отправкой Claude:

```markdown
## Current changes
!`git diff HEAD`

## Environment
```!
node --version
git status --short
```
```

**Правила:**
- `!` должен быть в начале строки или после пробела
- Многокомандные блоки: fenced code block с ` ```! `
- При ошибке команды — abort всего скилла
- `disableSkillShellExecution: true` в settings отключает выполнение

### 2.6 String Substitutions

| Переменная | Описание |
|------------|----------|
| `$ARGUMENTS` | Все аргументы при вызове |
| `$ARGUMENTS[N]` | Аргумент по индексу (0-based) |
| `$N` | Shorthand для `$ARGUMENTS[N]` |
| `$name` | Именованный аргумент из `arguments` |
| `${CLAUDE_SESSION_ID}` | ID текущей сессии |
| `${CLAUDE_EFFORT}` | Текущий effort level |
| `${CLAUDE_SKILL_DIR}` | Директория SKILL.md |
| `${CLAUDE_PROJECT_DIR}` | Корень проекта |
| `${CLAUDE_PLUGIN_ROOT}` | Директория плагина (только plugin skills) |
| `${CLAUDE_PLUGIN_DATA}` | Persistent data плагина (только plugin skills) |

### 2.7 Управление вызовами

| Frontmatter | Пользователь | Claude | Когда загружается |
|-------------|-------------|--------|-------------------|
| (default) | ✅ | ✅ | Description всегда, full content при вызове |
| `disable-model-invocation: true` | ✅ | ❌ | Description не в контексте, full content при вызове |
| `user-invocable: false` | ❌ | ✅ | Description всегда, full content при вызове |

### 2.8 Best Practices для скиллов

1. **Краткость:** SKILL.md до 500 строк, подробные материалы — в отдельные файлы
2. **Описание:** пишите ключевой use case первым — `description` + `when_to_use` обрезается до 1,536 символов
3. **Reference vs Task:** reference-контент (конвенции, паттерны) — inline; task-контент (deploy, commit) — с `disable-model-invocation: true`
4. **Токены:** каждый line скилла — повторяющаяся стоимость токенов. Будьте лаконичны
5. **Поддержка файлов:** ссылайтесь на вспомогательные файлы из SKILL.md
6. **Dynamic context:** используйте `` !`command` `` для актуальных данных (diff, status)
7. **Изоляция:** `context: fork` для ресурсоёмких задач
8. **Путь к скриптам:** используйте `${CLAUDE_SKILL_DIR}` для ссылок на bundled scripts
9. **Безопасность:** ревьюьте `allowed-tools` в репозиторийных скиллах

### 2.9 Ограничения скиллов

- `name` не может быть `synced` или `anthropic-skills*` (зарезервировано)
- YAML должен парситься — иначе скилл загружается без полей
- Frontmatter читается только если `---` на первой строке файла
- Нераспознанные поля игнорируются без ошибки
- `description` + `when_to_use` обрезаются до 1,536 символов
- Shell commands abort весь скилл при ошибке (exit code ≠ 0)
- Synced skills (claude.ai) не выполняют `!` команды на локальной машине
- Plugin skills: `allowed-tools` может игнорироваться при `allowManagedPermissionRulesOnly`

### 2.10 Agent Skills Standard (кросс-платформенность)

Для использования вне Claude Code (claude.ai uploads, Skills API) доступны только:
- `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`

Остальные поля — расширения Claude Code.

---

## 3. Расширения / Плагины (Plugins)

### 3.1 Структура плагина

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Manifest (обязательно)
├── skills/
│   └── review/
│       └── SKILL.md         # Skill
├── agents/
│   └── reviewer.md          # Agent
├── hooks/
│   └── hooks.json           # Hooks
├── .mcp.json                # MCP серверы
└── ...                      # Другие компоненты
```

### 3.2 Manifest (`plugin.json`) — Таблица полей

#### Обязательные поля

| Поле | Тип | Описание | Валидация |
|------|-----|----------|-----------|
| `name` | string | Идентификатор плагина | kebab-case. Без пробелов, `@`, `:`, path separators. Префикс для всех компонентов |

#### Опциональные поля

| Поле | Тип | Описание |
|------|-----|----------|
| `$schema` | string | JSON Schema URL для editor autocomplete |
| `displayName` | string | Имя для UI (может содержать пробелы) |
| `version` | string | Версия (не проверяется по semver) |
| `description` | string | Краткое описание |
| `author` | object | `{ name (required), email, url }` |
| `homepage` | string | URL документации (валидный URL) |
| `repository` | string | URL репозитория |
| `license` | string | SPDX identifier (MIT, Apache-2.0) |
| `keywords` | string[] | Теги для обнаружения |
| `metadata` | object | Free-form данные (v2.1.222+) |
| `icon` | string | Путь к изображению (для Directory listing) |
| `documentationUrl` | string | HTTPS URL документации |
| `supportUrl` | string | HTTPS URL поддержки |
| `privacyPolicyUrl` | string | HTTPS URL privacy policy |
| `termsOfServiceUrl` | string | HTTPS URL ToS |
| `defaultEnabled` | boolean | Включён ли по умолчанию. Default: `true` |
| `dependencies` | array | Зависимости: `"name"`, `"name@marketplace"`, или `{ name, marketplace, version }` |
| `settings` | object | Настройки (только `agent` и `subagentStatusLine`) |
| `userConfig` | object | Схема для пользовательского ввода |
| `types` | string | Путь к `.d.ts` для mods |
| `channels` | array | Message channels → MCP servers |

#### Component Path поля

| Поле | Тип | Поведение |
|------|-----|-----------|
| `skills` | string \| string[] | **Добавляет** к дефолтному `skills/` сканированию |
| `commands` | string \| string[] \| object | **Заменяет** дефолтное `commands/` сканирование |
| `agents` | string \| string[] | **Заменяет** дефолтное `agents/` сканирование. Только `.md` файлы |
| `hooks` | string \| object \| array | **Сливается** с `hooks/hooks.json` |
| `mcpServers` | string \| object \| array | **Сливается** с `.mcp.json` |
| `lspServers` | string \| object \| array | **Сливается** с `.lsp.json` |
| `outputStyles` | string \| string[] | **Заменяет** дефолтное `output-styles/` |
| `workflows` | string \| string[] | **Заменяет** дефолтное `workflows/` |
| `experimental.themes` | string \| string[] | **Заменяет** дефолтное `themes/` |
| `experimental.monitors` | string \| array | **Заменяет** дефолтное `monitors/monitors.json` |
| `experimental.evals` | string \| string[] | **Заменяет** дефолтное `evals/` |

### 3.3 Компоненты плагина

| Компонент | Файл/Директория | Как регистрируется |
|-----------|-----------------|-------------------|
| Skills | `skills/<name>/SKILL.md` | `/plugin-name:skill-name` |
| Agents | `agents/<name>.md` | Claude делегирует задачи |
| Commands | `commands/<name>.md` | `/plugin-name:command-name` |
| Hooks | `hooks/hooks.json` | Выполняются на lifecycle events |
| MCP Servers | `.mcp.json` | Инструменты подключаются при включённом плагине |
| LSP Servers | `.lsp.json` | Language servers |
| Output Styles | `output-styles/` | Стили вывода |
| Workflows | `workflows/` | Dynamic workflows (`.js`) |
| Themes | `themes/` | Темы оформления |
| Monitors | `monitors/monitors.json` | Фоновые мониторы |
| Executables | `bin/` | Добавляются в PATH для Bash tool |

### 3.4 Environment Variables

| Переменная | Значение |
|------------|----------|
| `${CLAUDE_PLUGIN_ROOT}` | Абсолютный путь установленной версии плагина |
| `${CLAUDE_PLUGIN_DATA}` | `~/.claude/plugins/data/<id>/` — persistent storage |
| `${CLAUDE_PROJECT_DIR}` | Корень проекта |

### 3.5 User Configuration Schema (`userConfig`)

| Поле | Тип | Обязательность | Описание |
|------|-----|----------------|----------|
| `type` | string | **Да** | `string`, `number`, `boolean`, `directory`, `file` |
| `title` | string | **Да** | Label в диалоге конфигурации |
| `description` | string | **Да** | Help text |
| `required` | boolean | Нет | Если `true` — пустые значения отклоняются |
| `default` | any | Нет | Значение по умолчанию |
| `options` | string[] | Нет | Фиксированный список значений (v2.1.271+) |
| `multiple` | boolean | Нет | Массив строк (для `type: string`) |
| `sensitive` | boolean | Нет | Маскированный ввод, secure store |
| `min` / `max` | number | Нет | Границы для `type: number` |

### 3.6 Best Practices для плагинов

1. **Имя:** kebab-case, без зарезервированных префиксов (`claude-`, `anthropic-`)
2. **Валидация:** `claude plugin validate ./my-plugin` перед публикацией
3. **Контекст:** name + description каждого компонента загружаются в КАЖДОМ turn — держите краткими
4. **Lazy loading:** полный текст скилла/агента загружается только при использовании
5. **Доверие:** плагины работают с привилегиями пользователя — ревьюйте перед установкой
6. **Persistent data:** используйте `${CLAUDE_PLUGIN_DATA}` для данных, переживающих обновления
7. **Изоляция компонентов:** используйте `${CLAUDE_PLUGIN_ROOT}` для bundled scripts
8. **Масштаб:** один плагин = один логический unit (набор связанных skills/agents/hooks)
9. **Dependencies:** указывайте зависимости через `dependencies` поле
10. **Разработка:** `claude --plugin-dir /path/to/plugin` для локальной разработки

### 3.7 Ограничения плагинов

- Только `name` обязателен в manifest
- Нераспознанные top-level поля удаляются с warning
- Нераспознанные поля в strict objects (`userConfig`, `channels`) → ошибка загрузки
- Пути должны быть относительными, начинаться с `./`, без `..` traversal
- Плагин-агенты НЕ поддерживают `hooks`, `mcpServers`, `permissionMode`
- `name` в kebab-case обязательно
- `${user_config.*}` отклоняется в shell-form hook commands, monitor commands, MCP `headersHelper`

---

## 4. Сравнение Claude Code и Qwen Code

### 4.1 Агенты

| Аспект | Claude Code | Qwen Code |
|--------|-------------|-----------|
| **Формат** | Markdown + YAML frontmatter | Markdown + YAML frontmatter |
| **Обязательные поля** | `name`, `description` | `name`, `description` |
| **Хранение** | `.claude/agents/`, `~/.claude/agents/` | `.qwen/agents/`, `~/.qwen/agents/` |
| **Model** | `sonnet`, `opus`, `haiku`, `fable`, ID, `inherit` | `inherit`, `fast`, modelId, `authType:modelId` |
| **Permission** | `permissionMode` (6 режимов) | `approvalMode` (5 режимов) |
| **Tools** | `tools` (allowlist), `disallowedTools` (blocklist) | `tools` (allowlist), `disallowedTools` (blocklist) |
| **Memory** | `memory`: `user`, `project`, `local` | Нет в frontmatter |
| **Isolation** | `isolation: worktree` | Нет |
| **MCP** | `mcpServers` в frontmatter | `mcpServers` в frontmatter |
| **Hooks** | `hooks` в frontmatter | `hooks` в frontmatter |
| **Background** | `background: boolean` | `background: boolean` (default `true`) |
| **Max turns** | `maxTurns: integer` | `maxTurns: positive integer` |
| **Effort** | `effort`: 5 уровней | Нет |
| **Skills preload** | `skills: string[]` | Нет |
| **External executors** | Нет | `executor.kind`: `codex`, `acp` |
| **Plugin agents** | Ограничения на `hooks`, `mcpServers`, `permissionMode` | Нет ограничений |
| **CLI определение** | `--agents` JSON | Нет |
| **Managed settings** | Поддерживается | Нет |

### 4.2 Скиллы

| Аспект | Claude Code | Qwen Code |
|--------|-------------|-----------|
| **Формат** | `SKILL.md` в директории | `SKILL.md` в директории или `.md` в `commands/` |
| **Обязательные поля** | Все опциональны, рекомендуется `description` | Все опциональны |
| **Хранение** | `.claude/skills/<name>/SKILL.md` | `.qwen/skills/<name>/SKILL.md`, `.qwen/commands/` |
| **Dynamic context** | `` !`command` ``, ` ```! ` блоки | Аналогично |
| **String substitution** | `$ARGUMENTS`, `${CLAUDE_*}` | `$ARGUMENTS`, `${QWEN_*}` |
| **Invocation control** | `disable-model-invocation`, `user-invocable` | `disable-model-invocation`, `user-invocable` |
| **Subagent execution** | `context: fork`, `agent`, `background` | `context: fork` |
| **Allowed tools** | `allowed-tools`, `disallowed-tools` | `allowed-tools`, `disallowed-tools` |
| **Paths** | `paths` (glob) | `paths` (glob) |
| **Hooks** | `hooks` в frontmatter | `hooks` в frontmatter |
| **Shell** | `shell`: `bash`/`powershell` | Нет |
| **Agent Skills spec** | Следует стандарту | Нет |
| **Synced skills** | Из claude.ai | Нет |
| **Metadata** | `metadata` object | Нет |
| **License/compatibility** | `license`, `compatibility` (Agent Skills spec) | Нет |

### 4.3 Плагины/Расширения

| Аспект | Claude Code | Qwen Code |
|--------|-------------|-----------|
| **Manifest** | `.claude-plugin/plugin.json` | `.qwen-extension/manifest.json` |
| **Обязательные поля** | Только `name` | `name`, `version`, `description` |
| **Компоненты** | Skills, Agents, Commands, Hooks, MCP, LSP, Output Styles, Workflows, Themes, Monitors, Executables | Skills, Agents, Commands, Hooks, MCP Servers, Settings |
| **User config** | `userConfig` schema | `settings` с типами |
| **Dependencies** | `dependencies` array | Нет |
| **Channels** | `channels` schema | Нет |
| **Environment vars** | `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}` | `${QWEN_EXTENSION_ROOT}` и др. |
| **Marketplace** | Поддерживается (JSON catalog) | Нет |
| **Validation** | `claude plugin validate` | Нет встроенной |
| **Development mode** | `claude --plugin-dir` | Link через `qwen extension link` |
| **Persistent data** | `${CLAUDE_PLUGIN_DATA}` | Нет |

### 4.4 Ключевые отличия

1. **Claude Code:** более зрелая plugin система с marketplace, dependencies, user config, channels
2. **Claude Code:** Agent Skills open standard для кросс-платформенности
3. **Claude Code:** `isolation: worktree` для изоляции агентов
4. **Claude Code:** `skills` preload в агентах
5. **Claude Code:** Managed settings для enterprise
6. **Claude Code:** Synced skills из claude.ai
7. **Qwen Code:** External executors (Codex, ACP) для кросс-платформенности
8. **Qwen Code:** Более простая система расширений

---

## 5. Сводные таблицы

### 5.1 Обязательные поля для агентов

| Поле | Claude Code | Qwen Code |
|------|-------------|-----------|
| `name` | ✅ Да | ✅ Да |
| `description` | ✅ Да | ✅ Да |
| Всё остальное | Опционально | Опционально |

### 5.2 Обязательные поля для скиллов

| Поле | Claude Code | Qwen Code |
|------|-------------|-----------|
| Все поля | Опциональны | Опциональны |
| `description` | Рекомендуется | — |

### 5.3 Обязательные поля для плагинов

| Поле | Claude Code | Qwen Code |
|------|-------------|-----------|
| `name` | ✅ Да | ✅ Да |
| `version` | Опционально | ✅ Да |
| `description` | Опционально | ✅ Да |

---

## 6. Источники

- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Claude Code Sub-agents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Plugins Overview](https://code.claude.com/docs/en/plugins/overview)
- [Claude Code Plugin Manifest Reference](https://code.claude.com/docs/en/plugins/manifest-reference)
- [Agent Skills Standard](https://agentskills.io)

---

*Документ создан: 2026-10-06*
*Версия документации Claude Code: актуальная на октябрь 2026*
