# Code Examples: JavaScript/TypeScript Professional

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Complete Vitest Test Suite

```typescript
// test/unit/test_user_service_create.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { UserService } from "@/services/user-service";
import type { UserRepository } from "@/repositories/user-repository";
import type { EmailService } from "@/services/email-service";

describe("UserService.create", () => {
  let service: UserService;
  let mockRepo: UserRepository;
  let mockEmailService: EmailService;

  beforeEach(() => {
    // Type each vi.fn() with the exact method signature from the interface
    mockRepo = {
      findById: vi.fn<UserRepository["findById"]>(),
      findByEmail: vi.fn<UserRepository["findByEmail"]>(),
      create: vi.fn<UserRepository["create"]>(),
      update: vi.fn<UserRepository["update"]>(),
      delete: vi.fn<UserRepository["delete"]>(),
    } as UserRepository;
    mockEmailService = { sendWelcome: vi.fn<EmailService["sendWelcome"]>() } as EmailService;
    service = new UserService({
      userRepository: mockRepo,
      emailService: mockEmailService,
    });
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
      password: "secure123456",
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
      expect.objectContaining({ password: "secure123456" })
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
        password: "secure123456",
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
    ).rejects.toThrow("Password must be at least 12 characters");
  });
});
```

---

## Example 2: Full DI Container Setup with awilix

```typescript
// container.ts
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
// services/user-service.ts
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

    if (data.password.length < 12) {
      throw new ValidationError("Password must be at least 12 characters", {
        password: ["Password must be at least 12 characters"],
      });
    }

    const existing = await userRepository.findByEmail(data.email);
    if (existing) {
      throw new ValidationError("Email already exists", {
        email: ["This email is already registered"],
      });
    }

    const { password: _password, ...safeData } = data;
    const hashedPassword = await hashPassword(data.password);
    const user = await userRepository.create({ ...safeData, hashedPassword });

    await emailService.sendWelcome(user.email, user.name);
    return user;
  }

  async findById(id: number): Promise<User> {
    const user = await this.deps.userRepository.findById(id);
    if (!user) throw new NotFoundError(`User ${id} not found`);
    return user;
  }
}
```

---

## Example 3: Express Error Handler

```typescript
import type { Request, Response, NextFunction } from 'express';

// Express error handler — MUST declare all 4 args
function errorHandler(error: Error, _req: Request, res: Response, _next: NextFunction): void {
  if (error instanceof AppError) {
    res.status(error.statusCode).json({
      error: { code: error.code, message: error.message, details: error.details ?? {} },
    });
    return;
  }

  // Unknown error — don't leak internals
  console.error("Unhandled error:", error);
  res.status(500).json({
    error: { code: "INTERNAL_ERROR", message: "An unexpected error occurred" },
  });
}
// app.use(errorHandler) — register AFTER all routes/middleware
```

---

## Example 4: Fastify Error Handler

```typescript
// Fastify has NO middleware — register an error handler instead
fastifyApp.setErrorHandler((error, request, reply) => {
  if (error instanceof AppError) {
    reply.status(error.statusCode).send({
      error: { code: error.code, message: error.message, details: error.details ?? {} },
    });
    return;
  }

  request.log.error({ err: error }, "Unhandled error");
  reply.status(500).send({
    error: { code: "INTERNAL_ERROR", message: "An unexpected error occurred" },
  });
});
```

---

## Example 5: Generic Repository Implementation

```typescript
import type { Pool } from "pg";

interface Identifiable {
  id: string | number;
}

interface Repository<T extends Identifiable> {
  findById(id: T["id"]): Promise<T | undefined>;
  findAll(filter?: Partial<T>): Promise<T[]>;
  create(data: Omit<T, "id">): Promise<T>;
}

class UserPostgresRepository implements Repository<User> {
  constructor(private readonly pool: Pool) {}

  async findById(id: number): Promise<User | undefined> {
    const result = await this.pool.query<User>("SELECT * FROM users WHERE id = $1", [id]);
    const row = result.rows[0];
    if (!row) return undefined;
    return row;
  }

  async findAll(filter?: Partial<User>): Promise<User[]> {
    const conditions: string[] = [];
    const values: unknown[] = [];
    let paramIndex = 1;

    if (filter?.email) {
      conditions.push(`email = $${paramIndex++}`);
      values.push(filter.email);
    }
    if (filter?.role) {
      conditions.push(`role = $${paramIndex++}`);
      values.push(filter.role);
    }

    const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";
    const result = await this.pool.query<User>(
      `SELECT * FROM users ${where} ORDER BY created_at DESC`,
      values
    );
    return result.rows;
  }

  async create(data: Omit<User, "id">): Promise<User> {
    const result = await this.pool.query<User>(
      `INSERT INTO users (email, name, role, hashed_password)
       VALUES ($1, $2, $3, $4)
       RETURNING *`,
      [data.email, data.name, data.role, data.hashedPassword]
    );
    return result.rows[0];
  }
}
```

---

## Example 6: Zod Paginated Response Schema

```typescript
import { z } from "zod";

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

const UserSchema = z.object({
  id: z.number().int().positive(),
  email: z.email(),
  name: z.string().min(1).max(100),
  role: z.enum(["admin", "user", "moderator"]),
});

const UserListSchema = PaginatedResponseSchema(UserSchema);
type UserListResponse = z.infer<typeof UserListSchema>;

// Usage in API client
async function fetchUsers(page: number): Promise<UserListResponse> {
  const response = await fetch(`/api/users?page=${page}`);
  const data = await response.json();
  return UserListSchema.parse(data);
}
```

---

## Example 7: Type Predicates for Narrowing

```typescript
type ApiResponse<T> =
  | { status: "loading" }
  | { status: "success"; data: T; timestamp: number }
  | { status: "error"; code: string; message: string; retryable: boolean };

// Type predicate for narrowing
function isSuccess<T>(resp: ApiResponse<T>): resp is ApiResponse<T> & { status: "success" } {
  return resp.status === "success";
}

function isError<T>(resp: ApiResponse<T>): resp is ApiResponse<T> & { status: "error" } {
  return resp.status === "error";
}

// Usage
const resp: ApiResponse<User> = await fetchUser();
if (isSuccess(resp)) {
  console.log(resp.data.name); // ✅ narrowed to success
} else if (isError(resp)) {
  console.error(resp.message); // ✅ narrowed to error
}
```

---

## Example 8: Module Augmentation for Express

```typescript
import type { Logger } from "pino";

// Module augmentation — makes req.log type-safe
declare global {
  namespace Express {
    interface Request {
      log: Logger;
    }
  }
}

// Now req.log is typed everywhere
app.use((req, res, next) => {
  req.log.info("Request received"); // ✅ type-safe
  next();
});
```
