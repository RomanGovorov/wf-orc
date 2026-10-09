# Code Examples: Java Professional

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Complete Spring Boot Integration Test with Testcontainers

```java
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

    @Test
    @DisplayName("GET /api/v1/users/{id} — should return 404 for non-existent user")
    void shouldReturn404ForNonExistentUser() {
        var response = restTemplate.getForEntity("/api/v1/users/999", UserResponse.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }
}
```

---

## Example 2: Parameterized Test

```java
@ExtendWith(MockitoExtension.class)
class UserServiceValidationTest {
    @Mock UserRepository userRepository;
    @Mock EmailService emailService;
    @InjectMocks UserService userService;

    @ParameterizedTest
    @ValueSource(strings = {"", "  ", "invalid-email", "no-at-sign"})
    @DisplayName("Should reject invalid emails")
    void shouldRejectInvalidEmails(String email) {
        var request = new CreateUserRequest("John", email, 30, null);

        assertThatThrownBy(() -> userService.create(request))
            .isInstanceOf(ValidationException.class);
    }

    @ParameterizedTest
    @ValueSource(ints = {-1, 151, 200})
    @DisplayName("Should reject invalid ages")
    void shouldRejectInvalidAges(int age) {
        var request = new CreateUserRequest("John", "john@test.com", age, null);

        assertThatThrownBy(() -> userService.create(request))
            .isInstanceOf(ValidationException.class);
    }
}
```

---

## Example 3: JWT Token Provider

```java
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

    public String extractUsername(String token) {
        return parseClaims(token).getSubject();
    }

    public boolean validateToken(String token, UserDetails user) {
        final String username = extractUsername(token);
        return username.equals(user.getUsername()) && !isTokenExpired(token);
    }

    private boolean isTokenExpired(String token) {
        return parseClaims(token).getExpiration().before(new Date());
    }

    private Claims parseClaims(String token) {
        return Jwts.parser()
            .verifyWith(getSigningKey())
            .build()
            .parseSignedClaims(token)
            .getPayload();
    }

    private SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(Decoders.BASE64.decode(secret));
    }
}
```

---

## Example 4: Complete Exception Hierarchy

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

    @ExceptionHandler(DuplicateResourceException.class)
    public ResponseEntity<ProblemDetail> handleDuplicate(DuplicateResourceException ex) {
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
        detail.setTitle("Duplicate Resource");
        detail.setProperty("errorCode", ex.getErrorCode());
        return ResponseEntity.status(HttpStatus.CONFLICT).body(detail);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ProblemDetail> handleGeneric(Exception ex) {
        log.error("Unexpected error", ex);
        var detail = ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR,
            "An unexpected error occurred");
        detail.setTitle("Internal Server Error");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(detail);
    }
}
```

---

## Example 5: Entity with Relationships

```java
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

    // Getters, equals, hashCode — use business key (email), not generated id
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        User user = (User) o;
        return email != null && email.equals(user.email);
    }

    @Override
    public int hashCode() {
        return Objects.hash(email);
    }
}
```

---

## Example 6: Repository with Custom Query Methods

```java
public interface UserRepository extends JpaRepository<User, Long>,
                                         JpaSpecificationExecutor<User> {

    Optional<User> findByEmail(String email);

    boolean existsByEmail(String email);

    @Query("SELECT u FROM User u WHERE u.role = :role AND u.createdAt > :since")
    List<User> findActiveByRole(@Param("role") Role role, @Param("since") Instant since);

    // Use CONCAT to safely build the LIKE pattern
    @Query(value = "SELECT * FROM users WHERE email LIKE CONCAT('%', :domain, '%')", nativeQuery = true)
    List<User> findByEmailDomain(@Param("domain") String domain);

    // Paginated query
    Page<User> findByRole(Role role, Pageable pageable);

    // Delete with return count
    @Modifying
    @Query("DELETE FROM User u WHERE u.isActive = false AND u.createdAt < :before")
    int deleteInactiveUsersBefore(@Param("before") Instant before);
}
```

---

## Example 7: application.yml Configuration

```yaml
spring:
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:dev}

  datasource:
    url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:myapp}
    username: ${DB_USER:postgres}
    password: ${DB_PASSWORD:postgres}
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
      idle-timeout: 600000

  jpa:
    hibernate:
      ddl-auto: validate
    properties:
      hibernate:
        format_sql: true
        jdbc:
          batch_size: 50
        order_inserts: true
        order_updates: true

jwt:
  secret: ${JWT_SECRET:your-256-bit-secret}
  expiration-ms: ${JWT_EXPIRATION_MS:3600000}

logging:
  level:
    root: INFO
    com.example: DEBUG
    org.hibernate.SQL: DEBUG
```

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Advanced techniques:** See [`advanced.md`](advanced.md) for deep dives and edge cases
