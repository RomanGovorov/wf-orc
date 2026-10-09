---
name: java-professional
description: Professional Java 21+ — records, sealed classes, pattern matching, virtual threads, Spring Boot 3.x/4.x, Jakarta EE, JUnit 5, Gradle, Maven. Use when writing, reviewing, or refactoring Java code.
priority: 10
paths:
  - "**/src/**/*.java"
  - "**/main/**/*.java"
  - "**/test/**/*.java"
  - "**/pom.xml"
  - "**/build.gradle*"
  - "**/settings.gradle*"
  - "**/application*.yml"
  - "**/application*.properties"
  - "**/gradlew*"
  - "**/.mvn/**"
  - "**/mvnw*"
  - "**/logback*.xml"
  - "**/log4j*"
  - "**/spring/**"
---

# Java Professional

Complete guide to professional Java 21+ development — modern language features, Spring Boot 4, Jakarta EE, testing, build tools, and production patterns.

## When to Use This Skill

- When writing new Java code (Java 21+)
- When reviewing or refactoring legacy Java
- When setting up a Spring Boot application
- When designing JPA/Hibernate data layer
- When configuring Spring Security (JWT, OAuth2)
- When writing JUnit 5/6 tests (JUnit 6 keeps the Jupiter programming model)
- When structuring Gradle or Maven multi-module projects
- When working with virtual threads and structured concurrency

## Core Concepts

- **JVM Memory Model** — heap (young/old gen), stack, metaspace, direct memory; tune with `-Xms`, `-Xmx`, `-XX:MaxMetaspaceSize`
- **Garbage Collection** — G1 is the default collector (JDK 21 and 25 LTS); ZGC is opt-in via `-XX:+UseZGC` for low-latency workloads
- **Class Loading** — bootstrap → platform → application classloaders; classpath vs module path (JPMS)
- **Platform Threads vs Virtual Threads** — virtual threads are lightweight, managed by JVM, ideal for I/O-bound workloads
- **Records** — immutable data carriers with auto-generated `equals()`, `hashCode()`, `toString()`
- **Sealed Classes** — restrict which classes can extend/implement; enables exhaustive pattern matching
- **Pattern Matching** — `instanceof` patterns (16+), switch expressions (14+), switch pattern matching (21+)

## Patterns

### 1. Records + Pattern Matching

```java
// Record — immutable data carrier
public record UserDTO(String name, String email, int age) {
    public UserDTO {
        if (name == null || name.isBlank())
            throw new IllegalArgumentException("Name must not be blank");
        if (age < 0 || age > 150)
            throw new IllegalArgumentException("Age must be between 0 and 150");
    }
    public String displayName() { return name + " <" + email + ">"; }
}

// Sealed interface + permits — exhaustive pattern matching
public sealed interface Shape permits Circle, Rectangle, Triangle {
    double area();
}

public record Circle(double radius) implements Shape {
    public double area() { return Math.PI * radius * radius; }
}
public record Rectangle(double width, double height) implements Shape {
    public double area() { return width * height; }
}
public record Triangle(double base, double height) implements Shape {
    public double area() { return 0.5 * base * height; }
}

// Switch expression with pattern matching (Java 21+)
public String describe(Shape shape) {
    return switch (shape) {
        case Circle c when c.radius() > 100 -> "Large circle (r=" + c.radius() + ")";
        case Circle c    -> "Circle (r=" + c.radius() + ")";
        case Rectangle r -> "Rectangle " + r.width() + "x" + r.height();
        case Triangle t  -> "Triangle (base=" + t.base() + ")";
    };
}
```

### 2. Virtual Threads

```java
// Virtual thread executor — preferred approach
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    IntStream.range(0, 10_000).forEach(i -> {
        executor.submit(() -> {
            Thread.sleep(Duration.ofSeconds(1)); // blocking is cheap on VT
            return fetchFromApi(i);
        });
    });
} // auto-closes: waits for all tasks

// synchronized + virtual threads — pinning rules depend on JDK version
// JDK 21–23: synchronized blocks pin the VT to its carrier thread
// JDK 24+:   pinning eliminated (JEP 491) — VT unmounts inside synchronized

// JDK 21–23: prefer ReentrantLock around blocking calls
private final ReentrantLock lock = new ReentrantLock();
lock.lock();
try {
    httpClient.send(request, BodyHandlers.ofString());
} finally {
    lock.unlock();
}
```

### 3. Spring Boot REST Controllers

```java
@RestController
@RequestMapping("/api/v1/users")
@Tag(name = "Users", description = "User management API")
@Validated
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    @Operation(summary = "List users with pagination")
    public Page<UserResponse> listUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") @Max(100) int size,
            @RequestParam(required = false) String search) {
        return userService.findAll(PageRequest.of(page, size), search);
    }

    @GetMapping("/{id}")
    public UserResponse getUser(@PathVariable Long id) {
        return userService.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("User", id));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public UserResponse createUser(@Valid @RequestBody CreateUserRequest request) {
        return userService.create(request);
    }
}

// Request DTO with validation
public record CreateUserRequest(
    @NotBlank @Size(max = 100) String name,
    @NotBlank @Email String email,
    @Min(0) @Max(150) Integer age,
    @Size(max = 500) String bio
) {}
```

### 4. Spring Data JPA

```java
@Entity
@Table(name = "users")
public class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(nullable = false, length = 100)
    private String name;
    @Column(nullable = false, unique = true, length = 255)
    private String email;
    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Order> orders = new ArrayList<>();
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private Role role = Role.USER;
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;
    @PrePersist void onCreate() { this.createdAt = Instant.now(); }
}

public interface UserRepository extends JpaRepository<User, Long>,
                                         JpaSpecificationExecutor<User> {
    Optional<User> findByEmail(String email);
    boolean existsByEmail(String email);
    @Query("SELECT u FROM User u WHERE u.role = :role AND u.createdAt > :since")
    List<User> findActiveByRole(@Param("role") Role role, @Param("since") Instant since);
    Page<User> findByRole(Role role, Pageable pageable);
}
```

### 5. Spring Security (JWT)

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    private final JwtTokenProvider jwtTokenProvider;

    public SecurityConfig(JwtTokenProvider jwtTokenProvider) {
        this.jwtTokenProvider = jwtTokenProvider;
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable) // stateless API only
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter()))
            )
            .build();
    }

    @Bean
    public JwtAuthenticationConverter jwtAuthenticationConverter() {
        var grantedAuthoritiesConverter = new JwtGrantedAuthoritiesConverter();
        grantedAuthoritiesConverter.setAuthorityPrefix("ROLE_");
        grantedAuthoritiesConverter.setAuthoritiesClaimName("roles");
        var converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(grantedAuthoritiesConverter);
        return converter;
    }
}
```

### 6. Exception Handling (ProblemDetail)

```java
public abstract class BusinessException extends RuntimeException {
    private final String errorCode;
    protected BusinessException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }
    public String getErrorCode() { return errorCode; }
}

public class ResourceNotFoundException extends BusinessException {
    public ResourceNotFoundException(String entity, Object id) {
        super("RESOURCE_NOT_FOUND", entity + " not found with id: " + id);
    }
}

@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ProblemDetail> handleNotFound(ResourceNotFoundException ex) {
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        detail.setTitle("Resource Not Found");
        detail.setProperty("errorCode", ex.getErrorCode());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(detail);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ProblemDetail> handleGeneric(Exception ex) {
        log.error("Unexpected error", ex);
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR,
            "An unexpected error occurred");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(detail);
    }
}
```

### 7. Testing (JUnit 5 + Mockito)

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {
    @Mock UserRepository userRepository;
    @Mock EmailService emailService;
    @InjectMocks UserService userService;

    @Test
    @DisplayName("Should create user with valid data")
    void shouldCreateUser() {
        var request = new CreateUserRequest("John", "john@example.com", 30, null);
        when(userRepository.existsByEmail("john@example.com")).thenReturn(false);
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        UserResponse result = userService.create(request);

        assertThat(result.name()).isEqualTo("John");
        verify(emailService).sendWelcomeEmail("john@example.com");
    }

    @Test
    @DisplayName("Should throw on duplicate email")
    void shouldThrowOnDuplicateEmail() {
        var request = new CreateUserRequest("John", "existing@example.com", 30, null);
        when(userRepository.existsByEmail("existing@example.com")).thenReturn(true);

        assertThatThrownBy(() -> userService.create(request))
            .isInstanceOf(DuplicateResourceException.class);
    }
}
```

---

## Best Practices

1. **Use records for DTOs** — immutable, concise, auto-generated methods
2. **Virtual threads for I/O** — `Executors.newVirtualThreadPerTaskExecutor()` for HTTP, DB, file I/O
3. **Constructor injection only** — never field injection (`@Autowired` on fields)
4. **Sealed hierarchies for domain models** — use `sealed interface` + `permits` for exhaustive matching
5. **ProblemDetail for errors** — RFC 7807 built into Spring 6+
6. **Never catch `Exception`** — catch specific exceptions; use `@ControllerAdvice`
7. **Immutable collections** — use `List.of()`, `Map.of()`, `.toList()`
8. **Log at boundaries** — log at service entry/exit; use MDC for request correlation
9. **Profile-based config** — `application-{profile}.yml`; never hardcode secrets
10. **Test pyramid** — many unit tests (Mockito), fewer integration (Testcontainers)
11. **Prefer `Optional` return types** — from repository methods
12. **Use switch expressions** — for enums, finite states, sealed types

---

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---------|-------------|-----|
| `synchronized` with VT (JDK 21–23) | Pins VT to carrier thread | JDK 21–23: use `ReentrantLock`. JDK 24+: `synchronized` is safe |
| `Optional.get()` without `isPresent()` | `NoSuchElementException` | `orElseThrow()`, `orElseGet()`, `ifPresent()` |
| Field injection (`@Autowired`) | Untestable, hides dependencies | Constructor injection |
| Parallel streams for I/O | Blocks ForkJoinPool common pool | Virtual threads or `CompletableFuture` |
| N+1 queries in JPA | One query per entity in a loop | `@EntityGraph`, JPQL `JOIN FETCH`, `@BatchSize` |
| `equals()` on JPA entities | Generated IDs are null before persist | Use business key or `@NaturalId` |
| Catching `Exception` broadly | Hides bugs | Catch specific exceptions |
| Mutable `@ConfigurationProperties` | Thread safety issues | Bind immutable records |
| Not using `@Transactional` boundaries | Lazy loading fails outside session | Apply at service method level |
| Logging with string concatenation | Always evaluated even if DEBUG is off | `log.debug("User {}", user)` — parameterized |

---

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for deep dives, edge cases, and advanced techniques
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates

---

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| Spring Boot | `/spring-projects/spring-boot` | Auto-configuration, starters, properties |
| Spring Framework | (query "Spring Framework") | DI, AOP, transaction management |
| JUnit 5 | (query "JUnit 5") | Test annotations, extensions |
| Gradle | (query "Gradle") | Build configuration, multi-module |
| Hibernate | `/hibernate/hibernate-orm` | JPA patterns, fetching strategies |

## See also

- [`secure-coding-patterns`](../secure-coding-patterns/SKILL.md) — Spring Security, authentication, authorization, JWT
- [`database-patterns`](../database-patterns/SKILL.md) — JPA/Hibernate, connection pooling, transaction management
- [`testing-patterns`](../testing-patterns/SKILL.md) — JUnit 5/6, Testcontainers, integration testing
- [`api-design-principles`](../api-design-principles/SKILL.md) — REST controller patterns, error handling, pagination
