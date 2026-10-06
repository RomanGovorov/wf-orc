# Verification Protocol Implementation Summary

**Дата:** 2026-10-06  
**Статус:** ✅ Реализовано

---

## 📋 Что было сделано

### 1. Создан Orchestrator Verification Protocol

**Файл:** `templates/fragments/orchestrator_verification_protocol.md`

**Содержание:**
- Пошаговая инструкция по проверке статуса agents
- Примеры кода для Qwen Code и Claude Code
- Timeout и retry логика
- Diagnostic commands
- Common mistakes to avoid
- Platform-specific notes
- Summary checklist

### 2. Обновлены все workflow команды

**Файлы обновлены:**
- ✅ `templates/commands/run.md.tmpl` — добавлен verification protocol
- ✅ `templates/commands/full.md.tmpl` — добавлен verification protocol
- ✅ `templates/commands/research.md.tmpl` — добавлен verification protocol

### 3. Перегенерирована документация

**Команда:** `python3 scripts/generate_all.py`

**Результат:**
- ✅ `commands/wf-orc/run.md` — сгенерирован с verification protocol
- ✅ `commands/wf-orc/full.md` — сгенерирован с verification protocol
- ✅ `commands/wf-orc/research.md` — сгенерирован с verification protocol
- ✅ `GEMINI.md` — обновлен
- ✅ `AGENTS.md` — обновлен (копия GEMINI.md)

---

## 🎯 Ключевые добавления

### Проверка статуса через list_agents (MANDATORY)

```javascript
// После EVERY agent launch
const agents = await list_agents();
const myAgent = agents.find(a => a.task_id === result.task_id);

if (!myAgent) {
  throw new Error(`Agent ${result.task_id} not found in roster`);
}

if (myAgent.status === "completed") {
  // Parse result and continue workflow
} else if (myAgent.status === "running") {
  // Wait for completion
} else if (myAgent.status === "failed") {
  // Handle error
}
```

### Timeout и Retry логика

```javascript
async function launchAgentWithRetry(agentType, prompt, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const result = await agent(subagent_type=agentType, prompt=prompt);
      const agents = await list_agents();
      const myAgent = agents.find(a => a.task_id === result.task_id);
      
      if (myAgent && myAgent.status === "completed") {
        return result; // Success
      }
    } catch (error) {
      if (attempt === maxRetries) {
        return { status: "pass", blocked: true, error: error.message };
      }
      await sleep(1000 * attempt); // Exponential backoff
    }
  }
}
```

### Common Mistakes to Avoid

❌ **WRONG:** "Project-manager недоступен" (без проверки статуса)  
✅ **RIGHT:** Проверить `list_agents()` → найти agent → проверить `status`

❌ **WRONG:** "Workflow не работает" (после одного неудачного вызова)  
✅ **RIGHT:** Retry 3 раза с exponential backoff → если все failed → задокументировать и продолжить

❌ **WRONG:** Работать напрямую, пропуская workflow  
✅ **RIGHT:** Всегда следовать workflow — даже если задача кажется простой

---

## 📂 Структура файлов

```
wf-orc/
├── templates/
│   ├── fragments/
│   │   └── orchestrator_verification_protocol.md  ← НОВЫЙ
│   └── commands/
│       ├── run.md.tmpl       ← ОБНОВЛЕН
│       ├── full.md.tmpl      ← ОБНОВЛЕН
│       └── research.md.tmpl  ← ОБНОВЛЕН
├── commands/wf-orc/
│   ├── run.md                ← ОБНОВЛЕН (auto-generated)
│   ├── full.md               ← ОБНОВЛЕН (auto-generated)
│   └── research.md           ← ОБНОВЛЕН (auto-generated)
├── GEMINI.md                 ← ОБНОВЛЕН (auto-generated)
└── AGENTS.md                 ← ОБНОВЛЕН (auto-generated)
```

---

## ✅ Checklist для оркестратора (из документации)

Перед интерпретацией результата:

- [ ] Agent launched successfully (no tool error)
- [ ] Agent status checked via `list_agents`
- [ ] Agent status is "completed" (not "running" or "failed")
- [ ] Agent result parsed from JSON
- [ ] Required fields present (`status`, `artifacts`, flags)
- [ ] Special flags handled (`needs_user_input`, `blocked`)
- [ ] Transitions evaluated based on agent result
- [ ] Next agent launched based on matching transition

**NEVER assume agent tool is unavailable without explicit evidence (tool error message).**

---

## 🔗 Связанные файлы

- `WORKFLOW-ANALYSIS-AND-SOLUTIONS.md` — Полный анализ проблемы
- `templates/fragments/orchestrator_verification_protocol.md` — Verification protocol
- `commands/wf-orc/run.md` — Обновленная документация
- `workflow.yaml` — Single source of truth для transitions

---

## 🚀 Следующие шаги

1. **Протестировать** новый verification protocol в unirec-base
2. **Мониторить** работу оркестратора — убедиться, что он следует protocol
3. **Собрать feedback** — есть ли улучшения
4. **Добавить tests** — для verification protocol (опционально)

---

**Статус:** ✅ Готово к использованию  
**Версия:** 0.6.2  
**Дата обновления:** 2026-10-06
