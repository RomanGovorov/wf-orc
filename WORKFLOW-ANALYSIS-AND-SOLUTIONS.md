# Workflow Analysis & Solutions for Qwen Code / Claude Code

**Дата анализа:** 2026-10-06  
**Проект:** unirec-base  
**Проблема:** Оркестратор неправильно интерпретирует результаты subagents

---

## 📊 Анализ проблемы в unirec-base

### Хронология событий (Oct 6, 2026)

| Время (UTC) | Событие | Статус | Проблема |
|-------------|---------|--------|----------|
| 05:21 | Orchestrator → `agent(project-manager)` | ✅ Запущен | - |
| 05:23 | Project-manager completed | ✅ Pass | Вернул `backlog_approved: true` |
| 05:23+ | Orchestrator пишет: "Project-manager недоступен" | ❌ Ошибка | Неверная интерпретация |
| 06:05 | Orchestrator → `agent(project-manager)` retry | ✅ Запущен | - |
| 06:06 | Project-manager completed | ✅ Pass | Вернул корректный JSON |
| 06:06+ | Orchestrator пишет: "workflow не работает" | ❌ Ошибка | Игнорирует успешные результаты |
| 11:49-12:27 | Code-implementer запущен 3 раза | ✅ Все выполнены | TSK-145 реализована |
| 12:27 | Code-implementer завершил TSK-145 | ✅ Pass | Все тесты проходят |

### Корень проблемы

**НЕ инструмент** — `agent(subagent_type="project-manager")` работает  
**НЕ агенты** — project-manager успешно запустился 2 раза  
**ОРКЕСТРАТОР** — главный агент неправильно интерпретировал результаты

**Почему это произошло:**
1. Оркестратор не дождался completion notification
2. Быстро сделал вывод "инструмент недоступен" без проверки
3. Решил работать "напрямую", игнорируя workflow
4. Создал ложную память "wf-orc subagent tool unavailable"

---

## 🔍 Диагностика: Как проверить работоспособность workflow

### Проверка для Qwen Code

```bash
# 1. Проверить, что инструмент agent существует
# В начале сессии проверить список доступных инструментов — должен быть "agent"

# 2. Проверить, что агенты загружены
ls ~/.qwen/extensions/wf-orc/agents/
# Должны быть: project-manager.md, architecture-planner.md, code-implementer.md, etc.

# 3. Тестовый запуск
agent(subagent_type="project-manager", prompt="Тест", run_in_background=false)
# Должен вернуться результат со статусом "pass"

# 4. Проверить логи subagents
ls .qwen/projects/<project-hash>/subagents/<session-id>/
# Должны быть .jsonl и .meta.json файлы

# 5. Проверить статус agents
list_agents
# Должны показать active/completed agents
```

### Проверка для Claude Code

```bash
# 1. Проверить, что инструмент Agent существует
# В начале сессии проверить список доступных инструментов — должен быть "Agent"

# 2. Проверить, что агенты загружены
ls ~/.claude/extensions/wf-orc/agents/
# Должны быть: project-manager.md, architecture-planner.md, code-implementer.md, etc.

# 3. Тестовый запуск
Agent(subagent_type="project-manager", prompt="Тест")
# Должен вернуться результат со статусом "pass"

# 4. Проверить логи subagents
ls .claude/projects/<project-hash>/subagents/<session-id>/
# Должны быть .jsonl и .meta.json файлы
```

---

## 💡 Решения для улучшения workflow

### Решение 1: Явная проверка статуса agents (Рекомендуется)

**Проблема:** Оркестратор не проверяет статус agents перед интерпретацией результата.

**Решение:** Добавить обязательную проверку через `list_agents` после запуска.

#### Для Qwen Code:

```javascript
// После запуска agent
const agentResult = await agent(subagent_type="project-manager", prompt="...");

// Явная проверка статуса
const agents = await list_agents();
const myAgent = agents.find(a => a.task_id === agentResult.task_id);

if (!myAgent) {
  throw new Error("Agent not found in roster");
}

if (myAgent.status === "completed") {
  // Получить результат из completion notification
  const result = await get_agent_result(agentResult.task_id);
  // Продолжить workflow
} else if (myAgent.status === "running") {
  // Подождать completion notification
  await wait_for_completion(agentResult.task_id);
} else if (myAgent.status === "failed") {
  // Обработать ошибку
  throw new Error(`Agent failed: ${myAgent.error}`);
}
```

#### Для Claude Code:

```javascript
// После запуска Agent
const agentResult = await Agent(subagent_type="project-manager", prompt="...");

// Явная проверка статуса
const agents = await list_agents();
const myAgent = agents.find(a => a.task_id === agentResult.task_id);

if (!myAgent) {
  throw new Error("Agent not found in roster");
}

// Claude Code: background agents report via completion notifications
// Wait for notification before proceeding
if (myAgent.status === "completed") {
  // Результат придет в completion notification
  // Продолжить workflow после получения notification
}
```

**Преимущества:**
- ✅ Явная проверка статуса
- ✅ Нет ложных выводов о недоступности
- ✅ Работает в обеих платформах

**Недостатки:**
- ⚠️ Требует дополнительных вызовов list_agents
- ⚠️ Увеличивает время выполнения

---

### Решение 2: Timeout и retry логика (Рекомендуется)

**Проблема:** Оркестратор быстро делает вывод о недоступности без ожидания.

**Решение:** Добавить явный timeout и retry логику.

#### Псевдокод для оркестратора:

```javascript
async function launchAgentWithRetry(agentType, prompt, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      // Запуск agent
      const result = await agent(subagent_type=agentType, prompt=prompt);
      
      // Проверка результата
      if (result && result.status === "pass") {
        return result; // Успех
      }
      
      // Если результат не pass, но и не ошибка — продолжить
      if (result && result.status !== "fail") {
        return result;
      }
      
    } catch (error) {
      console.error(`Attempt ${attempt} failed:`, error);
      
      if (attempt === maxRetries) {
        throw new Error(`Agent ${agentType} failed after ${maxRetries} attempts`);
      }
      
      // Подождать перед retry
      await sleep(1000 * attempt); // Exponential backoff
    }
  }
}

// Использование
const pmResult = await launchAgentWithRetry("project-manager", taskPrompt);
```

**Преимущества:**
- ✅ Автоматический retry при ошибках
- ✅ Exponential backoff
- ✅ Явная обработка ошибок

**Недостатки:**
- ⚠️ Увеличивает время выполнения при ошибках
- ⚠️ Может скрыть реальные проблемы

---

### Решение 3: Явное логирование состояния workflow (Опционально)

**Проблема:** Сложно диагностировать, что произошло в workflow.

**Решение:** Добавить явное логирование каждого шага.

#### Псевдокод для оркестратора:

```javascript
const workflowLog = [];

function logWorkflowStep(step, data) {
  const entry = {
    timestamp: new Date().toISOString(),
    step,
    data,
    platform: detectPlatform() // "qwen" or "claude"
  };
  workflowLog.push(entry);
  console.log(`[Workflow] ${step}:`, data);
}

// Использование
logWorkflowStep("launch_agent", { agent: "project-manager", attempt: 1 });
const pmResult = await agent(subagent_type="project-manager", prompt="...");
logWorkflowStep("agent_completed", { agent: "project-manager", status: pmResult.status });

// Сохранить лог в файл
await write_file("workflow-log.json", JSON.stringify(workflowLog, null, 2));
```

**Преимущества:**
- ✅ Полная трассируемость workflow
- ✅ Легко диагностировать проблемы
- ✅ Можно анализировать post-factum

**Недостатки:**
- ⚠️ Дополнительные накладные расходы
- ⚠️ Требует управления файлами логов

---

### Решение 4: Platform-specific адаптеры (Рекомендуется для production)

**Проблема:** Различия в API между Qwen Code и Claude Code.

**Решение:** Создать platform-specific адаптеры для унификации API.

#### Структура:

```
wf-orc/
├── adapters/
│   ├── qwen-adapter.js      # Qwen Code specific
│   ├── claude-adapter.js    # Claude Code specific
│   └── adapter-interface.js # Common interface
└── orchestrator.js           # Platform-agnostic logic
```

#### adapter-interface.js:

```javascript
export interface AgentAdapter {
  launchAgent(agentType: string, prompt: string): Promise<AgentResult>;
  listAgents(): Promise<Agent[]>;
  getAgentResult(taskId: string): Promise<AgentResult>;
  waitForCompletion(taskId: string, timeout?: number): Promise<AgentResult>;
}

export interface AgentResult {
  task_id: string;
  status: "pass" | "fail" | "blocked";
  artifacts?: string[];
  content?: string;
  // ... other fields
}
```

#### qwen-adapter.js:

```javascript
export class QwenAdapter implements AgentAdapter {
  async launchAgent(agentType: string, prompt: string): Promise<AgentResult> {
    // Qwen Code specific: agent(subagent_type=...)
    const result = await agent(subagent_type=agentType, prompt=prompt);
    return result;
  }
  
  async listAgents(): Promise<Agent[]> {
    return await list_agents();
  }
  
  async getAgentResult(taskId: string): Promise<AgentResult> {
    // Qwen Code: получить результат из completed agent
    const agents = await list_agents();
    const agent = agents.find(a => a.task_id === taskId);
    if (!agent) throw new Error(`Agent ${taskId} not found`);
    return agent.result;
  }
  
  async waitForCompletion(taskId: string, timeout = 60000): Promise<AgentResult> {
    // Qwen Code: ждать completion notification
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      const agents = await list_agents();
      const agent = agents.find(a => a.task_id === taskId);
      if (agent && agent.status === "completed") {
        return agent.result;
      }
      await sleep(1000);
    }
    throw new Error(`Timeout waiting for agent ${taskId}`);
  }
}
```

#### claude-adapter.js:

```javascript
export class ClaudeAdapter implements AgentAdapter {
  async launchAgent(agentType: string, prompt: string): Promise<AgentResult> {
    // Claude Code specific: Agent(subagent_type=...)
    const result = await Agent(subagent_type=agentType, prompt=prompt);
    return result;
  }
  
  async listAgents(): Promise<Agent[]> {
    return await list_agents();
  }
  
  async getAgentResult(taskId: string): Promise<AgentResult> {
    // Claude Code: результат придет в completion notification
    const agents = await list_agents();
    const agent = agents.find(a => a.task_id === taskId);
    if (!agent) throw new Error(`Agent ${taskId} not found`);
    return agent.result;
  }
  
  async waitForCompletion(taskId: string, timeout = 60000): Promise<AgentResult> {
    // Claude Code: ждать completion notification
    // В Claude Code background agents report via notifications
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      const agents = await list_agents();
      const agent = agents.find(a => a.task_id === taskId);
      if (agent && agent.status === "completed") {
        return agent.result;
      }
      await sleep(1000);
    }
    throw new Error(`Timeout waiting for agent ${taskId}`);
  }
}
```

#### orchestrator.js:

```javascript
import { QwenAdapter } from './adapters/qwen-adapter.js';
import { ClaudeAdapter } from './adapters/claude-adapter.js';

// Detect platform
function detectPlatform() {
  if (typeof agent !== 'undefined') return 'qwen';
  if (typeof Agent !== 'undefined') return 'claude';
  throw new Error('Unknown platform');
}

// Create adapter
const adapter = detectPlatform() === 'qwen' ? new QwenAdapter() : new ClaudeAdapter();

// Platform-agnostic orchestration
async function runWorkflow(task) {
  // Launch project-manager
  const pmResult = await adapter.launchAgent('project-manager', task);
  
  // Wait for completion
  const pmCompleted = await adapter.waitForCompletion(pmResult.task_id);
  
  // Evaluate transitions
  if (pmCompleted.backlog_approved) {
    // Launch architecture-planner
    const archResult = await adapter.launchAgent('architecture-planner', pmCompleted.artifacts);
    // ... continue workflow
  }
}
```

**Преимущества:**
- ✅ Platform-agnostic логика
- ✅ Легко тестировать
- ✅ Легко расширять для новых платформ
- ✅ Единый API для всех платформ

**Недостатки:**
- ⚠️ Требует дополнительной разработки
- ⚠️ Нужно поддерживать несколько адаптеров

---

## 🎯 Рекомендации для unirec-base

### Краткосрочные решения (быстрые исправления)

1. **Удалить ложную память** ✅ Уже сделано
   - Удалить `feedback/wf-orc-auto-activation.md`
   - Создать `feedback/wf-orc-agent-tool-works.md`

2. **Добавить явную проверку статуса** (Реализовать сейчас)
   ```javascript
   // После запуска agent
   const agents = await list_agents();
   const myAgent = agents.find(a => a.task_id === result.task_id);
   if (!myAgent || myAgent.status !== "completed") {
     // Подождать или retry
   }
   ```

3. **Добавить timeout логику** (Реализовать сейчас)
   ```javascript
   // Ждать completion notification с timeout
   const timeout = 60000; // 60 seconds
   const startTime = Date.now();
   while (Date.now() - startTime < timeout) {
     const agents = await list_agents();
     if (agents.find(a => a.task_id === taskId && a.status === "completed")) {
       break;
     }
     await sleep(1000);
   }
   ```

### Долгосрочные решения (production-ready)

1. **Создать platform-specific адаптеры** (Реализовать в следующем спринте)
   - QwenAdapter
   - ClaudeAdapter
   - Common interface

2. **Добавить workflow logging** (Реализовать в следующем спринте)
   - Логировать каждый шаг
   - Сохранять в файл
   - Анализировать post-factum

3. **Добавить workflow tests** (Реализовать в следующем спринте)
   - Тестировать каждый transition
   - Тестировать platform-specific код
   - Тестировать error handling

---

## 📋 Checklist для оркестратора

Перед запуском workflow:

- [ ] Проверить, что инструмент `agent` (Qwen) или `Agent` (Claude) доступен
- [ ] Проверить, что агенты загружены (`ls ~/.qwen/extensions/wf-orc/agents/`)
- [ ] Инициализировать iteration counters (все = 0)
- [ ] Подготовить task prompt
- [ ] Запустить первого агента (project-manager)
- [ ] **Явно проверить статус через `list_agents`**
- [ ] **Дождаться completion notification (с timeout)**
- [ ] Проверить результат (status, artifacts, flags)
- [ ] Продолжить workflow по transition map

Перед интерпретацией результата:

- [ ] **НЕ делать предположений о недоступности инструмента**
- [ ] **Проверить статус agent через `list_agents`**
- [ ] **Дождаться completion notification**
- [ ] **Проверить результат agent (не только факт запуска)**
- [ ] Если результат не получен — retry с exponential backoff
- [ ] Если retry не помог — задокументировать проблему и продолжить

---

## 🔗 Связанные файлы

- `workflow.yaml` — Single source of truth для transitions
- `AGENTS.md` — Описание агентов (auto-generated)
- `GEMINI.md` — Context file для Qwen Code (auto-generated)
- `scripts/generate_all.py` — Генерация документации из templates

---

## 📞 Контакты

Если проблема повторяется:
1. Проверить логи: `.qwen/projects/<project-hash>/subagents/<session-id>/`
2. Проверить статус: `list_agents`
3. Проверить память: `.qwen/memories/feedback/wf-orc-agent-tool-works.md`
4. Создать issue в wf-orc repo

---

**Статус:** ✅ Готово к реализации  
**Приоритет:** High  
**Оценка:** 2-3 дня для краткосрочных решений, 1-2 недели для долгосрочных
