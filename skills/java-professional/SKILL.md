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
- **Garbage Collection** — G1 is the default collector (JDK 21 and 25 LTS); ZGC is opt-in via `-XX:+UseZGC` for low-latency workloads (generational mode is the default since JDK 23 and the only mode since JDK 24); understand GC pauses and allocation rates
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
    // Compact canonical constructor with validation
    public UserDTO {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("Name must not be blank");
        }
        if (age < 0 || age > 150) {
            throw new IllegalArgumentException("Age must be between 0 and 150");
        }
    }

    // Derived property
    public String displayName() {
        return name + " <" + email + ">";
    }
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
        case Circle c when c.radius() > 100  -> "Large circle (r=" + c.radius() + ")";
        case Circle c                         -> "Circle (r=" + c.radius() + ")";
        case Rectangle r                      -> "Rectangle " + r.width() + "x" + r.height();
        case Triangle t                       -> "Triangle (base=" + t.base() + ")";
        // No default needed — sealed interface is exhaustive
    };
}

// instanceof pattern matching (Java 16+)
public void process(Object obj) {
    if (obj instanceof String s && !s.isBlank()) {
        System.out.println("Non-blank string: " + s.toUpperCase());
    } else if (obj instanceof Integer i && i > 0) {
        System.out.println("Positive integer: " + i);
    }
}
```

### 2. Virtual Threads

```java
// Virtual threads — lightweight threads for I/O-bound work
// Java 21+ (Project Loom)

// Single virtual thread
Thread.startVirtualThread(() -> {
    System.out.println("Running on virtual thread: " + Thread.currentThread());
});

// Virtual thread executor — preferred approach
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    IntStream.range(0, 10_000).forEach(i -> {
        executor.submit(() -> {
            Thread.sleep(Duration.ofSeconds(1)); // blocking is cheap on VT
            return fetchFromApi(i);
        });
    });
} // auto-closes: waits for all tasks to complete

// Structured concurrency — Java 25 (JEP 505, fifth preview; STILL a preview feature)
// Requires: --enable-preview (javac --release 25 --enable-preview)
// import java.util.concurrent.StructuredTaskScope;
record UserWithOrders(User user, List<Order> orders) {}

UserWithOrders fetchUserWithOrders(long userId) throws Exception {
    // open() uses the default join policy: fail if any subtask fails
    try (var scope = StructuredTaskScope.open()) {
        var userTask = scope.fork(() -> userService.getById(userId));
        var ordersTask = scope.fork(() -> orderService.getByUserId(userId));

        scope.join(); // waits for both tasks; throws FailedException if any failed

        return new UserWithOrders(userTask.get(), ordersTask.get());
    }
}
// Other policies: StructuredTaskScope.open(StructuredTaskScope.Joiner.awaitAll()),
// Joiner.awaitAllSuccessfulOrThrow(), Joiner.anySuccessfulResultOrThrow(),
// Joiner.allSuccessfulOrThrow(), Joiner.allUntil(predicate) — join() then returns
// the joiner's result instead of null.
// Note: the JDK 21–24 previews used `new StructuredTaskScope.ShutdownOnFailure()`
// + `scope.join().throwIfFailed()`; that API was replaced in Java 25 (JEP 505).

// synchronized + virtual threads — pinning rules depend on the JDK version
// JDK 21–23: synchronized blocks pin the virtual thread to its carrier thread
// JDK 24+:   pinning eliminated (JEP 491) — virtual threads unmount inside synchronized

// JDK 21–23 only: prefer ReentrantLock around blocking calls
private final ReentrantLock lock = new ReentrantLock();

lock.lock();
try {
    httpClient.send(request, BodyHandlers.ofString()); // unmounts safely on 21–23
} finally {
    lock.unlock();
}

// JDK 24+: synchronized is fine again — no carrier pinning
private final Object monitor = new Object();

synchronized (monitor) {
    httpClient.send(request, BodyHandlers.ofString()); // virtual thread unmounts (JEP 491)
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

    // Constructor injection — no @Autowired needed
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
    @Operation(summary = "Get user by ID")
    public UserResponse getUser(@PathVariable Long id) {
        return userService.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("User", id));
    }

    @PostMapping
    @Operation(summary = "Create new user")
    @ResponseStatus(HttpStatus.CREATED)
    public UserResponse createUser(@Valid @RequestBody CreateUserRequest request) {
        return userService.create(request);
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update user")
    public UserResponse updateUser(
            @PathVariable Long id,
            @Valid @RequestBody UpdateUserRequest request) {
        return userService.update(id, request);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete user")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteUser(@PathVariable Long id) {
        userService.delete(id);
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
// Entity
@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
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

    @PrePersist
    void onCreate() { this.createdAt = Instant.now(); }
}

// Repository with query methods
public interface UserRepository extends JpaRepository<User, Long>,
                                         JpaSpecificationExecutor<User> {

    Optional<User> findByEmail(String email);

    boolean existsByEmail(String email);

    @Query("SELECT u FROM User u WHERE u.role = :role AND u.createdAt > :since")
    List<User> findActiveByRole(@Param("role") Role role, @Param("since") Instant since);

    // Use CONCAT to safely build the LIKE pattern — avoids invalid SQL from "LIKE %:domain"
    @Query(value = "SELECT * FROM users WHERE email LIKE CONCAT('%', :domain, '%')", nativeQuery = true)
    List<User> findByEmailDomain(@Param("domain") String domain);

    // Paginated query
    Page<User> findByRole(Role role, Pageable pageable);
}

// Specification for dynamic queries
public class UserSpecifications {
    public static Specification<User> hasName(String name) {
        return (root, query, cb) ->
            name == null ? null : cb.like(cb.lower(root.get("name")), "%" + name.toLowerCase() + "%");
    }

    public static Specification<User> hasRole(Role role) {
        return (root, query, cb) ->
            role == null ? null : cb.equal(root.get("role"), role);
    }

    public static Specification<User> createdAfter(Instant since) {
        return (root, query, cb) ->
            since == null ? null : cb.greaterThanOrEqualTo(root.get("createdAt"), since);
    }
}

// Usage — combine specifications
var spec = Specification.where(UserSpecifications.hasName(search))
        .and(UserSpecifications.hasRole(role))
        .and(UserSpecifications.createdAfter(since));

Page<User> users = userRepository.findAll(spec, PageRequest.of(0, 20, Sort.by("createdAt").descending()));
```

### 5. Spring Security (JWT + OAuth2)

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
            .csrf(AbstractHttpConfigurer::disable) // stateless API
            // WARNING: Only disable CSRF for stateless APIs (JWT/token-based).
            // For session-based auth, keep CSRF enabled to prevent cross-site attacks.
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            // ONE JWT mechanism only: oauth2ResourceServer decodes and validates tokens.
            // Don't also addFilterBefore() a custom JWT filter — that authenticates twice.
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

// JWT token provider
@Component
public class JwtTokenProvider {
    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expiration-ms:3600000}")
    private long expirationMs;

    public String generateToken(UserDetails user) {
        return Jwts.builder()
            .subject(user.getUsername())
            .claim("roles", user.getAuthorities().stream()
                .map(a -> a.getAuthority().replace("ROLE_", ""))
                .toList())
            .issuedAt(new Date())
            .expiration(new Date(System.currentTimeMillis() + expirationMs))
            .signWith(getSigningKey())
            .compact();
    }

    private SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(Decoders.BASE64.decode(secret));
    }
}

// Method-level security
@Service
public class OrderService {
    @PreAuthorize("hasRole('ADMIN') or #userId == authentication.principal.id")
    public List<Order> getOrdersForUser(Long userId) { ... }

    // Admins may fetch ANY order; users only their own — checked AFTER execution.
    // Don't add a restrictive @PreAuthorize("hasRole('ADMIN')") here: it would let
    // only admins in, then the @PostAuthorize owner check would fail them anyway.
    @PostAuthorize("hasRole('ADMIN') or returnObject.owner == authentication.principal.username")
    public Order getOrder(Long orderId) { ... }
}
```

### 6. Dependency Injection Patterns

```java
// ✅ Constructor injection — preferred (immutable, testable)
@Service
public class UserService {
    private final UserRepository userRepository;
    private final EmailService emailService;
    private final CacheManager cacheManager;

    public UserService(UserRepository userRepository,
                       EmailService emailService,
                       CacheManager cacheManager) {
        this.userRepository = userRepository;
        this.emailService = emailService;
        this.cacheManager = cacheManager;
    }
}

// @Qualifier — when multiple implementations exist
@Configuration
public class StorageConfig {
    @Bean
    @Qualifier("s3")
    public StorageService s3StorageService() { return new S3StorageService(); }

    @Bean
    @Qualifier("local")
    public StorageService localStorageService() { return new LocalStorageService(); }
}

@Service
public class DocumentService {
    private final StorageService storage;

    public DocumentService(@Qualifier("s3") StorageService storage) {
        this.storage = storage;
    }
}

// Profiles — environment-specific configuration
@Profile("production")
@Service
public class ProductionEmailService implements EmailService { /* SMTP */ }

@Profile({"dev", "test"})
@Service
public class StubEmailService implements EmailService { /* logs only */ }

// application.yml
// spring:
//   profiles:
//     active: ${SPRING_PROFILES_ACTIVE:dev}
```

### 7. Exception Handling

```java
// Custom exception hierarchy
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

public class DuplicateResourceException extends BusinessException {
    public DuplicateResourceException(String entity, String field, Object value) {
        super("DUPLICATE_RESOURCE", entity + " with " + field + "=" + value + " already exists");
    }
}

public class ValidationException extends BusinessException {
    private final Map<String, List<String>> fieldErrors;

    public ValidationException(Map<String, List<String>> fieldErrors) {
        super("VALIDATION_ERROR", "Validation failed");
        this.fieldErrors = fieldErrors;
    }

    public Map<String, List<String>> getFieldErrors() { return fieldErrors; }
}

// Global exception handler — RFC 7807 ProblemDetail
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ProblemDetail> handleNotFound(ResourceNotFoundException ex) {
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        detail.setTitle("Resource Not Found");
        detail.setProperty("errorCode", ex.getErrorCode());
        detail.setProperty("timestamp", Instant.now());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(detail);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ProblemDetail> handleValidation(MethodArgumentNotValidException ex) {
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_ENTITY, "Validation failed");
        detail.setTitle("Validation Error");

        Map<String, List<String>> errors = ex.getBindingResult().getFieldErrors().stream()
            .collect(Collectors.groupingBy(
                FieldError::getField,
                Collectors.mapping(FieldError::getDefaultMessage, Collectors.toList())
            ));
        detail.setProperty("fieldErrors", errors);
        return ResponseEntity.unprocessableEntity().body(detail);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ProblemDetail> handleGeneric(Exception ex) {
        log.error("Unexpected error", ex);
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred");
        detail.setTitle("Internal Server Error");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(detail);
    }
}
```

### 8. Testing (JUnit 5/6 + Mockito + Testcontainers)

```java
// Unit test with Mockito
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock UserRepository userRepository;
    @Mock EmailService emailService;
    @InjectMocks UserService userService;

    @Test
    @DisplayName("Should create user with valid data")
    void shouldCreateUser() {
        // given
        var request = new CreateUserRequest("John", "john@example.com", 30, null);
        when(userRepository.existsByEmail("john@example.com")).thenReturn(false);
        // The entity has no setId() — JPA assigns the generated id on persist,
        // so the mock simply returns the argument unchanged
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        // when
        UserResponse result = userService.create(request);

        // then
        assertThat(result.name()).isEqualTo("John");
        assertThat(result.email()).isEqualTo("john@example.com");
        verify(emailService).sendWelcomeEmail("john@example.com");
    }

    @Test
    @DisplayName("Should throw on duplicate email")
    void shouldThrowOnDuplicateEmail() {
        var request = new CreateUserRequest("John", "existing@example.com", 30, null);
        when(userRepository.existsByEmail("existing@example.com")).thenReturn(true);

        assertThatThrownBy(() -> userService.create(request))
            .isInstanceOf(DuplicateResourceException.class)
            .hasMessageContaining("existing@example.com");
    }

    @ParameterizedTest
    @ValueSource(strings = {"", "  ", "invalid-email", "no-at-sign"})
    @DisplayName("Should reject invalid emails")
    void shouldRejectInvalidEmails(String email) {
        var request = new CreateUserRequest("John", email, 30, null);
        assertThatThrownBy(() -> userService.create(request))
            .isInstanceOf(ValidationException.class);
    }
}

// Integration test with Testcontainers
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
class UserControllerIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:17")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired TestRestTemplate restTemplate;
    @Autowired UserRepository userRepository;

    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
    }

    @Test
    @DisplayName("POST /api/v1/users — should create and return 201")
    void shouldCreateUser() {
        var request = new CreateUserRequest("Jane", "jane@test.com", 25, "Bio");

        var response = restTemplate.postForEntity("/api/v1/users", request, UserResponse.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(response.getBody().name()).isEqualTo("Jane");
    }
}
```

### 9. Gradle Multi-Module Project

```groovy
// settings.gradle
rootProject.name = 'myapp'

include 'common'
include 'domain'
include 'infrastructure'
include 'api'
include 'app'

// build.gradle (root)
plugins {
    id 'java'
    id 'org.springframework.boot' version '4.1.1' apply false
    id 'io.spring.dependency-management' version '1.1.7' apply false
}

subprojects {
    apply plugin: 'java'

    group = 'com.example'
    version = '1.0.0'

    java {
        toolchain {
            languageVersion = JavaLanguageVersion.of(21)
        }
    }

    repositories {
        mavenCentral()
    }

    dependencies {
        compileOnly 'org.projectlombok:lombok:1.18.48'
        annotationProcessor 'org.projectlombok:lombok:1.18.48'

        // JUnit 6.x continues the JUnit 5 (Jupiter) programming model; requires Java 17+
        testImplementation 'org.junit.jupiter:junit-jupiter:6.1.3'
        testImplementation 'org.assertj:assertj-core:3.27.7'
        testImplementation 'org.mockito:mockito-core:5.23.0'
    }

    test {
        useJUnitPlatform()
    }
}

// api/build.gradle
plugins {
    id 'org.springframework.boot'
    id 'io.spring.dependency-management'
}

dependencies {
    implementation project(':domain')
    implementation project(':common')

    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-validation'
    implementation 'org.springdoc:springdoc-openapi-starter-webmvc-ui:3.1.1' // springdoc 3.x = Spring Boot 4
}

// app/build.gradle — the bootable module
plugins {
    id 'org.springframework.boot'
    id 'io.spring.dependency-management'
}

dependencies {
    implementation project(':api')
    implementation project(':infrastructure')
    implementation project(':domain')
    implementation project(':common')

    implementation 'org.springframework.boot:spring-boot-starter'
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
}

// Dependency direction: app → api → domain → common
// Infrastructure implements domain interfaces (hexagonal)
```

### 10. Streams API

```java
// Collectors — grouping, partitioning, mapping
record Order(String product, String category, BigDecimal amount, Instant date) {}

// Grouping + summing
Map<String, BigDecimal> totalByCategory = orders.stream()
    .collect(Collectors.groupingBy(
        Order::category,
        Collectors.reducing(BigDecimal.ZERO, Order::amount, BigDecimal::add)
    ));

// Partitioning — split into two groups by predicate
Map<Boolean, List<Order>> partitioned = orders.stream()
    .collect(Collectors.partitioningBy(o -> o.amount().compareTo(BigDecimal.valueOf(100)) > 0));

// toMap with merge function for duplicates
Map<String, Order> latestByProduct = orders.stream()
    .collect(Collectors.toMap(
        Order::product,
        Function.identity(),
        (o1, o2) -> o1.date().isAfter(o2.date()) ? o1 : o2
    ));

// flatMap — flatten nested collections
List<String> allTags = users.stream()
    .flatMap(u -> u.getTags().stream())
    .distinct()
    .sorted()
    .toList(); // Java 16+ unmodifiable list

// Parallel streams — use only for CPU-bound work on large collections
long count = largeDataset.parallelStream()
    .filter(item -> item.isActive())
    .mapToLong(Item::computeExpensiveMetric)
    .sum();

// ⚠️ Parallel streams pitfalls:
// - Don't use for I/O-bound operations (use virtual threads instead)
// - Don't use on small collections (overhead > benefit)
// - Avoid stateful operations (forEach with shared mutable state)
// - Prefer unordered operations when order doesn't matter (forEachOrdered vs forEach)
```

### 11. Optional Best Practices

```java
// ✅ GOOD patterns
Optional<User> user = userRepository.findById(id);

// Return Optional from methods that might not find a result
public Optional<User> findUserByEmail(String email) {
    return userRepository.findByEmail(email);
}

// orElseGet for expensive defaults (lazy evaluation)
User user = findUserByEmail(email)
    .orElseGet(() -> createDefaultUser(email));

// orElseThrow for required values
User user = findUserByEmail(email)
    .orElseThrow(() -> new ResourceNotFoundException("User", email));

// ifPresentOrElse (Java 9+)
findUserByEmail(email).ifPresentOrElse(
    user -> log.info("Found user: {}", user.name()),
    () -> log.warn("User not found: {}", email)
);

// map + flatMap chaining
String city = findUserByEmail(email)
    .map(User::getAddress)
    .map(Address::getCity)
    .orElse("Unknown");

// stream() from Optional — useful in flatMap chains
List<String> emails = userIds.stream()
    .map(userRepository::findById)
    .flatMap(Optional::stream)   // skips empty optionals
    .map(User::getEmail)
    .toList();

// ❌ BAD patterns — never do these
Optional<User> user = findUserByEmail(email);
user.get();                           // NoSuchElementException risk
if (user.isPresent()) { ... }         // defeats the purpose of Optional
Optional<User> empty = Optional.of(null); // NullPointerException
Optional<User> opt = Optional.ofNullable(getUser()); // use orElse, not null check
```

### 12. Logging (SLF4J + Logback)

```java
// ✅ Use SLF4J facade, not implementation directly
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;

@Service
public class OrderService {
    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    public Order createOrder(CreateOrderRequest request) {
        log.info("Creating order: userId={}, items={}", request.userId(), request.items().size());

        try {
            Order order = processOrder(request);
            log.info("Order created: orderId={}, total={}", order.getId(), order.getTotal());
            return order;
        } catch (PaymentException ex) {
            log.error("Payment failed for user={}: {}", request.userId(), ex.getMessage(), ex);
            throw ex;
        }
    }
}

// MDC — Mapped Diagnostic Context (request correlation)
@Component
public class RequestLoggingFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String requestId = req.getHeader("X-Request-Id");
        if (requestId == null) requestId = UUID.randomUUID().toString();

        MDC.put("requestId", requestId);
        MDC.put("method", req.getMethod());
        MDC.put("path", req.getRequestURI());

        long start = System.nanoTime();
        try {
            chain.doFilter(req, res);
        } finally {
            long durationMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start);
            log.info("Request completed: status={}, duration={}ms", res.getStatus(), durationMs);
            MDC.clear();
        }
    }
}

// logback-spring.xml — structured JSON output for production
// <configuration>
//   <springProfile name="production">
//     <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
//       <encoder class="net.logstash.logback.encoder.LogstashEncoder">
//         <includeMdcKeyName>requestId</includeMdcKeyName>
//       </encoder>
//     </appender>
//     <root level="INFO"><appender-ref ref="JSON"/></root>
//   </springProfile>
//   <springProfile name="dev">
//     <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
//       <encoder><pattern>%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} — %msg%n</pattern></encoder>
//     </appender>
//     <root level="DEBUG"><appender-ref ref="CONSOLE"/></root>
//   </springProfile>
// </configuration>
```

## Best Practices

1. **Use records for DTOs** — immutable, concise, auto-generated methods; use classes for entities with mutable state
2. **Virtual threads for I/O** — `Executors.newVirtualThreadPerTaskExecutor()` for HTTP calls, DB queries, file I/O; use platform threads for CPU-bound work
3. **Constructor injection only** — never field injection (`@Autowired` on fields); constructor injection makes dependencies explicit and testable
4. **Sealed hierarchies for domain models** — use `sealed interface` + `permits` to model finite state machines, ensure exhaustive pattern matching
5. **ProblemDetail for errors** — use RFC 7807 `ProblemDetail` (built into Spring 6+) instead of custom error response classes
6. **Never catch `Exception`** — catch specific exceptions; use `@ControllerAdvice` for global handling; let unexpected exceptions propagate
7. **Immutable collections** — use `List.of()`, `Map.of()`, `.toList()` for unmodifiable collections; avoid returning mutable internal state
8. **Log at boundaries** — log at service entry/exit, not inside every method; use MDC for request correlation; structured JSON in production
9. **Profile-based config** — `application-{profile}.yml` for environment-specific settings; never hardcode secrets; use `${ENV_VAR:default}`
10. **Test pyramid** — many unit tests (Mockito), fewer integration tests (Testcontainers), minimal E2E tests; `@SpringBootTest` only for integration
11. **Prefer `Optional` return types** — from repository methods; never return `Optional` as a parameter or field
12. **Use switch expressions** — for mapping enums, finite states, sealed types; prefer over if-else chains when matching against patterns

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---------|-------------|-----|
| `synchronized` with virtual threads (JDK 21–23) | Pins virtual thread to carrier thread on JDK 21–23, defeating the purpose; pinning eliminated in JDK 24 (JEP 491) | JDK 21–23: use `ReentrantLock`. JDK 24+: `synchronized` is safe |
| `Optional.get()` without `isPresent()` | `NoSuchElementException` at runtime | `orElseThrow()`, `orElseGet()`, `ifPresent()` |
| Field injection (`@Autowired`) | Untestable, hides dependencies, mutable | Constructor injection |
| Parallel streams for I/O | Blocks ForkJoinPool common pool | Virtual threads or `CompletableFuture` with custom executor |
| N+1 queries in JPA | One query per entity in a loop | `@EntityGraph`, JPQL `JOIN FETCH`, or batch loading via `@Fetch(FetchMode.SELECT)` + `@BatchSize` (`FetchMode.SUBSELECT` is discouraged in Hibernate 6 in favor of batch/select loading; it is NOT annotated `@Deprecated` — "discouraged" rather than formally deprecated; `selectinload` is SQLAlchemy, not JPA) |
| `equals()` on JPA entities | Generated IDs are null before persist; breaks `hashCode` contract | Use business key or `@NaturalId` for equality |
| Catching `Exception` broadly | Hides bugs, makes debugging impossible | Catch specific exceptions; let unexpected ones propagate |
| Mutable `@ConfigurationProperties` | Thread safety issues, accidental mutation | Bind immutable records — constructor binding is implicit since Spring Boot 3.0; `@ConstructorBinding` is only needed to disambiguate multiple constructors |
| Not using `@Transactional` boundaries | Lazy loading fails outside session; partial updates | Apply `@Transactional` at service method level |
| Logging with string concatenation | `log.debug("User " + user)` — always evaluated even if DEBUG is off | `log.debug("User {}", user)` — parameterized logging |

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| Spring Boot | `/spring-projects/spring-boot` | Auto-configuration, starters, properties |
| Spring Framework | (query "Spring Framework") | DI, AOP, transaction management |
| JUnit 5 | (query "JUnit 5") | Test annotations, extensions |
| Gradle | (query "Gradle") | Build configuration, multi-module |
| Hibernate | `/hibernate/hibernate-orm` | JPA patterns, fetching strategies |
