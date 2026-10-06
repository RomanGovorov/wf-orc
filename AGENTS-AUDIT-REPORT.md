# Аудит агентов wf-orc

**Дата:** 2026-10-06  
**Аудитор:** Code Review Specialist  
**Объект:** 12 агентов в `agents/*.md`  
**Критерии:** Формат frontmatter, соответствие документации Qwen Code, полнота секций, корректность Result Format, разделение ответственностей с оркестратором

---

## Сводная таблица

| # | Агент | Frontmatter | maxTurns | disallowedTools | Transition IDs | Result JSON | Секции | Оценка |
|---|-------|-------------|----------|-----------------|----------------|-------------|--------|--------|
| 1 | `project-manager` | ✅ | 100 | ✅ (4) | ⚠️ T01, T70, T70_REV | ✅ | ✅ | **B** |
| 2 | `architecture-planner` | ⚠️ Двойной `---` | 80 | ✅ (4) | ⚠️ T13, T12a/b/c, T23c, T_AGG_TO_DEVOPS | ✅ | ✅ | **C** |
| 3 | `code-implementer` | ⚠️ Двойной `---` | 100 | ✅ (4) | ⚠️ T34, T_CODE_TO_* (6 шт.) | ✅ | ✅ | **C** |
| 4 | `code-reviewer` | ✅ | 50 | ✅ (4) | ✅ Нет | ✅ | ✅ | **A** |
| 5 | `comprehensive-test-engineer` | ✅ | 80 | ✅ (4) | ✅ Нет | ✅ | ✅ | **A** |
| 6 | `performance-analyst` | ✅ | 60 | ✅ (4) | ✅ Нет | ✅ | ✅ | **A** |
| 7 | `devops-infrastructure-engineer` | ✅ | 60 | ✅ (4) | ⚠️ T_AGG_TO_DEVOPS | ✅ | ✅ | **B** |
| 8 | `tech-docs-writer` | ✅ | 50 | ✅ (4) | ⚠️ T70 | ✅ | ✅ | **B** |
| 9 | `business-analyst` | ✅ | 80 | ✅ (4) | ✅ Нет | ✅ | ✅ | **A** |
| 10 | `security-auditor` | ✅ | 50 | ✅ (4) | ✅ Нет | ✅ | ✅ | **A** |
| 11 | `ui-ux-accessibility-specialist` | ✅ | 50 | ✅ (4) | ✅ Нет | ✅ | ✅ | **A** |
| 12 | `data-engineering-architect` | ✅ | 60 | ✅ (4) | ⚠️ T23c, T_AGG_TO_DEVOPS | ✅ | ✅ | **B** |

---

## Детальный аудит по агентам

### 1. project-manager

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `project-manager` | ✅ |
| `description` | Уникальный, без "Use this agent when" | ⚠️ Нестандартный стиль |
| `maxTurns` | 100 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |
| `tools` | Не указан | ✅ (опционально) |

**Секции:**
- ✅ Execution Model (с критическим правилом "No Code Writing")
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Input Data
- ✅ Output Data
- ✅ Core Responsibilities
- ✅ Operational Methodology (7 фаз)
- ✅ Self-Verification Checklist
- ✅ File Naming Notes
- ✅ Result Format (4 варианта)
- ✅ Skills (5 скиллов)

**Проблемы:**
- **[MEDIUM] Transition IDs в тексте:** `T01`, `T70`, `T70_REV` — идентификаторы переходов из workflow.yaml. Агент не должен знать о transition IDs — это зона ответственности оркестратора.
  - Строка 15: `"The main workflow starts at you (T01) and ends at you (T70 → workflow_complete)"`
  - Строка 62: `"The main workflow starts at you (backlog approval → T01)"`
  - Строка 107: `"T70_REV loop"`
  - **Рекомендация:** Заменить на "the orchestrator launches you first" / "the orchestrator closes the workflow" / "documentation revision loop".

**Result Format:**
- ✅ Backlog approved: `status: "pass"`, `backlog_approved: true`, `artifacts`, `task_ids`, `tasks`
- ✅ Documentation needs revision: `status: "pass"`, `documentation_needs_revision: true`
- ✅ Workflow complete: `status: "pass"`, `workflow_complete: true`
- ✅ Все варианты возвращают `status: "pass"` (forced progress policy)

---

### 2. architecture-planner

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `architecture-planner` | ✅ |
| `description` | "Use this agent when..." | ✅ Стандартный стиль |
| `maxTurns` | 80 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Input Data (с агрегацией аудиторских артефактов)
- ✅ Output Data
- ✅ Specialized Agent Invocation (условия вызова аудитор)
- ✅ Operational Methodology (5 шагов)
- ✅ Core Responsibilities
- ✅ Result Format (5 вариантов)
- ✅ Skills (5 скиллов)

**Проблемы:**
- **[CRITICAL] Двойной frontmatter delimiter:** Файл начинается с `---\n\n---\nname: ...`. Первый `---` создаёт пустой YAML frontmatter блок, после чего настоящий frontmatter не парсится. Это может привести к тому, что Qwen Code не распознает `name`, `maxTurns`, `disallowedTools`.
  - **Фикс:** Удалить первую строку `---` и пустую строку, оставить только один frontmatter блок.
  
- **[HIGH] Transition IDs (5+ упоминаний):** `T13`, `T12a/b/c`, `T23c`, `T_AGG_TO_DEVOPS` — агент не должен знать внутренние ID переходов.
  - Строка 59: `"To code-implementer (aggregated handoff, T13)"`
  - Строка 60: `"T_AGG_TO_DEVOPS"`
  - Строка 132: `"routes to devops via T_AGG_TO_DEVOPS"`
  - Строка 156: `"NOT fire T13 or any audit transitions (T12a/b/c)"`
  - **Рекомендация:** Переписать на "the orchestrator routes to code-implementer" / "the orchestrator handles transition logic".

---

### 3. code-implementer

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `code-implementer` | ✅ |
| `description` | "Use this agent when..." | ✅ |
| `maxTurns` | 100 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Input Data (от 7 источников)
- ✅ Output Data
- ✅ Transition Mapping (таблица JSON Flag → Transition)
- ✅ Core Responsibilities (3 направления)
- ✅ Error Handling (BLOCKED-RESULT PROTOCOL)
- ✅ Operational Methodology
- ✅ Self-Verification Checklist
- ✅ Result Format (6 вариантов)
- ✅ Skills (11 скиллов — максимум среди всех агентов)

**Проблемы:**
- **[CRITICAL] Двойной frontmatter delimiter:** Аналогично architecture-planner — файл начинается с `---\n\n---\nname: ...`.
  - **Фикс:** Удалить первую строку `---` и пустую строку.

- **[HIGH] Transition IDs в таблице и тексте (8+ упоминаний):**
  - Строки 79-86: Таблица с `T34`, `T_CODE_TO_SEC`, `T_CODE_TO_UI`, `T_CODE_TO_DATA`, `T_CODE_TO_TEST`, `T_CODE_TO_PERF`
  - Строка 86: `"use T34 (standard pass to code-reviewer)"`
  - Строка 123: `"typically T34 → code-reviewer"`
  - **Рекомендация:** Удалить столбец "Transition" из таблицы, оставить только "JSON Flag" и "Next Agent". Агент должен знать какой флаг установить, а не какой transition использовать.

- **[LOW] Transition Mapping таблица:** Таблица содержит transition IDs (`T34`, `T_CODE_TO_*`), которые агент не должен знать. Однако сама таблица полезна для понимания — рекомендуется переформатировать, убрав столбец transition ID.

---

### 4. code-reviewer

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `code-reviewer` | ✅ |
| `description` | "Use this agent when..." | ✅ |
| `maxTurns` | 50 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Input Data (от 5 источников)
- ✅ Output Data
- ✅ Review Types (3 типа)
- ✅ Core Responsibilities
- ✅ Operational Methodology (3 фазы)
- ✅ Output Format
- ✅ Result Format (10+ вариантов)
- ✅ File Naming Notes
- ✅ Skills (12 скиллов — максимум)

**Проблемы:**
- **[INFO] Нет значимых проблем.** Эталонный агент. Transition IDs отсутствуют. Result Format покрывает все сценарии (application review, test fix review, performance fix review, infrastructure review, verification pass, forced pass).

**Замечания:**
- Result Format содержит 10+ вариантов — это оправдано сложностью роли (множественные типы ревью).
- `verification_pass_only: true` с `source` — правильный паттерн для auditor verification pass.

---

### 5. comprehensive-test-engineer

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `comprehensive-test-engineer` | ✅ |
| `description` | "Use this agent when..." | ✅ |
| `maxTurns` | 80 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Input Data
- ✅ Output Data
- ✅ Core Responsibilities (с критическим правилом "Test Scope Boundary")
- ✅ Operational Methodology
- ✅ File Naming Notes
- ✅ Result Format (3 варианта: pass, bugs found, forced pass)
- ✅ Skills (7 скиллов)

**Проблемы:**
- **[INFO] Нет значимых проблем.** Чистый агент без transition IDs. Scope Boundary правило правильно предотвращает попытку исправления багов.

---

### 6. performance-analyst

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `performance-analyst` | ✅ |
| `description` | "Use this agent when..." | ✅ |
| `maxTurns` | 60 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Input Data
- ✅ Output Data (с определением `optimized_application`)
- ✅ Core Responsibilities (с "Scope Boundary")
- ✅ Operational Methodology (4 направления)
- ✅ Self-Verification Checklist
- ✅ File Naming Notes
- ✅ Result Format (3 варианта)
- ✅ Skills (5 скиллов)

**Проблемы:**
- **[INFO] Нет значимых проблем.** Эталонный агент.

---

### 7. devops-infrastructure-engineer

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `devops-infrastructure-engineer` | ✅ |
| `description` | "Use this agent when..." | ✅ |
| `maxTurns` | 60 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Input Data (с conditional deployment_only path)
- ✅ Output Data
- ✅ Core Responsibilities (7 направлений)
- ✅ Operational Methodology (5 шагов + Code Quality Requirements)
- ✅ File Naming Notes
- ✅ Result Format (3 варианта)
- ✅ Skills (5 скиллов)

**Проблемы:**
- **[MEDIUM] Transition ID:** `T_AGG_TO_DEVOPS` упомянут в строке 50.
  - **Рекомендация:** Заменить на "when the orchestrator routes via the deployment-only path".

---

### 8. tech-docs-writer

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `tech-docs-writer` | ✅ |
| `description` | "Use this agent when..." | ✅ |
| `maxTurns` | 50 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Input Data
- ✅ Output Data
- ✅ Core Responsibilities (6 направлений)
- ✅ Operational Methodology (4 типа документации)
- ✅ Self-Verification Checklist
- ✅ File Naming Notes
- ✅ Result Format (2 варианта + note)
- ✅ Skills (3 скилла)

**Проблемы:**
- **[MEDIUM] Transition ID:** `T70` упомянут в строке 131: `"so T70 fires on the flag"`.
  - **Рекомендация:** Заменить на "so the orchestrator recognizes completion".

---

### 9. business-analyst

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `business-analyst` | ✅ |
| `description` | "Use this agent to gather..." | ✅ (альтернативный стиль) |
| `maxTurns` | 80 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model (с User Interaction Protocol)
- ✅ Interview State Persistence (MANDATORY)
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Role
- ✅ Core Responsibilities
- ✅ Input Data (таблица)
- ✅ Output Data (таблица с путями)
- ✅ Interview Protocol (7 раундов)
- ✅ Operational Methodology (Before/During/After)
- ✅ Quality Standards
- ✅ Self-Verification Checklist
- ✅ Result Format (2 варианта + important note о `task_type`)
- ✅ File Naming Notes
- ✅ Skills (3 скилла)

**Проблемы:**
- **[INFO] Нет значимых проблем.** Первичный агент без transition IDs. `needs_user_input` relay protocol правильно документирован. `task_type` field — правильное решение для маршрутизации.

---

### 10. security-auditor

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `security-auditor` | ✅ |
| `description` | "Use this agent when..." | ✅ |
| `maxTurns` | 50 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Two-Phase Workflow
- ✅ Input Data (Phase 1 + Phase 2)
- ✅ Output Data
- ✅ Core Responsibilities (4 направления)
- ✅ Operational Methodology (3 направления)
- ✅ Output Format
- ✅ Result Format (5 вариантов)
- ✅ File Naming Notes
- ✅ Skills (3 скилла)

**Проблемы:**
- **[INFO] Нет значимых проблем.** Двухфазный workflow правильно документирован. Forced pass корректно обрабатывает `FINAL ITERATION`.

---

### 11. ui-ux-accessibility-specialist

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `ui-ux-accessibility-specialist` | ✅ |
| `description` | "Use this agent when..." | ✅ |
| `maxTurns` | 50 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Two-Phase Workflow
- ✅ Input Data
- ✅ Output Data
- ✅ Core Responsibilities (3 направления)
- ✅ Operational Methodology (3 направления)
- ✅ Self-Verification Checklist
- ✅ File Naming Notes
- ✅ Result Format (5 вариантов)
- ✅ Skills (6 скиллов)

**Проблемы:**
- **[INFO] Нет значимых проблем.** Структура зеркальна security-auditor — корректно.

---

### 12. data-engineering-architect

| Параметр | Значение | Статус |
|----------|----------|--------|
| `name` | `data-engineering-architect` | ✅ |
| `description` | "Use this agent when..." | ✅ |
| `maxTurns` | 60 | ✅ |
| `disallowedTools` | Agent, agent, Task, task | ✅ |

**Секции:**
- ✅ Execution Model
- ✅ Working with Large Files
- ✅ Turn Management
- ✅ Two-Phase Workflow
- ✅ Input Data
- ✅ Output Data (с deployment-only path)
- ✅ Core Responsibilities (5 направлений)
- ✅ Operational Methodology (5 направлений)
- ✅ Self-Verification Checklist
- ✅ Result Format (5 вариантов + deployment-only)
- ✅ File Naming Notes
- ✅ Skills (6 скиллов)

**Проблемы:**
- **[MEDIUM] Transition IDs:** `T23c` и `T_AGG_TO_DEVOPS` упомянуты в строках 69 и 171.
  - **Рекомендация:** Заменить на описательные формулировки: "returns to architecture-planner for aggregation" вместо "via T23c".

---

## Сводка проблем

### CRITICAL (2)

| # | Агент | Проблема | Файл | Строка |
|---|-------|----------|------|--------|
| 1 | `architecture-planner` | Двойной `---` в начале файла — frontmatter не парсится | `agents/architecture-planner.md` | 1-3 |
| 2 | `code-implementer` | Двойной `---` в начале файла — frontmatter не парсится | `agents/code-implementer.md` | 1-3 |

**Фикс:** Удалить первую строку `---` и пустую строку из каждого файла. Файл должен начинаться непосредственно с:
```yaml
---
name: agent-name
description: ...
```

### HIGH (2)

| # | Агент | Проблема | Кол-во упоминаний |
|---|-------|----------|--------------------|
| 1 | `code-implementer` | Transition IDs в таблице Transition Mapping и тексте | 8+ |
| 2 | `architecture-planner` | Transition IDs в Output Data и Result Format | 5+ |

**Фикс:** Убрать все transition IDs из текста агентов. Агент должен знать:
- Какие входные данные он получает
- Какие флаги устанавливать в Result JSON
- Кто следующий агент (по имени, не по ID)

### MEDIUM (3)

| # | Агент | Проблема |
|---|-------|----------|
| 1 | `project-manager` | Transition IDs: T01, T70, T70_REV (3 упоминания) |
| 2 | `devops-infrastructure-engineer` | Transition ID: T_AGG_TO_DEVOPS (1 упоминание) |
| 3 | `tech-docs-writer` | Transition ID: T70 (1 упоминание) |
| 4 | `data-engineering-architect` | Transition IDs: T23c, T_AGG_TO_DEVOPS (2 упоминания) |

### LOW (1)

| # | Агент | Проблема |
|---|-------|----------|
| 1 | `code-implementer` | Transition Mapping таблица содержит столбец с transition IDs |

### INFO (стилистические)

| # | Агент | Проблема |
|---|-------|----------|
| 1 | `project-manager` | Описание в frontmatter не использует стандартный стиль "Use this agent when..." |

---

## Положительные аспекты

### Сильные стороны архитектуры агентов

1. **Единый Execution Model** — все 12 агентов содержат идентичную секцию "Execution Model" с чётким правилом "MUST NOT launch other agents". Это обеспечивает предсказуемое поведение.

2. **Консистентный disallowedTools** — все агенты блокируют `Agent`, `agent`, `Task`, `task` — защита от несанкционированного запуска субагентов на всех платформах.

3. **Forced Progress Policy** — все агенты с итерационными циклами (code-reviewer, comprehensive-test-engineer, performance-analyst, security-auditor, ui-ux-accessibility-specialist, data-engineering-architect, devops-infrastructure-engineer, tech-docs-writer) корректно обрабатывают `FINAL ITERATION` и возвращают `status: "pass"` с `forced: true`.

4. **Scope Boundaries** — test-engineer и performance-analyst имеют явные правила "analyze and report, don't fix", что предотвращает расход turn budget на исправления.

5. **Двухфазные агенты** — security-auditor, ui-ux-accessibility-specialist, data-engineering-architect корректно разделяют Phase 1 (audit/design) и Phase 2 (verification), с разными Input/Output для каждой фазы.

6. **State Persistence** — business-analyst (`interview-state.md`) и project-manager (`doc-review-state.md`) реализуют persistence для переживания relaunch cycles.

7. **Result Format полнота** — все агенты возвращают `status: "pass"` (никогда "fail"), что соответствует forced progress policy. JSON содержит все необходимые флаги для маршрутизации оркестратора.

8. **Skills таблицы** — все агенты содержат таблицы скиллов с пояснением "When to Use" и примечанием о platform-specific naming (`wf-orc:` prefix для Claude Code).

9. **Working with Large Files** — стандартизированная секция во всех 12 агентах обеспечивает эффективную работу с файлами >500 строк.

10. **Input/Output Data** — чёткое документирование источников и потребителей артефактов в каждом агенте.

---

## Рекомендации по улучшению

### Приоритет 1 — Критические фиксы

1. **Исправить двойной `---` в architecture-planner.md и code-implementer.md**
   ```bash
   # Для каждого файла: удалить первую пустую строку и первый "---"
   # Файл должен начинаться с:
   ---
   name: agent-name
   ...
   ---
   ```

### Приоритет 2 — Удаление transition IDs

2. **Удалить все transition IDs из агентов** — создать таблицу соответствий для оркестратора, но не раскрывать ID агентам:

   **project-manager.md:**
   - `T01` → "the orchestrator launches you at workflow start"
   - `T70` → "the orchestrator closes the workflow"
   - `T70_REV` → "documentation revision loop"

   **architecture-planner.md:**
   - `T13` → "the orchestrator routes to code-implementer"
   - `T12a/b/c` → "the orchestrator routes to specialized auditors"
   - `T23c` → "returns to architecture-planner for aggregation"
   - `T_AGG_TO_DEVOPS` → "the orchestrator routes to devops after aggregation"

   **code-implementer.md:**
   - Убрать столбец "Transition" из таблицы, оставить "JSON Flag" → "Next Agent"
   - `T34` → "standard review pass"
   - `T_CODE_TO_*` → убрать, агент устанавливает флаг, оркестратор маршрутизирует

   **devops-infrastructure-engineer.md:**
   - `T_AGG_TO_DEVOPS` → "deployment-only path"

   **tech-docs-writer.md:**
   - `T70` → "workflow completion"

   **data-engineering-architect.md:**
   - `T23c` → "returns to architecture-planner"
   - `T_AGG_TO_DEVOPS` → "deployment-only routing"

### Приоритет 3 — Стилистические улучшения

3. **Унифицировать description стиль** — привести `project-manager` к стандартному стилю:
   ```yaml
   description: Use this agent when you need project management, backlog grooming, sprint planning, task prioritization, or documentation review. This agent specializes in managing the development workflow lifecycle and coordinating work through task files and result flags.
   ```

4. **Добавить Self-Verification Checklist** агентам, у которых его нет:
   - `architecture-planner` — нет явного чеклиста
   - `tech-docs-writer` — есть, но минимальный
   - `devops-infrastructure-engineer` — есть, но в формате "Verify:"

---

## Соответствие документации Qwen Code

| Критерий | Статус | Комментарий |
|----------|--------|-------------|
| YAML frontmatter формат | ⚠️ | 2 из 12 файлов имеют двойной `---` |
| Обязательные поля (`name`, `description`) | ✅ | Все 12 имеют |
| `maxTurns` | ✅ | Все 12 имеют, значения разумные (50-100) |
| `disallowedTools` | ✅ | Все 12 блокируют Agent/Task |
| `tools` поле | ✅ | Не используется (опционально, все инструменты доступны по умолчанию) |
| Sub-agent не запускает субагентов | ✅ | Все 12 имеют "You MUST NOT launch other agents" |
| Orchestrator manages transitions | ✅ | Все 12 имеют "The orchestrator manages all transitions" |
| Result Format — JSON с `status` | ✅ | Все варианты возвращают `status: "pass"` |
| No fail results | ✅ | Соответствует forced progress policy |

---

## Итоговая оценка

| Метрика | Значение |
|---------|----------|
| **Всего агентов** | 12 |
| **Оценка A (эталон)** | 6 (code-reviewer, comprehensive-test-engineer, performance-analyst, business-analyst, security-auditor, ui-ux-accessibility-specialist) |
| **Оценка B (минорные проблемы)** | 4 (project-manager, devops-infrastructure-engineer, tech-docs-writer, data-engineering-architect) |
| **Оценка C (критические проблемы)** | 2 (architecture-planner, code-implementer) |
| **Оценка D/F** | 0 |
| **CRITICAL проблем** | 2 |
| **HIGH проблем** | 2 |
| **MEDIUM проблем** | 4 |
| **LOW проблем** | 1 |

### Общий вердикт: **B-**

Агенты wf-orc демонстрируют сильную архитектуру с консистентной структурой, правильным разделением ответственностей и корректной forced progress policy. Однако два критических бага (двойной frontmatter delimiter) требуют немедленного исправления, а проблема transition IDs в 6 из 12 агентов нарушает принцип разделения оркестратор/агент.

---

## План исправлений

```bash
# 1. Исправить двойной frontmatter (CRITICAL)
# architecture-planner.md — удалить строки 1-2 (--- и пустую строку)
# code-implementer.md — удалить строки 1-2 (--- и пустую строку)

# 2. Удалить transition IDs из 6 агентов (HIGH + MEDIUM)
# project-manager.md — заменить T01, T70, T70_REV
# architecture-planner.md — заменить T13, T12a/b/c, T23c, T_AGG_TO_DEVOPS
# code-implementer.md — убрать столбец Transition из таблицы
# devops-infrastructure-engineer.md — заменить T_AGG_TO_DEVOPS
# tech-docs-writer.md — заменить T70
# data-engineering-architect.md — заменить T23c, T_AGG_TO_DEVOPS

# 3. Унифицировать description (LOW)
# project-manager.md — переписать description в стиле "Use this agent when..."
```
