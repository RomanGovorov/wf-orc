# Advanced Patterns: Java Professional

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Structured Concurrency (Java 25 Preview)

```java
// Structured concurrency — Java 25 (JEP 505, fifth preview; STILL a preview feature)
// Requires: --enable-preview (javac --release 25 --enable-preview)
// import java.util.concurrent.StructuredTaskScope;
record UserWithOrders(User user, List<Order> orders) {}

UserWithOrders fetchUserWithOrders(long userId) throws Exception {
    try (var scope = StructuredTaskScope.open()) {
        var userTask = scope.fork(() -> userService.getById(userId));
        var ordersTask = scope.fork(() -> orderService.getByUserId(userId));

        scope.join(); // waits for both; throws FailedException if any failed

        return new UserWithOrders(userTask.get(), ordersTask.get());
    }
}
// Other policies: StructuredTaskScope.open(StructuredTaskScope.Joiner.awaitAll()),
// Joiner.awaitAllSuccessfulOrThrow(), Joiner.anySuccessfulResultOrThrow(),
// Joiner.allSuccessfulOrThrow(), Joiner.allUntil(predicate)
// Note: JDK 21–24 previews used `new StructuredTaskScope.ShutdownOnFailure()`
// + `scope.join().throwIfFailed()`; that API was replaced in Java 25 (JEP 505).
```

---

## Dependency Injection Patterns

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
```

---

## Spring Data JPA — Specifications for Dynamic Queries

```java
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

---

## Method-Level Security

```java
@Service
public class OrderService {
    @PreAuthorize("hasRole('ADMIN') or #userId == authentication.principal.id")
    public List<Order> getOrdersForUser(Long userId) { ... }

    // Admins may fetch ANY order; users only their own — checked AFTER execution.
    @PostAuthorize("hasRole('ADMIN') or returnObject.owner == authentication.principal.username")
    public Order getOrder(Long orderId) { ... }
}
```

---

## Streams API — Advanced Collectors

```java
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
    .toList();

// Parallel streams — use only for CPU-bound work on large collections
long count = largeDataset.parallelStream()
    .filter(item -> item.isActive())
    .mapToLong(Item::computeExpensiveMetric)
    .sum();

// ⚠️ Parallel streams pitfalls:
// - Don't use for I/O-bound operations (use virtual threads instead)
// - Don't use on small collections (overhead > benefit)
// - Avoid stateful operations (forEach with shared mutable state)
// - Prefer unordered operations when order doesn't matter
```

---

## Optional Best Practices

```java
// ✅ GOOD patterns
Optional<User> user = userRepository.findById(id);

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
    .flatMap(Optional::stream)
    .map(User::getEmail)
    .toList();

// ❌ BAD patterns — never do these
Optional<User> user = findUserByEmail(email);
user.get();                           // NoSuchElementException risk
if (user.isPresent()) { ... }         // defeats the purpose of Optional
Optional<User> empty = Optional.of(null); // NullPointerException
```

---

## Logging (SLF4J + Logback)

```java
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
```

---

## Gradle Multi-Module Project

```groovy
// settings.gradle
rootProject.name = 'myapp'
include 'common', 'domain', 'infrastructure', 'api', 'app'

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
        toolchain { languageVersion = JavaLanguageVersion.of(21) }
    }
    repositories { mavenCentral() }
    dependencies {
        compileOnly 'org.projectlombok:lombok:1.18.48'
        annotationProcessor 'org.projectlombok:lombok:1.18.48'
        testImplementation 'org.junit.jupiter:junit-jupiter:6.1.3'
        testImplementation 'org.assertj:assertj-core:3.27.7'
        testImplementation 'org.mockito:mockito-core:5.23.0'
    }
    test { useJUnitPlatform() }
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
    implementation 'org.springdoc:springdoc-openapi-starter-webmvc-ui:3.1.1'
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
```

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
