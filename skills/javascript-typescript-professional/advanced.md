# Advanced Patterns: JavaScript/TypeScript Professional

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Generic Constraints + Conditional Types

Build reusable, type-safe abstractions with advanced type system features.

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
```

### Edge Cases

- **Circular references in mapped types:** Use `extends object` guard to prevent infinite recursion
- **Template literal limits:** TypeScript has a recursion limit for template literal types — keep them shallow
- **Conditional type distribution:** Wrap in tuple `[T] extends [U]` to prevent distribution over unions

---

## Node.js Streams + Backpressure

Process large data efficiently without loading everything into memory.

```typescript
import { createReadStream, createWriteStream } from "node:fs";
import { Transform, type TransformCallback } from "node:stream";
import { pipeline } from "node:stream/promises";
import { createGzip } from "node:zlib";

class JsonLineParser extends Transform {
  private _buffer = "";

  constructor() {
    super({ objectMode: true });
  }

  override _transform(chunk: Buffer, _encoding: BufferEncoding, callback: TransformCallback): void {
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

  override _flush(callback: TransformCallback): void {
    if (this._buffer.trim()) {
      try {
        this.push(JSON.parse(this._buffer));
      } catch { /* ignore trailing incomplete line */ }
    }
    callback();
  }
}

// Pipeline with backpressure — automatically handles flow control
async function processLargeFile(input: string, output: string): Promise<void> {
  await pipeline(
    createReadStream(input, { highWaterMark: 64 * 1024 }),
    new JsonLineParser(),
    new Transform({
      objectMode: true,
      transform(record: unknown, _enc, cb) {
        const transformed = enrichRecord(record);
        this.push(JSON.stringify(transformed) + "\n");
        cb();
      },
    }),
    createGzip(),
    createWriteStream(output),
  );
}
```

### Performance Considerations

- **highWaterMark:** Controls buffer size — 64KB is a good default for file processing
- **Object mode:** Allows non-string/Buffer values in the stream pipeline
- **pipeline() vs pipe():** `pipeline()` handles errors and cleanup automatically; `pipe()` requires manual error handling

### Web Streams API

```typescript
// Global fetch/web streams available unflagged since Node.js 18
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

## React Server Components Patterns

Server-first component architecture with Next.js App Router.

```tsx
// app/users/page.tsx — Server Component (default)
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

export async function UserList({ query, offset }: { query: string; offset: number }) {
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
      if (value) params.set("q", value);
      else params.delete("q");
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

### Key Principles

- **Server Components by default** — zero client JS, can access DB directly
- **"use client" directive** — only when you need interactivity, hooks, or browser APIs
- **Suspense boundaries** — wrap async components for streaming HTML
- **searchParams as Promise** — Next.js 16+ makes searchParams async

---

## Dependency Injection (awilix)

Invert dependencies for testability and modularity.

```typescript
// container.ts — DI container setup
import { createContainer, asClass, asValue, InjectionMode } from "awilix";
import { PostgresPool } from "./infra/postgres-pool.js";
import { UserPostgresRepository } from "./repositories/user-postgres-repository.js";
import { UserService } from "./services/user-service.js";

export const container = createContainer({
  injectionMode: InjectionMode.PROXY,
  strict: true,
});

container.register({
  pool: asClass(PostgresPool).singleton().inject(() => ({
    connectionString: process.env.DATABASE_URL!,
  })),
  userRepository: asClass(UserPostgresRepository).singleton(),
  userService: asClass(UserService).scoped(),
});

// services/user-service.ts — constructor injection
import type { UserRepository } from "@/repositories/user-repository.js";

export class UserService {
  constructor(private readonly deps: { userRepository: UserRepository }) {}

  async findById(id: number) {
    const user = await this.deps.userRepository.findById(id);
    if (!user) throw new NotFoundError(`User ${id} not found`);
    return user;
  }
}
```

### Testing with DI

```typescript
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
    });

    const userService = new UserService(testContainer.cradle);
    // ... test implementation
  });
});
```

---

## Logging (pino Structured Output)

Production-grade structured logging.

```typescript
// lib/logger.ts
import pino from "pino";

const isProduction = process.env.NODE_ENV === "production";

export const logger = pino({
  level: process.env.LOG_LEVEL ?? (isProduction ? "info" : "debug"),
  ...(isProduction
    ? {
        formatters: { level: (label: string) => ({ level: label }) },
        timestamp: pino.stdTimeFunctions.isoTime,
      }
    : {
        transport: {
          target: "pino-pretty",
          options: { colorize: true, translateTime: "HH:MM:ss.l" },
        },
      }),
});

export function createLogger(context: Record<string, unknown>) {
  return logger.child(context);
}

// middleware/request-logger.ts — Express
import { createLogger } from "@/lib/logger";
import { randomUUID } from "node:crypto";

export function requestLogger(req: Request, res: Response, next: NextFunction) {
  const requestId = (req.headers["x-request-id"] as string) ?? randomUUID();
  const log = createLogger({ requestId, method: req.method, path: req.path });

  const start = performance.now();
  res.on("finish", () => {
    const durationMs = Math.round(performance.now() - start);
    log.info({ statusCode: res.statusCode, durationMs }, "request completed");
  });

  req.log = log;
  next();
}

// Usage in business logic
const log = createLogger({ service: "order-service" });

async function createOrder(userId: number, items: OrderItem[]): Promise<Order> {
  log.info({ userId, itemCount: items.length }, "creating order");
  const order = await db.orders.create({ userId, items });
  log.info({ orderId: order.id, total: order.total }, "order created");
  return order;
}
```

### Best Practices

- **Child loggers** — add context to all log entries in a scope
- **Structured data** — pass objects as first argument, message as second
- **Error logging** — include `err: { message, stack }` in the log data
- **Request correlation** — always include `requestId` for tracing

---

## AsyncIterable — Stream Processing

Process large files without loading into memory.

```typescript
async function* readLines(filePath: string): AsyncIterable<string> {
  const stream = createReadStream(filePath, { encoding: "utf-8" });
  let buffer = "";

  for await (const chunk of stream) {
    buffer += chunk;
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      yield line;
    }
  }

  if (buffer) yield buffer;
}

// Usage
async function processLogFile(filePath: string): Promise<void> {
  for await (const line of readLines(filePath)) {
    const entry = JSON.parse(line) as LogEntry;
    if (entry.level === "error") {
      await alertOnCall(entry);
    }
  }
}
```

---

## Concurrent Operations with Semaphore

Control concurrency for rate-limited operations.

```typescript
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
    if (next) next();
    else this.permits++;
  }
}

// Fetch 100 URLs with max 10 concurrent
async function fetchBatch(urls: string[], concurrency = 10) {
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
