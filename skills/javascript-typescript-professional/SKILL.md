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

```typescript
// tsconfig.json — strict configuration
{
  "compilerOptions": {
    "target": "ES2022",
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
    "isolatedModules": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

**Key strict options explained:**

```typescript
// noUncheckedIndexedAccess — forces undefined check on index access
const map: Record<string, number> = { a: 1 };
const val = map["b"]; // type: number | undefined (not number)

// noImplicitOverride — requires explicit 'override' keyword
class Base {
  greet() { return "hello"; }
}
class Child extends Base {
  override greet() { return "hi"; } // ✅ explicit override
}

// verbatimModuleSyntax — type-only imports must use 'import type'
import type { User } from "./types.js";  // ✅ erased at runtime
import { createUser } from "./services.js"; // ✅ kept at runtime
```

---

### 2. Discriminated Unions + Type Narrowing

Model complex state with exhaustive type checking.

```typescript
// Discriminated union — model API response states
type ApiResponse<T> =
  | { status: "loading" }
  | { status: "success"; data: T; timestamp: number }
  | { status: "error"; code: string; message: string; retryable: boolean };

// Type narrowing with switch
function handleResponse(response: ApiResponse<User>): string {
  switch (response.status) {
    case "loading":
      return "Loading...";
    case "success":
      // response.data is typed as User here
      return `Welcome, ${response.data.name}`;
    case "error":
      // response.code and response.message are available
      return response.retryable
        ? `Error: ${response.message} (will retry)`
        : `Fatal: ${response.message}`;
  }
  // TypeScript knows this is unreachable — exhaustive check
  const _exhaustive: never = response;
  return _exhaustive;
}

// Exhaustive check helper
function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${value}`);
}

// Narrowing with type predicates
function isSuccess<T>(resp: ApiResponse<T>): resp is ApiResponse<T> & { status: "success" } {
  return resp.status === "success";
}

// Usage
const resp: ApiResponse<User> = await fetchUser();
if (isSuccess(resp)) {
  console.log(resp.data.name); // ✅ narrowed to success
}
```

---

### 3. Generic Constraints + Conditional Types

Build reusable, type-safe abstractions.

```typescript
// Generic constraint — T must have an 'id' property
interface Identifiable {
  id: string | number;
}

function findById<T extends Identifiable>(items: T[], id: T["id"]): T | undefined {
  return items.find((item) => item.id === id);
}

// Conditional type — extract promise return type
type UnwrapPromise<T> = T extends Promise<infer U> ? U : T;

// Usage
type A = UnwrapPromise<Promise<string>>; // string
type B = UnwrapPromise<number>;          // number

// Mapped type with conditional
type ReadonlyDeep<T> = {
  readonly [K in keyof T]: T[K] extends object ? ReadonlyDeep<T[K]> : T[K];
};

// Template literal types
type EventName<T extends string> = `on${Capitalize<T>}`;
type ClickEvent = EventName<"click">; // "onClick"

// Generic factory with constraints
interface Repository<T extends Identifiable> {
  findById(id: T["id"]): Promise<T | undefined>;
  findAll(filter?: Partial<T>): Promise<T[]>;
  create(data: Omit<T, "id">): Promise<T>;
  update(id: T["id"], data: Partial<T>): Promise<T>;
  delete(id: T["id"]): Promise<void>;
}

// Concrete implementation
class UserPostgresRepository implements Repository<User> {
  async findById(id: number): Promise<User | undefined> {
    const row = await this.pool.query("SELECT * FROM users WHERE id = $1", [id]);
    return row.rows[0];
  }
  // ... other methods
}
```

---

### 4. Zod Schema Validation + Inference

Runtime validation that produces compile-time types.

```typescript
import { z } from "zod";

// Define schema
const UserSchema = z.object({
  id: z.number().int().positive(),
  email: z.string().email(),
  name: z.string().min(1).max(100),
  role: z.enum(["admin", "user", "moderator"]),
  preferences: z.object({
    theme: z.enum(["light", "dark"]).default("light"),
    notifications: z.boolean().default(true),
  }).optional(),
  tags: z.array(z.string()).default([]),
  createdAt: z.coerce.date(), // auto-converts strings to Date
});

// Infer TypeScript type from schema
type User = z.infer<typeof UserSchema>;
// ^ { id: number; email: string; name: string; role: "admin" | "user" | "moderator"; ... }

// Input schema (for creation — no id, no createdAt)
const CreateUserSchema = UserSchema.omit({ id: true, createdAt: true });
type CreateUser = z.infer<typeof CreateUserSchema>;

// Validation with detailed errors
function validateUser(input: unknown): User {
  const result = UserSchema.safeParse(input);
  if (!result.success) {
    const formatted = result.error.format();
    // formatted.email?._errors → ["Invalid email"]
    throw new ValidationError("User validation failed", formatted);
  }
  return result.data;
}

// API request validation
const CreateOrderSchema = z.object({
  items: z.array(z.object({
    productId: z.string().uuid(),
    quantity: z.number().int().min(1).max(100),
  })).min(1),
  shippingAddress: z.object({
    street: z.string(),
    city: z.string(),
    zip: z.string().regex(/^\d{5}(-\d{4})?$/),
    country: z.string().length(2), // ISO 3166-1 alpha-2
  }),
});

// Transform + validate
const PaginatedResponseSchema = <T extends z.ZodType>(itemSchema: T) =>
  z.object({
    data: z.array(itemSchema),
    meta: z.object({
      page: z.number(),
      pageSize: z.number(),
      total: z.number(),
      totalPages: z.number(),
    }),
  });

// Usage
const UserListSchema = PaginatedResponseSchema(UserSchema);
type UserListResponse = z.infer<typeof UserListSchema>;
```

---

### 5. Async Patterns (Promise.allSettled, AbortController, AsyncIterable)

Robust concurrent and cancellable async operations.

```typescript
// Promise.allSettled — handle partial failures
interface FetchResult<T> {
  data?: T;
  error?: Error;
}

async function fetchAllResources(ids: string[]): Promise<FetchResult<Resource>[]> {
  const results = await Promise.allSettled(
    ids.map((id) => fetchResource(id))
  );

  return results.map((result) =>
    result.status === "fulfilled"
      ? { data: result.value }
      : { error: result.reason }
  );
}

// AbortController — cancel async operations
async function fetchWithTimeout<T>(
  url: string,
  timeoutMs: number = 5000
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
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

// AsyncIterable — stream processing
async function* readLines(filePath: string): AsyncIterable<string> {
  const stream = createReadStream(filePath, { encoding: "utf-8" });
  let buffer = "";

  for await (const chunk of stream) {
    buffer += chunk;
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? ""; // keep incomplete line

    for (const line of lines) {
      yield line;
    }
  }

  if (buffer) yield buffer;
}

// Usage — process large files without loading into memory
async function processLogFile(filePath: string): Promise<void> {
  for await (const line of readLines(filePath)) {
    const entry = JSON.parse(line) as LogEntry;
    if (entry.level === "error") {
      await alertOnCall(entry);
    }
  }
}

// Concurrent with semaphore
class Semaphore {
  private permits: number;
  private queue: Array<() => void> = [];

  constructor(permits: number) {
    this.permits = permits;
  }

  async acquire(): Promise<void> {
    if (this.permits > 0) {
      this.permits--;
      return;
    }
    return new Promise<void>((resolve) => {
      this.queue.push(resolve);
    });
  }

  release(): void {
    const next = this.queue.shift();
    if (next) {
      next();
    } else {
      this.permits++;
    }
  }
}

// Fetch 100 URLs with max 10 concurrent
async function fetchBatch(urls: string[], concurrency: number = 10) {
  const sem = new Semaphore(concurrency);
  const results = await Promise.allSettled(
    urls.map(async (url) => {
      await sem.acquire();
      try {
        return await fetchWithTimeout(url);
      } finally {
        sem.release();
      }
    })
  );
  return results;
}
```

---

### 6. ESM Modules (import.meta, Dynamic Import, "type": "module")

Modern module system for Node.js and browsers.

```json
// package.json — ESM configuration
{
  "name": "my-app",
  "type": "module",
  "main": "./dist/index.js",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "types": "./dist/index.d.ts"
    },
    "./utils": {
      "import": "./dist/utils/index.js",
      "types": "./dist/utils/index.d.ts"
    }
  },
  "engines": {
    "node": ">=22.0.0"
  }
}
```

```typescript
// Static imports — resolved at compile time
import { readFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

// __dirname equivalent in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Dynamic import — lazy loading, code splitting
async function loadDatabaseDriver(env: string) {
  if (env === "test") {
    const { MockDatabase } = await import("./db/mock.js");
    return new MockDatabase();
  }
  const { PostgresDatabase } = await import("./db/postgres.js");
  return new PostgresDatabase();
}

// import.meta — module metadata
console.log(import.meta.url);   // file:///path/to/module.js
console.log(import.meta.resolve("./config.json")); // resolved path

// Top-level await (ESM only)
const config = await loadConfig();
export { config };
```

---

### 7. Error Handling (Result Type Pattern, Custom Error Classes)

Explicit error handling without exceptions.

```typescript
// Result type — Rust-inspired explicit error handling
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

function ok<T>(value: T): Result<T, never> {
  return { ok: true, value };
}

function err<E>(error: E): Result<never, E> {
  return { ok: false, error };
}

// Usage
async function findUser(id: string): Promise<Result<User, AppError>> {
  const user = await db.users.findById(id);
  if (!user) {
    return err(new NotFoundError(`User ${id} not found`));
  }
  return ok(user);
}

// Call site — explicit handling
const result = await findUser("123");
if (result.ok) {
  console.log(result.value.name);
} else {
  console.error(result.error.message);
}

// Custom error hierarchy
class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number = 500,
    public readonly cause?: Error,
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

class NotFoundError extends AppError {
  constructor(message: string) {
    super(message, "NOT_FOUND", 404);
  }
}

class ValidationError extends AppError {
  constructor(
    message: string,
    public readonly fields: Record<string, string[]>,
  ) {
    super(message, "VALIDATION_ERROR", 422);
  }
}

class AuthenticationError extends AppError {
  constructor(message: string = "Authentication required") {
    super(message, "UNAUTHORIZED", 401);
  }
}

// Error handler middleware (Express/Fastify)
function errorHandler(error: Error, _req: Request, res: Response): void {
  if (error instanceof AppError) {
    res.status(error.statusCode).json({
      error: { code: error.code, message: error.message },
    });
    return;
  }

  // Unknown error — don't leak internals
  console.error("Unhandled error:", error);
  res.status(500).json({
    error: { code: "INTERNAL_ERROR", message: "An unexpected error occurred" },
  });
}
```

---

### 8. Node.js Streams + Backpressure

Process large data efficiently without loading everything into memory.

```typescript
import { createReadStream, createWriteStream } from "node:fs";
import { Transform } from "node:stream";
import { pipeline } from "node:stream/promises";
import { createGzip } from "node:zlib";

// Transform stream — process data chunk by chunk
class JsonLineParser extends Transform {
  constructor() {
    super({ objectMode: true });
    this._buffer = "";
  }

  override _transform(chunk: Buffer, _encoding: string, callback: () => void): void {
    this._buffer += chunk.toString();
    const lines = this._buffer.split("\n");
    this._buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.trim()) {
        try {
          this.push(JSON.parse(line));
        } catch {
          this.emit("warning", new Error(`Invalid JSON: ${line.slice(0, 50)}`));
        }
      }
    }
    callback();
  }

  override _flush(callback: () => void): void {
    if (this._buffer.trim()) {
      try {
        this.push(JSON.parse(this._buffer));
      } catch {
        // ignore trailing incomplete line
      }
    }
    callback();
  }
}

// Pipeline with backpressure — automatically handles flow control
async function processLargeFile(input: string, output: string): Promise<void> {
  await pipeline(
    createReadStream(input, { highWaterMark: 64 * 1024 }), // 64KB chunks
    new JsonLineParser(),
    new Transform({
      objectMode: true,
      transform(record: unknown, _enc, cb) {
        // Process each record
        const transformed = enrichRecord(record);
        this.push(JSON.stringify(transformed) + "\n");
        cb();
      },
    }),
    createGzip(),
    createWriteStream(output),
  );
}

// Web Streams API (Node.js 22+)
async function streamResponse(url: string): Promise<void> {
  const response = await fetch(url);
  if (!response.body) throw new Error("No response body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    process.stdout.write(decoder.decode(value, { stream: true }));
  }
}
```

---

### 9. React Server Components Patterns

Server-first component architecture with Next.js App Router.

```tsx
// app/users/page.tsx — Server Component (default)
// Runs on server, zero client JS, can access DB directly
import { db } from "@/lib/db";
import { UserList } from "./UserList";
import { Suspense } from "react";

interface UsersPageProps {
  searchParams: Promise<{ q?: string; page?: string }>;
}

export default async function UsersPage({ searchParams }: UsersPageProps) {
  const { q = "", page = "1" } = await searchParams;
  const offset = (Number(page) - 1) * 20;

  return (
    <div>
      <h1>Users</h1>
      <Suspense fallback={<UserListSkeleton />}>
        <UserList query={q} offset={offset} />
      </Suspense>
    </div>
  );
}

// app/users/UserList.tsx — Server Component with data access
import { db } from "@/lib/db";

async function UserList({ query, offset }: { query: string; offset: number }) {
  // Direct database access — no API layer needed
  const users = await db.users.findMany({
    where: query ? { name: { contains: query } } : undefined,
    take: 20,
    skip: offset,
    orderBy: { createdAt: "desc" },
  });

  return (
    <ul>
      {users.map((user) => (
        <li key={user.id}>
          {user.name} — {user.email}
        </li>
      ))}
    </ul>
  );
}

// app/users/SearchInput.tsx — Client Component
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

export function SearchInput() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  function handleChange(value: string) {
    startTransition(() => {
      const params = new URLSearchParams(searchParams);
      if (value) {
        params.set("q", value);
      } else {
        params.delete("q");
      }
      router.push(`/users?${params.toString()}`);
    });
  }

  return (
    <input
      type="search"
      defaultValue={searchParams.get("q") ?? ""}
      onChange={(e) => handleChange(e.target.value)}
      placeholder="Search users..."
      aria-label="Search users"
    />
  );
}
```

---

### 10. Testing with Vitest

Fast, native ESM test runner with full TypeScript support.

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    globals: false,
    environment: "node",
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      thresholds: {
        lines: 80,
        branches: 80,
        functions: 80,
        statements: 80,
      },
    },
    mockReset: true,
    restoreMocks: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
});
```

```typescript
// test/unit/test_user_service_create.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { UserService } from "@/services/user-service";
import type { UserRepository } from "@/repositories/user-repository";

describe("UserService.create", () => {
  let service: UserService;
  let mockRepo: UserRepository;

  beforeEach(() => {
    mockRepo = {
      findById: vi.fn(),
      findByEmail: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    };
    service = new UserService(mockRepo);
  });

  it("creates a user with hashed password", async () => {
    mockRepo.findByEmail.mockResolvedValue(undefined);
    mockRepo.create.mockResolvedValue({
      id: 1,
      email: "test@example.com",
      name: "Test",
      role: "user",
    });

    const result = await service.create({
      email: "test@example.com",
      name: "Test",
      password: "secure123",
    });

    expect(result).toMatchObject({
      email: "test@example.com",
      name: "Test",
    });
    expect(mockRepo.create).toHaveBeenCalledWith(
      expect.objectContaining({
        email: "test@example.com",
        hashedPassword: expect.any(String),
      })
    );
    // Ensure raw password is not stored
    expect(mockRepo.create).not.toHaveBeenCalledWith(
      expect.objectContaining({ password: "secure123" })
    );
  });

  it("throws ValidationError for duplicate email", async () => {
    mockRepo.findByEmail.mockResolvedValue({
      id: 1,
      email: "existing@example.com",
      name: "Existing",
      role: "user",
    });

    await expect(
      service.create({
        email: "existing@example.com",
        name: "Test",
        password: "secure123",
      })
    ).rejects.toThrow("Email already exists");
  });

  it("throws ValidationError for weak password", async () => {
    await expect(
      service.create({
        email: "test@example.com",
        name: "Test",
        password: "123",
      })
    ).rejects.toThrow("Password must be at least 8 characters");
  });
});
```

---

### 11. Dependency Injection (awilix)

Invert dependencies for testability and modularity. No decorators needed — awilix uses registration-based DI with automatic resolution.

```typescript
// container.ts — DI container setup
import { createContainer, asClass, asValue, InjectionMode } from "awilix";
import { PostgresPool } from "./infra/postgres-pool.js";
import { UserPostgresRepository } from "./repositories/user-postgres-repository.js";
import { UserService } from "./services/user-service.js";
import { EmailService } from "./services/email-service.js";

export const container = createContainer({
  injectionMode: InjectionMode.PROXY,
  strict: true,
});

container.register({
  pool: asClass(PostgresPool).singleton().inject(() => ({
    connectionString: process.env.DATABASE_URL!,
  })),
  userRepository: asClass(UserPostgresRepository).singleton(),
  emailService: asClass(EmailService).singleton(),
  userService: asClass(UserService).scoped(),
});

export type AppContainer = typeof container;
```

```typescript
// services/user-service.ts — constructor injection via destructuring
import type { UserRepository } from "@/repositories/user-repository.js";
import type { EmailService } from "@/services/email-service.js";

export class UserService {
  constructor(
    private readonly deps: {
      userRepository: UserRepository;
      emailService: EmailService;
    },
  ) {}

  async create(data: CreateUserInput): Promise<User> {
    const { userRepository, emailService } = this.deps;
    const existing = await userRepository.findByEmail(data.email);
    if (existing) {
      throw new ValidationError("Email already exists", {
        email: ["This email is already registered"],
      });
    }

    const hashedPassword = await hashPassword(data.password);
    const user = await userRepository.create({
      ...data,
      hashedPassword,
    });

    await emailService.sendWelcome(user.email, user.name);
    return user;
  }

  async findById(id: number): Promise<User> {
    const user = await this.deps.userRepository.findById(id);
    if (!user) {
      throw new NotFoundError(`User ${id} not found`);
    }
    return user;
  }
}
```

```typescript
// test — easy mocking with awilix
import { createContainer, asValue } from "awilix";
import { UserService } from "@/services/user-service.js";
import { vi, describe, it, expect } from "vitest";

describe("UserService with DI", () => {
  it("creates user successfully", async () => {
    const testContainer = createContainer({ strict: true });
    testContainer.register({
      userRepository: asValue({
        findByEmail: vi.fn().mockResolvedValue(undefined),
        create: vi.fn().mockResolvedValue({ id: 1, email: "test@test.com" }),
      }),
      emailService: asValue({
        sendWelcome: vi.fn().mockResolvedValue(undefined),
      }),
    });

    const userService = new UserService(testContainer.cradle);
    const user = await userService.create({
      email: "test@test.com",
      password: "secure123",
      name: "Test",
    });

    expect(user.id).toBe(1);
  });
});
```

---

### 12. Logging (pino Structured Output)

Production-grade structured logging with pino.

```typescript
// lib/logger.ts — pino configuration
import pino from "pino";

const isProduction = process.env.NODE_ENV === "production";

export const logger = pino({
  level: process.env.LOG_LEVEL ?? (isProduction ? "info" : "debug"),
  ...(isProduction
    ? {
        // Production: JSON output for log aggregators
        formatters: {
          level: (label: string) => ({ level: label }),
        },
        timestamp: pino.stdTimeFunctions.isoTime,
      }
    : {
        // Development: pretty-printed output
        transport: {
          target: "pino-pretty",
          options: {
            colorize: true,
            translateTime: "HH:MM:ss.l",
            ignore: "pid,hostname",
          },
        },
      }),
});

// Child logger — add context to all log entries in a scope
export function createLogger(context: Record<string, unknown>) {
  return logger.child(context);
}
```

```typescript
// middleware/request-logger.ts — Express/Fastify middleware
import { createLogger } from "@/lib/logger";
import type { Request, Response, NextFunction } from "express";
import { randomUUID } from "node:crypto";

export function requestLogger(req: Request, res: Response, next: NextFunction) {
  const requestId = (req.headers["x-request-id"] as string) ?? randomUUID();
  const log = createLogger({
    requestId,
    method: req.method,
    path: req.path,
    ip: req.ip,
  });

  const start = performance.now();

  res.on("finish", () => {
    const durationMs = Math.round(performance.now() - start);
    log.info(
      { statusCode: res.statusCode, durationMs },
      "request completed"
    );
  });

  // Attach logger to request for downstream use
  (req as any).log = log;
  next();
}
```

```typescript
// Usage in business logic
import { createLogger } from "@/lib/logger";

const log = createLogger({ service: "order-service" });

async function createOrder(userId: number, items: OrderItem[]): Promise<Order> {
  log.info({ userId, itemCount: items.length }, "creating order");

  const order = await db.orders.create({ userId, items });

  log.info(
    { orderId: order.id, total: order.total, userId },
    "order created"
  );

  return order;
}

// Error logging
async function processPayment(orderId: string): Promise<void> {
  try {
    await paymentGateway.charge(orderId);
    log.info({ orderId }, "payment processed");
  } catch (error) {
    log.error(
      {
        orderId,
        err: error instanceof Error ? { message: error.message, stack: error.stack } : error,
      },
      "payment processing failed"
    );
    throw error;
  }
}
```

---

## Best Practices

1. **TypeScript strict mode always** — `"strict": true` in tsconfig; no `any` unless explicitly justified with a comment
2. **ESM over CommonJS** — `"type": "module"` in package.json; use `import`/`export`; Node.js 22+ has full ESM support
3. **Zod for runtime validation** — never trust external input; validate at API boundaries; infer types from schemas
4. **Result types over exceptions** — use `Result<T, E>` for expected failures; throw only for truly unexpected errors
5. **Structured logging** — `pino` in production (JSON), `pino-pretty` in development; never `console.log` in production code
6. **Vitest for testing** — native ESM and TypeScript support; same API as Jest but faster; use `describe`/`it`/`expect`
7. **Dependency injection** — constructor injection with `awilix`; register in container, not in business logic
8. **AbortController for cancellation** — cancel fetch requests, timers, and event listeners; prevent memory leaks
9. **Streams for large data** — never load entire files into memory; use `pipeline()` for automatic backpressure handling
10. **Barrel files cautiously** — re-export from `index.ts` only for public API; avoid circular dependencies
11. **Explicit error classes** — extend `AppError` with code, statusCode, and cause; never throw plain strings
12. **`as const` for literal types** — `const STATUS = ["active", "inactive"] as const` preserves literal types

---

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| `any` type assertions | Defeats TypeScript's purpose | Use `unknown` + type guards or Zod validation |
| `console.log` in production | Unstructured, no levels, no context | `pino` with child loggers |
| Mixing CJS and ESM | Dual-package hazard, import errors | `"type": "module"` everywhere; use `import` |
| Unhandled promise rejections | Silent failures, process crash | Always `catch` or use `Result` type |
| Loading large files into memory | OOM on production workloads | Streams + `pipeline()` |
| `==` instead of `===` | Type coercion surprises | ESLint `eqeqeq` rule; TypeScript catches most |
| Missing `await` on async calls | Unhandled promises, race conditions | ESLint `no-floating-promises`; review all async functions |
| Barrel files causing circular deps | Import loops, tree-shaking failures | Re-export only public API; avoid `index.ts` chains |
| `catch (e: any)` | Loses error context, no type safety | `catch (e: unknown)` + `instanceof` or `Result` |
| Not using `AbortController` | Leaked connections on timeout/navigation | Pass `signal` to `fetch`; clean up in `finally` |

---

## Context7 Integration

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

Use `mcp__context7__resolve-library-id` then `mcp__context7__query-docs`.
