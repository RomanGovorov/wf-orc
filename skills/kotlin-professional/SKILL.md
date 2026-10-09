---
name: kotlin-professional
description: Professional Kotlin 2.x — coroutines, Flow, Ktor, Compose Multiplatform, KSP, kotlinx.serialization, Arrow. Use when writing, reviewing, or refactoring Kotlin code.
priority: 10
paths:
  - "**/src/**/*.kt"
  - "**/commonMain/**/*.kt"
  - "**/androidMain/**/*.kt"
  - "**/iosMain/**/*.kt"
  - "**/test/**/*.kt"
  - "**/build.gradle.kts"
  - "**/settings.gradle.kts"
  - "**/gradlew*"
  - "**/ktor*"
  - "**/compose*"
  - "**/iosApp/**"
  - "**/androidApp/**"
  - "**/shared/**"
---

# Kotlin Professional

Complete guide to professional Kotlin 2.x development — coroutines, Flow, Ktor, Compose Multiplatform, functional patterns, and production-ready code.

## When to Use This Skill

- When writing new Kotlin code
- When reviewing or refactoring Kotlin code
- When building Ktor server or client applications
- When working with coroutines and Flow
- When building Compose Multiplatform UI
- When using kotlinx.serialization
- When applying functional patterns with Arrow
- When writing Kotlin tests (kotest, MockK)
- When setting up KSP annotation processing

## Core Concepts

- **Null Safety** — the type system distinguishes nullable (`String?`) from non-null (`String`); eliminates NullPointerExceptions at compile time
- **Coroutines** — lightweight, structured concurrency via `suspend` functions; cooperative cancellation; no thread blocking
- **Extension Functions** — add methods to existing types without inheritance; `fun String.isValidEmail(): Boolean`
- **DSL Builders** — type-safe builders using lambdas with receivers; used extensively in Ktor, Compose, Gradle Kotlin DSL
- **Data Classes** — auto-generated `equals()`, `hashCode()`, `copy()`, `toString()`, component functions for destructuring
- **Sealed Classes/Interfaces** — restricted hierarchies; enable exhaustive `when` expressions without `else` branch
- **Scope Functions** — `let`, `apply`, `run`, `also`, `with` — each has specific use cases and return values

## Patterns

### 1. Coroutines

```kotlin
// Suspend functions — the foundation
suspend fun fetchUser(id: Long): User {
    return httpClient.get("/api/users/$id").body()
}

// CoroutineScope — structured concurrency
class UserStateService(private val scope: CoroutineScope) {
    private val _state = MutableStateFlow<UserState>(UserState.Idle)
    val state = _state.asStateFlow()

    fun loadUser(id: Long) {
        scope.launch {
            try {
                _state.value = UserState.Loading
                val user = fetchUser(id)
                _state.value = UserState.Loaded(user)
            } catch (e: CancellationException) {
                throw e // always rethrow CancellationException
            } catch (e: Exception) {
                _state.value = UserState.Error(e.message ?: "Unknown error")
            }
        }
    }
}

// Dispatchers — choose the right context
suspend fun loadData() = coroutineScope {
    val ioResult = async(Dispatchers.IO) { database.queryUsers() }
    val cpuResult = async(Dispatchers.Default) { heavyComputation() }
    Pair(ioResult.await(), cpuResult.await())
}

// withContext — switch dispatcher safely
suspend fun readFile(path: String): String = withContext(Dispatchers.IO) {
    File(path).readText()
}
```

### 2. Flow

```kotlin
// StateFlow — hot, always has a current value (like LiveData)
class UserViewModel(private val repository: UserRepository) : ViewModel() {
    private val _state = MutableStateFlow<UserState>(UserState.Idle)
    val state: StateFlow<UserState> = _state.asStateFlow()

    fun loadUser(id: Long) {
        viewModelScope.launch {
            _state.value = UserState.Loading
            try {
                val user = repository.findById(id) ?: error("User not found: $id")
                _state.value = UserState.Loaded(user)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _state.value = UserState.Error(e.message ?: "Unknown error")
            }
        }
    }
}

// Flow operators — transformation pipeline
fun searchUsers(query: Flow<String>): Flow<List<User>> = query
    .debounce(300)
    .distinctUntilChanged()
    .filter { it.length >= 2 }
    .flatMapLatest { searchTerm ->
        repository.searchUsers(searchTerm)
            .catch { emit(emptyList()) }
    }
```

### 3. Sealed Classes + Exhaustive When

```kotlin
sealed interface ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>
    data class Error(val code: Int, val message: String) : ApiResult<Nothing>
    data object Loading : ApiResult<Nothing>
}

fun <T> handleResult(result: ApiResult<T>): String = when (result) {
    is ApiResult.Success -> "Data: ${result.data}"
    is ApiResult.Error -> "Error ${result.code}: ${result.message}"
    is ApiResult.Loading -> "Loading..."
    // No else needed — compiler knows all subtypes
}
```

### 4. Data Classes + copy() + Destructuring

```kotlin
data class User(
    val id: Long = 0,
    val name: String,
    val email: String,
    val role: Role = Role.USER,
    val isActive: Boolean = true,
    val createdAt: Instant = Instant.now()
)

// copy() — create modified copies without mutation
val user = User(id = 1, name = "Alice", email = "alice@example.com")
val updatedUser = user.copy(name = "Alice Smith")

// Destructuring declarations
val (id, name, email) = user

// Data class with validation in init block
data class Email(val value: String) {
    init {
        require(value.contains("@") && value.contains(".")) {
            "Invalid email format: $value"
        }
    }
}
```

### 5. Extension Functions + DSL Builders

```kotlin
// Extension functions
fun String.isValidEmail(): Boolean =
    matches(Regex("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$"))

fun String.toSlug(): String =
    lowercase().replace(Regex("[^a-z0-9]+"), "-").trim('-')

// Type-safe builder DSL
@DslMarker
annotation class HtmlDsl

@HtmlDsl
class HTML {
    private val children = mutableListOf<Tag>()
    fun head(block: Head.() -> Unit) { children.add(Head().apply(block)) }
    fun body(block: Body.() -> Unit) { children.add(Body().apply(block)) }
    fun render(): String = children.joinToString("\n") { it.render() }
}

@HtmlDsl
class Body : Tag {
    private val elements = mutableListOf<String>()
    fun h1(text: String) { elements.add("<h1>$text</h1>") }
    fun p(text: String) { elements.add("<p>$text</p>") }
    override fun render(): String = "<body>\n${elements.joinToString("\n")}\n</body>"
}

@HtmlDsl
class Head : Tag {
    var title: String = ""
    override fun render(): String = "<head><title>$title</title></head>"
}

fun html(block: HTML.() -> Unit): HTML = HTML().apply(block)
```

### 6. Ktor Server (Brief)

```kotlin
fun Application.configurePlugins() {
    install(ContentNegotiation) {
        json(Json {
            prettyPrint = true
            ignoreUnknownKeys = true
            encodeDefaults = true
        })
    }
    install(Authentication) {
        jwt("auth-jwt") {
            verifier(JWT.require(Algorithm.HMAC256(secret)).build())
            validate { credential -> JWTPrincipal(credential.payload) }
        }
    }
}

fun Application.configureRouting() {
    routing {
        route("/api/v1") {
            authenticate("auth-jwt") {
                get("/users") {
                    val users = userService.findAll()
                    call.respond(users)
                }
            }
        }
    }
}
```

### 7. kotlinx.serialization (Brief)

```kotlin
@Serializable
data class User(
    val id: Long,
    val name: String,
    val email: String,
    val tags: List<String> = emptyList()
)

val json = Json {
    prettyPrint = true
    ignoreUnknownKeys = true
    encodeDefaults = true
}

val userJson = json.encodeToString(User(id = 1, name = "Alice", email = "alice@test.com"))
val user = json.decodeFromString<User>(userJson)
```

---

## Best Practices

1. **Null safety is mandatory** — never use `!!`; use `?.let`, `?:`, `requireNotNull()`, or `checkNotNull()`
2. **Structured concurrency** — always use `coroutineScope { }` or a defined `CoroutineScope`; never `GlobalScope`
3. **Rethrow `CancellationException`** — always `catch (e: CancellationException) { throw e }` before generic catch
4. **Immutable data by default** — use `data class` with `val` properties; use `copy()` for modifications
5. **Sealed types for states** — model UI state, API results as `sealed interface`; enables exhaustive `when`
6. **Flow for reactive streams** — `StateFlow` for state, `SharedFlow` for events; `.flowOn(Dispatchers.IO)` for I/O
7. **Extension functions over utils** — prefer `fun String.isValidEmail()` over `StringUtils.isValidEmail(String)`
8. **DSL markers** — always annotate DSL builders with `@DslMarker` to prevent scope leaking
9. **kotlinx.serialization over Jackson** — multiplatform, compile-time safe, no reflection
10. **Test with kotest + MockK** — `coEvery`/`coVerify` for suspend functions; Turbine for Flow testing
11. **Use `Result` or `Either`** — never throw exceptions for expected business logic failures
12. **`withContext(Dispatchers.IO)`** — wrap all blocking calls; never block the coroutine dispatcher

---

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---------|-------------|-----|
| `GlobalScope.launch { }` | Unstructured — can't cancel, leaks | Use `viewModelScope` or explicit `CoroutineScope` |
| `!!` (non-null assertion) | `NullPointerException` in production | `?.let { }`, `?: default`, `requireNotNull()` |
| Swallowing `CancellationException` | Breaks cancellation propagation | Always `catch (e: CancellationException) { throw e }` first |
| Blocking calls in suspend functions | Blocks the dispatcher thread | `withContext(Dispatchers.IO) { blockingCall() }` |
| `lateinit var` for non-null types | UninitializedPropertyAccessException | Constructor injection, nullable types, or `by lazy` |
| Not using `@DslMarker` on builders | Outer receiver accessible in nested scope | Add `@DslMarker` annotation |
| `MutableStateFlow` as public property | External code can mutate state | Expose as `StateFlow` via `.asStateFlow()` |
| Mixing `callbackFlow` without `awaitClose` | Flow never completes, resource leak | Always `awaitClose { cleanup() }` |
| Using `runBlocking` in suspend code | Blocks the thread | Use `coroutineScope { }` or call suspend functions directly |
| Not handling `Either` left side | Errors silently ignored | Use `.fold()` or `.bind()` in `effect { }` |

---

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for deep dives, edge cases, and advanced techniques
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates

---

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| Kotlin | (query "Kotlin") | Language features, coroutines |
| Ktor | `/websites/ktor_io` | Server/client configuration |
| Spring Boot (Kotlin) | `/spring-projects/spring-boot` | Kotlin-specific Spring features |
| Arrow | (query "Arrow Kotlin") | Functional patterns, Either, Option |
| kotlinx.coroutines | (query "kotlinx coroutines") | Coroutine builders, channels |

## See also

- [`secure-coding-patterns`](../secure-coding-patterns/SKILL.md) — Ktor authentication, authorization, secure coding
- [`testing-patterns`](../testing-patterns/SKILL.md) — kotest, MockK, coroutine testing
- [`api-design-principles`](../api-design-principles/SKILL.md) — Ktor routing, REST patterns, error handling
