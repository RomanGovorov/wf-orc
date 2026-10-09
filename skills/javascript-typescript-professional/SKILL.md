---
name: javascript-typescript-professional
description: Professional JavaScript/TypeScript — ES2024+ features, TypeScript 5.x types, Node.js 22, Deno, Bun, React 19, Next.js 16, Express, Fastify, Vitest, Zod. Use when writing, reviewing, or refactoring JS/TS code.
priority: 10
paths:
  - "**/src/**/*.ts"
  - "**/lib/**/*.ts"
  - "**/src/**/*.tsx"
  - "**/app/**/*.tsx"
  - "**/components/**/*.tsx"
  - "**/*.mjs"
  - "**/package.json"
  - "**/tsconfig*"
  - "**/vite.config*"
  - "**/next.config*"
  - "**/eslint.config*"
  - "**/react/**"
  - "**/next/**"
  - "**/vue/**"
  - "**/angular/**"
  - "**/express*/**"
  - "**/nest/**"
  - "**/.babelrc*"
  - "**/babel.config*"
  - "**/webpack.config*"
  - "**/rollup.config*"
  - "**/.eslintrc*"
  - "**/.prettierrc*"
  - "**/tailwind.config*"
  - "**/postcss.config*"
  - "**/deno.json*"
  - "**/bun.lockb"
  - "**/bunfig.toml"
---

# JavaScript/TypeScript Professional

Complete guide to professional JS/TS development — TypeScript 5.x strict mode, modern async patterns, Node.js 22, React 19, Next.js 16, Vitest, Zod, and structured logging.

## When to Use This Skill

- When writing new TypeScript or JavaScript code
- When reviewing or refactoring existing JS/TS code
- When setting up a Node.js, Deno, or Bun project
- When building React or Next.js applications
- When configuring Vitest, ESLint, or Prettier
- When implementing schema validation with Zod
- When designing async workflows, streams, or error handling
- When setting up dependency injection or structured logging

## Core Concepts

- **Event Loop** — single-threaded, non-blocking I/O; microtasks (Promises) before macrotasks (setTimeout); `process.nextTick` before microtasks
- **Prototype Chain** — prototypal inheritance; `class` is syntactic sugar over prototypes; `Object.create()`, `__proto__`
- **Type System** — TypeScript is a structural type system (duck typing at compile time); erased at runtime; `strict` mode catches real bugs
- **ESM Modules** — `import`/`export` is the standard; `"type": "module"` in package.json; dynamic `import()` for code splitting
- **Async First** — `async/await` over callbacks; `Promise.all`/`allSettled` for concurrency; `AbortController` for cancellation

---

## Patterns

### 1. TypeScript Strict Mode Configuration

Maximum type safety for production applications.

```jsonc
// tsconfig.json — strict configuration
{
  "compilerOptions": {
    "target": "ES2024",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "exactOptionalPropertyTypes": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true
  }
}
```

Key strict options: `noUncheckedIndexedAccess` forces undefined check on index access; `noImplicitOverride` requires explicit `override` keyword; `verbatimModuleSyntax` requires `import type` for type-only imports.

### 2. Discriminated Unions + Type Narrowing

Model complex state with exhaustive type checking.

```typescript
type ApiResponse<T> =
  | { status: "loading" }
  | { status: "success"; data: T; timestamp: number }
  | { status: "error"; code: string; message: string; retryable: boolean };

function handleResponse(response: ApiResponse<User>): string {
  switch (response.status) {
    case "loading": return "Loading...";
    case "success": return `Welcome, ${response.data.name}`;
    case "error":
      return response.retryable
        ? `Error: ${response.message} (will retry)`
        : `Fatal: ${response.message}`;
    default: return assertNever(response);
  }
}

function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${value}`);
}
```

### 3. Zod Schema Validation + Inference

Runtime validation that produces compile-time types.

```typescript
import { z } from "zod";

const UserSchema = z.object({
  id: z.number().int().positive(),
  email: z.email(),
  name: z.string().min(1).max(100),
  role: z.enum(["admin", "user", "moderator"]),
  tags: z.array(z.string()).default([]),
  createdAt: z.coerce.date(),
});

type User = z.infer<typeof UserSchema>;

const CreateUserSchema = UserSchema.omit({ id: true, createdAt: true });
type CreateUser = z.infer<typeof CreateUserSchema>;

function validateUser(input: unknown): User {
  const result = UserSchema.safeParse(input);
  if (!result.success) {
    throw new ValidationError("User validation failed", result.error.flatten().fieldErrors ?? {});
  }
  return result.data;
}
```

### 4. Async Patterns (Promise.allSettled, AbortController)

Robust concurrent and cancellable async operations.

```typescript
// Promise.allSettled — handle partial failures
async function fetchAllResources(ids: string[]) {
  const results = await Promise.allSettled(ids.map((id) => fetchResource(id)));
  return results.map((r) =>
    r.status === "fulfilled" ? { data: r.value } : { error: r.reason }
  );
}

// AbortController — cancel async operations
async function fetchWithTimeout<T>(url: string, timeoutMs = 5000): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`Request timed out after ${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
```

### 5. Error Handling (Result Type, Custom Error Classes)

Explicit error handling without exceptions.

```typescript
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

function ok<T>(value: T): Result<T, never> { return { ok: true, value }; }
function err<E>(error: E): Result<never, E> { return { ok: false, error }; }

async function findUser(id: string): Promise<Result<User, AppError>> {
  const user = await db.users.findById(id);
  if (!user) return err(new NotFoundError(`User ${id} not found`));
  return ok(user);
}

// Custom error hierarchy
class AppError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, string[]>,
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

class NotFoundError extends AppError {
  constructor(message: string) { super(404, "NOT_FOUND", message); }
}

class ValidationError extends AppError {
  constructor(message: string, public readonly fields: Record<string, string[]>) {
    super(422, "VALIDATION_ERROR", message, fields);
  }
}
```

### 6. ESM Modules

Modern module system for Node.js and browsers.

```json
{
  "name": "my-app",
  "type": "module",
  "exports": {
    ".": { "types": "./dist/index.d.ts", "import": "./dist/index.js" }
  },
  "engines": { "node": ">=22.0.0" }
}
```

```typescript
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);

// Dynamic import — lazy loading
async function loadDatabaseDriver(env: string) {
  const { PostgresDatabase } = await import("./db/postgres.js");
  return new PostgresDatabase();
}

// Top-level await (ESM only)
const config = await loadConfig();
export { config };
```

### 7. Testing with Vitest

Fast, native ESM test runner with full TypeScript support.

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";
export default defineConfig({
  test: {
    environment: "node",
    coverage: { provider: "v8", thresholds: { lines: 80, branches: 80 } },
    mockReset: true,
  },
});

// test example
import { describe, it, expect, vi, beforeEach } from "vitest";

describe("UserService.create", () => {
  it("creates a user with hashed password", async () => {
    const mockRepo = { findByEmail: vi.fn(), create: vi.fn() };
    // ... test implementation
  });
});
```

---

## Best Practices

1. **TypeScript strict mode always** — `"strict": true` in tsconfig; no `any` unless explicitly justified
2. **ESM over CommonJS** — `"type": "module"` in package.json; use `import`/`export`
3. **Zod for runtime validation** — never trust external input; validate at API boundaries
4. **Result types over exceptions** — use `Result<T, E>` for expected failures
5. **Structured logging** — `pino` in production (JSON), `pino-pretty` in development
6. **Vitest for testing** — native ESM and TypeScript support; same API as Jest but faster
7. **Dependency injection** — constructor injection with `awilix`; register in container
8. **AbortController for cancellation** — cancel fetch requests, timers; prevent memory leaks
9. **Streams for large data** — never load entire files into memory; use `pipeline()`
10. **Explicit error classes** — extend `AppError` with code, statusCode, and cause
11. **`as const` for literal types** — `const STATUS = ["active", "inactive"] as const`

---

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| `any` type assertions | Defeats TypeScript's purpose | Use `unknown` + type guards or Zod |
| `console.log` in production | Unstructured, no levels | `pino` with child loggers |
| Mixing CJS and ESM | Dual-package hazard | `"type": "module"` everywhere |
| Unhandled promise rejections | Silent failures | Always `catch` or use `Result` |
| Loading large files into memory | OOM on production | Streams + `pipeline()` |
| `==` instead of `===` | Type coercion surprises | ESLint `eqeqeq` rule |
| Missing `await` on async calls | Race conditions | ESLint `no-floating-promises` |
| Barrel files causing circular deps | Import loops | Re-export only public API |
| `catch (e: any)` | No type safety | `catch (e: unknown)` + `instanceof` |
| Not using `AbortController` | Leaked connections | Pass `signal` to `fetch` |

---

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for deep dives, edge cases, and advanced techniques
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates

---

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| TypeScript | `/microsoft/typescript` | Type system features, generics |
| Next.js | `/vercel/next.js` | App Router, Server Components, API routes |
| Node.js | `/nodejs/node` | Streams, worker threads, diagnostics |
| React | `/reactjs/react.dev` | Hooks, Server Components, Suspense |
| Vitest | `/vitest-dev/vitest` | Test configuration, mocking |
| Zod | `/colinhacks/zod` | Schema validation, type inference |
| Express.js | `/expressjs/express` | Routing, middleware, error handling |
| GraphQL | `/graphql/graphql-js` | Schema definition, resolvers |
