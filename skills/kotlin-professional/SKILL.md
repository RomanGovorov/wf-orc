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

// UI/service state — sealed hierarchy (also used in §2 and §10)
sealed interface UserState {
    data object Idle : UserState
    data object Loading : UserState
    data class Loaded(val user: User) : UserState
    data class Error(val message: String) : UserState
}

// CoroutineScope — structured concurrency
// NOTE: This is a *state-management* service (UI state flow), distinct
// from the domain UserService in §8 (which returns Either<DomainError, User>).
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
    val ioResult = async(Dispatchers.IO) {
        database.queryUsers() // blocking I/O
    }
    val cpuResult = async(Dispatchers.Default) {
        heavyComputation() // CPU-bound
    }
    Pair(ioResult.await(), cpuResult.await())
}

// withContext — switch dispatcher safely
suspend fun readFile(path: String): String = withContext(Dispatchers.IO) {
    File(path).readText() // blocking call, offloaded to IO pool
}

// SupervisorJob — child failure doesn't cancel siblings
val supervisorScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

supervisorScope.launch { /* task 1 — failure here won't cancel task 2 */ }
supervisorScope.launch { /* task 2 */ }

// Structured concurrency — coroutineScope waits for all children
suspend fun loadDashboard(): Dashboard = coroutineScope {
    val user = async { userService.getCurrentUser() }
    val orders = async { orderService.getRecentOrders() }
    val notifications = async { notificationService.getUnread() }

    Dashboard(
        user = user.await(),
        orders = orders.await(),
        notifications = notifications.await()
    )
}
```

### 2. Flow

```kotlin
// Cold Flow — lazy, only executes when collected
fun countDown(from: Int): Flow<Int> = flow {
    for (i in from downTo 1) {
        emit(i)
        delay(1000)
    }
}

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
                throw e // always rethrow CancellationException
            } catch (e: Exception) {
                _state.value = UserState.Error(e.message ?: "Unknown error")
            }
        }
    }
}

// SharedFlow — hot, event bus pattern (no initial value)
class EventBus {
    private val _events = MutableSharedFlow<AppEvent>(
        replay = 0,
        extraBufferCapacity = 64,
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )
    val events: SharedFlow<AppEvent> = _events.asSharedFlow()

    suspend fun emit(event: AppEvent) = _events.emit(event)
}

// Flow operators — transformation pipeline
fun searchUsers(query: Flow<String>): Flow<List<User>> = query
    .debounce(300)                    // wait for user to stop typing
    .distinctUntilChanged()            // skip duplicate queries
    .filter { it.length >= 2 }         // minimum query length
    .flatMapLatest { searchTerm ->     // cancel previous search on new input
        repository.searchUsers(searchTerm)
            .catch { emit(emptyList()) } // handle errors gracefully
    }

// Combining flows
fun combineData(
    usersFlow: Flow<List<User>>,
    filterFlow: Flow<FilterState>
): Flow<List<User>> = combine(usersFlow, filterFlow) { users, filter ->
    users.filter { it.matches(filter) }
}

// Flow lifecycle operators
fun trackableFlow(): Flow<Data> = repository.getData()
    .onStart { log.info("Flow started") }
    .onEach { log.debug("Emitted: $it") }
    .onCompletion { cause ->
        if (cause != null) log.error("Flow completed with error", cause)
        else log.info("Flow completed successfully")
    }
    .flowOn(Dispatchers.IO) // upstream runs on IO dispatcher
```

### 3. Sealed Classes + Exhaustive When

```kotlin
// Sealed interface — restricted hierarchy
sealed interface ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>
    data class Error(val code: Int, val message: String) : ApiResult<Nothing>
    data object Loading : ApiResult<Nothing>
}

// Exhaustive when — compiler enforces all branches
fun <T> handleResult(result: ApiResult<T>): String = when (result) {
    is ApiResult.Success -> "Data: ${result.data}"
    is ApiResult.Error -> "Error ${result.code}: ${result.message}"
    is ApiResult.Loading -> "Loading..."
    // No else needed — compiler knows all subtypes
}

// Sealed class for state machines
sealed class AuthState {
    data object Unauthenticated : AuthState()
    data class Authenticating(val attempt: Int) : AuthState()
    data class Authenticated(val user: User, val token: String) : AuthState()
    data class Error(val message: String, val retryable: Boolean) : AuthState()
}

// Extension function on sealed class
fun AuthState.canRetry(): Boolean = when (this) {
    is AuthState.Error -> retryable
    is AuthState.Authenticating -> attempt < 3
    is AuthState.Unauthenticated -> false
    is AuthState.Authenticated -> false
}

// Sealed interface for events (UI actions)
sealed interface UiEvent {
    data class Navigate(val route: String) : UiEvent
    data class ShowSnackbar(val message: String) : UiEvent
    data object DismissDialog : UiEvent
}
```

### 4. Data Classes + copy() + Destructuring

```kotlin
// Data class — immutable value object
data class User(
    val id: Long = 0, // 0 until persisted; the repository assigns the real id
    val name: String,
    val email: String,
    val role: Role = Role.USER,
    val isActive: Boolean = true,
    val createdAt: Instant = Instant.now()
)

// copy() — create modified copies without mutation
val user = User(id = 1, name = "Alice", email = "alice@example.com")
val updatedUser = user.copy(name = "Alice Smith")
val promoted = user.copy(role = Role.ADMIN)

// Destructuring declarations
val (id, name, email) = user
println("User $name ($id) — $email")

// Data class with validation in init block
data class Email(val value: String) {
    init {
        require(value.contains("@") && value.contains(".")) {
            "Invalid email format: $value"
        }
    }
}

// Data class in map operations
data class OrderItem(val price: BigDecimal, val quantity: Int)
data class OrderSummary(val orderId: Long, val total: BigDecimal, val itemCount: Int)

val summaries: List<OrderSummary> = orders.map { order ->
    OrderSummary(
        orderId = order.id,
        // sumOf has no BigDecimal overload and BigDecimal has no times(Int) — fold explicitly
        total = order.items.fold(BigDecimal.ZERO) { acc, item ->
            acc + item.price * BigDecimal(item.quantity)
        },
        itemCount = order.items.size
    )
}

// Pair and Triple destructuring
val (key, value) = Pair("host", "localhost")
val (first, second, third) = Triple("a", "b", "c")

// Component functions in for-loops
val map = mapOf("name" to "Alice", "city" to "Berlin")
for ((k, v) in map) {
    println("$k = $v")
}
```

### 5. Extension Functions + DSL Builders

```kotlin
// Extension functions — add behavior to existing types
fun String.isValidEmail(): Boolean =
    matches(Regex("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$"))

fun String.toSlug(): String =
    lowercase().replace(Regex("[^a-z0-9]+"), "-").trim('-')

fun <T> List<T>.secondOrNull(): T? = if (size >= 2) this[1] else null

fun Instant.toRelativeString(): String {
    val duration = Duration.between(this, Instant.now())
    return when {
        duration.toMinutes() < 1 -> "just now"
        duration.toHours() < 1 -> "${duration.toMinutes()}m ago"
        duration.toDays() < 1 -> "${duration.toHours()}h ago"
        else -> "${duration.toDays()}d ago"
    }
}

// Type-safe builder DSL
@DslMarker
annotation class HtmlDsl

// Common supertype so HTML.children can hold both Head and Body
sealed interface Tag {
    fun render(): String
}

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
    fun a(href: String, text: String) { elements.add("""<a href="$href">$text</a>""") }

    override fun render(): String = "<body>\n${elements.joinToString("\n")}\n</body>"
}

@HtmlDsl
class Head : Tag {
    var title: String = ""
    override fun render(): String = "<head><title>$title</title></head>"
}

// Using the DSL
fun html(block: HTML.() -> Unit): HTML = HTML().apply(block)

val page = html {
    head { title = "My Page" }
    body {
        h1("Welcome")
        p("This is a type-safe HTML builder")
        a("https://kotlinlang.org", "Kotlin")
    }
}
println(page.render())
```

### 6. Ktor Server

```kotlin
// Application entry point
fun main() {
    embeddedServer(Netty, port = 8080, host = "0.0.0.0") {
        configurePlugins()
        configureRouting()
    }.start(wait = true)
}

// Plugin configuration
fun Application.configurePlugins() {
    install(ContentNegotiation) {
        json(Json {
            prettyPrint = true
            isLenient = false
            ignoreUnknownKeys = true
            encodeDefaults = true
        })
    }

    install(Authentication) {
        jwt("auth-jwt") {
            realm = "MyApp"
            verifier(
                JWT.require(Algorithm.HMAC256(environment.config.property("jwt.secret").getString()))
                    .withAudience("myapp-users")
                    .withIssuer("myapp")
                    .build()
            )
            validate { credential ->
                if (credential.payload.getClaim("email").asString() != null) {
                    JWTPrincipal(credential.payload)
                } else null
            }
        }
    }

    install(StatusPages) {
        exception<NotFoundException> { call, cause ->
            call.respond(HttpStatusCode.NotFound, ErrorResponse(cause.message ?: "Not found"))
        }
        exception<ValidationException> { call, cause ->
            call.respond(HttpStatusCode.UnprocessableEntity, ErrorResponse(cause.message ?: "Validation failed"))
        }
        exception<Throwable> { call, cause ->
            call.application.log.error("Unhandled exception", cause)
            call.respond(HttpStatusCode.InternalServerError, ErrorResponse("Internal server error"))
        }
    }

    install(CallLogging) {
        level = Level.INFO
        format { call ->
            "${call.request.httpMethod.value} ${call.request.uri} -> ${call.response.status()}"
        }
    }
}

// Routing
fun Application.configureRouting() {
    routing {
        route("/api/v1") {
            get("/health") {
                // mapOf("status" to "UP", "timestamp" to Instant.now()) would fail:
                // Map<String, Any> has no serializer for Any — respond with a @Serializable DTO
                call.respond(HealthResponse(status = "UP", timestamp = Instant.now().toString()))
            }

            authenticate("auth-jwt") {
                route("/users") {
                    get {
                        val page = call.request.queryParameters["page"]?.toIntOrNull() ?: 0
                        val size = call.request.queryParameters["size"]?.toIntOrNull()?.coerceAtMost(100) ?: 20
                        val users = userService.findAll(page, size)
                        call.respond(users)
                    }

                    get("/{id}") {
                        val id = call.parameters["id"]?.toLongOrNull()
                            ?: throw ValidationException("Invalid user ID")
                        // userService.findById returns Either<DomainError, User> (see §8).
                        // fold() unwraps: Left → throw, Right → respond with user.
                        val user = userService.findById(id).fold(
                            { throw NotFoundException(it.message) },
                            { it }
                        )
                        call.respond(user)
                    }

                    post {
                        val request = call.receive<CreateUserRequest>()
                        val user = userService.create(request)
                        call.respond(HttpStatusCode.Created, user)
                    }
                }
            }
        }
    }
}

// Request/Response DTOs
@Serializable
data class CreateUserRequest(
    val name: String,
    val email: String,
    val age: Int? = null
)

@Serializable
data class UserResponse(
    val id: Long,
    val name: String,
    val email: String,
    // kotlinx.serialization has NO built-in java.time.Instant serializer —
    // wire one explicitly (InstantSerializer is defined in §7)
    @Serializable(with = InstantSerializer::class) val createdAt: Instant
)

@Serializable
data class HealthResponse(val status: String, val timestamp: String)

@Serializable
data class ErrorResponse(val message: String)
```

### 7. kotlinx.serialization

```kotlin
import kotlinx.serialization.*
import kotlinx.serialization.json.*
import kotlinx.serialization.modules.*

// Basic serialization
@Serializable
data class User(
    val id: Long,
    val name: String,
    val email: String,
    val tags: List<String> = emptyList(),
    val profile: Profile? = null
)

@Serializable
data class Profile(
    val bio: String,
    val avatarUrl: String? = null
)

// JSON configuration
val json = Json {
    prettyPrint = true
    ignoreUnknownKeys = true
    encodeDefaults = true
    coerceInputValues = true  // null for non-nullable → use default
    isLenient = false
    classDiscriminator = "type" // for polymorphic serialization
    // kotlinx.serialization has no built-in java.time.Instant serializer —
    // register one for every @Contextual Instant property
    serializersModule = module {
        contextual(Instant::class, InstantSerializer)
    }
}

// Serialize / Deserialize
val userJson = json.encodeToString(User(id = 1, name = "Alice", email = "alice@test.com"))
val user = json.decodeFromString<User>(userJson)

// Polymorphic serialization
@Serializable
sealed class Notification {
    abstract val id: String
    abstract val createdAt: Instant
}

@Serializable
@SerialName("email")
data class EmailNotification(
    override val id: String,
    @Contextual override val createdAt: Instant, // resolved via the contextual InstantSerializer
    val subject: String,
    val body: String
) : Notification()

@Serializable
@SerialName("push")
data class PushNotification(
    override val id: String,
    @Contextual override val createdAt: Instant,
    val title: String,
    val payload: Map<String, String>
) : Notification()

// Serializes with discriminator: {"type": "email", "id": "...", ...}

// Custom serializer — kotlinx.serialization ships NO java.time.Instant serializer,
// so the compiler plugin fails with "Serializer has not been found for type 'Instant'"
// unless you wire one. Two options:
//   1) per property: @Serializable(with = InstantSerializer::class)  (Event below)
//   2) contextually: register in Json { serializersModule } + annotate with @Contextual (above)
@Serializable
data class Event(
    @Serializable(with = InstantSerializer::class) val timestamp: Instant,
    val name: String
)

object InstantSerializer : KSerializer<Instant> {
    override val descriptor = PrimitiveSerialDescriptor("Instant", PrimitiveKind.STRING)

    override fun serialize(encoder: Encoder, value: Instant) {
        encoder.encodeString(value.toString())
    }

    override fun deserialize(decoder: Decoder): Instant {
        return Instant.parse(decoder.decodeString())
    }
}

// Surrogate for default values
@Serializable
data class PaginatedResponse<T>(
    val items: List<T>,
    val total: Long,
    val page: Int,
    val pageSize: Int,
    val hasNext: Boolean = false // encodeDefaults = true above → always encoded
)
```

### 8. Result + Either Patterns (Arrow)

```kotlin
import arrow.core.Either
import arrow.core.raise.effect
import arrow.core.raise.ensure
import arrow.core.raise.toEither

// Domain errors as sealed hierarchy
sealed interface DomainError {
    val message: String
    data class NotFound(val entityId: String) : DomainError {
        override val message = "Entity not found: $entityId"
    }
    data class ValidationError(val field: String, val reason: String) : DomainError {
        override val message = "Validation failed for $field: $reason"
    }
    data class Unauthorized(val reason: String) : DomainError {
        override val message = "Unauthorized: $reason"
    }
}

// Collaborator interface (implemented elsewhere, mocked in tests — see §10)
interface EmailService {
    suspend fun sendWelcome(email: String)
}

// Service returning Either — the repository is suspend (see §9), so use the
// suspend-capable effect { } DSL and convert with .toEither() (Arrow 2.x).
// The non-suspend either { } builder cannot call suspend functions.
class UserService(
    private val repo: UserRepository,
    private val emailService: EmailService
) {

    suspend fun findById(id: Long): Either<DomainError, User> = effect {
        val user = repo.findById(id) ?: raise(DomainError.NotFound(id.toString()))
        ensure(user.isActive) { DomainError.Unauthorized("User is deactivated") }
        user
    }.toEither()

    suspend fun create(request: CreateUserRequest): Either<DomainError, User> = effect {
        ensure(request.name.isNotBlank()) {
            DomainError.ValidationError("name", "must not be blank")
        }
        ensure(request.email.isValidEmail()) {
            DomainError.ValidationError("email", "invalid format")
        }
        ensure(!repo.existsByEmail(request.email)) {
            DomainError.ValidationError("email", "already taken")
        }
        val saved = repo.save(User(name = request.name, email = request.email))
        emailService.sendWelcome(saved.email)
        saved
    }.toEither()
}

// Composing Either results — same effect { } DSL for suspend composition
suspend fun processOrder(orderId: Long): Either<DomainError, Receipt> = effect {
    val order = orderService.findById(orderId).bind()
    val user = userService.findById(order.userId).bind()
    val payment = paymentService.charge(user, order.total).bind()
    Receipt(order, user, payment)
}.toEither()

// Kotlin stdlib Result (simpler cases)
fun parseConfig(raw: String): Result<Config> = runCatching {
    json.decodeFromString<Config>(raw)
}.recoverCatching { e ->
    log.warn("Failed to parse config, using defaults: ${e.message}")
    Config.default()
}

// Result chaining
val config = readConfigFile()
    .mapCatching { parseYaml(it) }
    .mapCatching { validate(it) }
    .getOrElse { Config.default() }
```

### 9. Repository Pattern with Coroutines

```kotlin
// Domain interface (no framework dependency)
interface UserRepository {
    suspend fun findById(id: Long): User?
    suspend fun findByEmail(email: String): User?
    suspend fun existsByEmail(email: String): Boolean
    suspend fun findAll(page: Int, size: Int): Page<User>
    suspend fun save(user: User): User
    suspend fun delete(id: Long): Boolean
    fun observeAll(): Flow<List<User>> // reactive stream
}

// Implementation with Exposed or Ktor client
class PostgresUserRepository(
    private val db: Database
) : UserRepository {

    override suspend fun findById(id: Long): User? = dbQuery {
        Users.selectAll().where { Users.id eq id }
            .map { it.toUser() }
            .singleOrNull()
    }

    override suspend fun findAll(page: Int, size: Int): Page<User> = dbQuery {
        val total = Users.selectAll().count()
        val items = Users.selectAll()
            .orderBy(Users.createdAt, SortOrder.DESC)
            .limit(size, (page * size).toLong())
            .map { it.toUser() }
        Page(items, total, page, size)
    }

    override suspend fun save(user: User): User = dbQuery {
        val id = Users.insertAndGetId {
            it[Users.name] = user.name
            it[Users.email] = user.email
            it[Users.createdAt] = user.createdAt
        }
        // insertAndGetId returns EntityID<Long>; User.id is Long — unwrap with .value
        user.copy(id = id.value)
    }

    override fun observeAll(): Flow<List<User>> = callbackFlow {
        val listener = object : UserChangeListener {
            override fun onChanged(users: List<User>) {
                trySend(users)
            }
        }
        registerListener(listener)
        awaitClose { unregisterListener(listener) }
    }

    // Helper to run blocking DB calls on IO dispatcher
    private suspend fun <T> dbQuery(block: suspend () -> T): T =
        withContext(Dispatchers.IO) { block() }
}
```

### 10. Testing (kotest, MockK, Turbine)

```kotlin
// Unit tests with kotest + MockK
class UserServiceTest : DescribeSpec({

    val repository = mockk<UserRepository>()
    val emailService = mockk<EmailService>(relaxed = true)
    val service = UserService(repository, emailService)

    describe("findById") {
        it("should return user when exists") {
            val expected = User(id = 1, name = "Alice", email = "alice@test.com")
            coEvery { repository.findById(1L) } returns expected

            val result = service.findById(1L)

            result.shouldBeRight()
            result.getOrNull() shouldBe expected
        }

        it("should return NotFound error when user doesn't exist") {
            coEvery { repository.findById(99L) } returns null

            val result = service.findById(99L)

            result.shouldBeLeft()
            result.swap().getOrNull() shouldBe DomainError.NotFound("99")
        }
    }

    describe("create") {
        it("should create user with valid data") {
            val request = CreateUserRequest("Bob", "bob@test.com")
            coEvery { repository.existsByEmail("bob@test.com") } returns false
            coEvery { repository.save(any()) } answers {
                firstArg<User>().copy(id = 42L)
            }

            val result = service.create(request)

            result.shouldBeRight()
            result.getOrNull()?.name shouldBe "Bob"
            coVerify { emailService.sendWelcome("bob@test.com") }
        }

        it("should reject blank name") {
            val request = CreateUserRequest("", "test@test.com")

            val result = service.create(request)

            result.shouldBeLeft()
            result.swap().getOrNull() shouldBeInstanceOf DomainError.ValidationError::class
        }
    }
})

// Flow testing with Turbine
// IMPORTANT: UserViewModel uses viewModelScope (= Dispatchers.Main.immediate).
// Tests must set Main dispatcher before each test — otherwise Turbine crashes
// with "Module with the Main dispatcher had failed to initialize".
class UserViewModelTest : DescribeSpec({
    beforeTest { Dispatchers.setMain(UnconfinedTestDispatcher()) }
    afterTest { Dispatchers.resetMain() }

    describe("loadUser") {
        it("should emit Idle, then Loading, then Loaded state") {
            val repository = mockk<UserRepository>()
            val alice = User(id = 1, name = "Alice", email = "a@b.com")
            coEvery { repository.findById(1L) } returns alice

            val viewModel = UserViewModel(repository)

            viewModel.state.test {
                awaitItem() shouldBe UserState.Idle // initial state

                viewModel.loadUser(1L)

                awaitItem() shouldBe UserState.Loading // emitted by loadUser
                awaitItem() shouldBe UserState.Loaded(alice)
            }
        }

        it("should emit Error on failure") {
            val repository = mockk<UserRepository>()
            coEvery { repository.findById(99L) } throws RuntimeException("Network error")

            val viewModel = UserViewModel(repository)

            viewModel.state.test {
                awaitItem() shouldBe UserState.Idle // initial state
                viewModel.loadUser(99L)
                awaitItem() shouldBe UserState.Loading
                val error = awaitItem()
                error shouldBeInstanceOf UserState.Error::class
            }
        }
    }
})
```

### 11. Compose Multiplatform (Shared UI + expect/actual)

```kotlin
// commonMain — shared UI code
@Composable
fun UserListScreen(viewModel: UserListViewModel) {
    val state by viewModel.state.collectAsState()

    when (val s = state) {
        is UserListState.Loading -> CircularProgressIndicator()
        is UserListState.Error -> ErrorView(s.message) { viewModel.retry() }
        is UserListState.Loaded -> {
            LazyColumn {
                items(s.users) { user ->
                    UserCard(user, onClick = { viewModel.selectUser(user.id) })
                }
            }
        }
    }
}

@Composable
fun UserCard(user: User, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(8.dp).clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Row(modifier = Modifier.padding(16.dp)) {
            AsyncImage(
                // User.profile is nullable (see §7); use ?. to access avatarUrl safely
                model = user.profile?.avatarUrl,
                contentDescription = "Avatar of ${user.name}",
                modifier = Modifier.size(48.dp).clip(CircleShape)
            )
            Spacer(Modifier.width(12.dp))
            Column {
                Text(user.name, style = MaterialTheme.typography.titleMedium)
                Text(user.email, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

// expect/actual — platform-specific implementations
// commonMain
expect class PlatformContext
expect fun getPlatformName(): String

// androidMain
actual typealias PlatformContext = android.content.Context
actual fun getPlatformName(): String = "Android ${Build.VERSION.SDK_INT}"

// iosMain — Kotlin/Native interop types come from platform.* packages
// (import platform.Foundation.NSObject; import platform.UIKit.UIDevice)
actual typealias PlatformContext = platform.Foundation.NSObject
actual fun getPlatformName(): String =
    // ObjC properties surface as Kotlin properties — no parentheses
    platform.UIKit.UIDevice.currentDevice.systemName + " " +
        platform.UIKit.UIDevice.currentDevice.systemVersion

// Shared ViewModel (commonMain)
class UserListViewModel(
    private val repository: UserRepository,
    private val scope: CoroutineScope
) {
    private val _state = MutableStateFlow<UserListState>(UserListState.Loading)
    val state: StateFlow<UserListState> = _state.asStateFlow()

    init { loadUsers() }

    fun loadUsers() {
        scope.launch {
            _state.value = UserListState.Loading
            try {
                val page = repository.findAll(0, 50) // returns Page<User> (see §9)
                _state.value = UserListState.Loaded(page.items)
            } catch (e: CancellationException) {
                throw e // always rethrow CancellationException
            } catch (e: Exception) {
                _state.value = UserListState.Error(e.message ?: "Failed to load users")
            }
        }
    }

    fun selectUser(id: Long) { /* navigation */ }
    fun retry() { loadUsers() }
}
```

### 12. KSP (Annotation Processing)

```kotlin
// Custom annotation
@Target(AnnotationTarget.CLASS)
@Retention(AnnotationRetention.SOURCE)
annotation class AutoRepository(val entity: KClass<*>)

// Usage
@AutoRepository(entity = User::class)
interface UserRepo

// KSP Processor
class AutoRepositoryProcessor(
    private val codeGenerator: CodeGenerator,
    private val logger: KSPLogger
) : SymbolProcessor {

    override fun process(resolver: Resolver): List<KSAnnotated> {
        val symbols = resolver.getSymbolsWithAnnotation(AutoRepository::class.qualifiedName!!)
        val unprocessed = mutableListOf<KSAnnotated>()

        symbols.forEach { symbol ->
            if (symbol !is KSClassDeclaration) {
                logger.error("@AutoRepository can only be applied to interfaces", symbol)
                return@forEach
            }

            if (!symbol.validate()) {
                unprocessed.add(symbol)
                return@forEach
            }

            generateRepository(symbol)
        }

        return unprocessed
    }

    private fun generateRepository(interfaceDecl: KSClassDeclaration) {
        val annotation = interfaceDecl.annotations
            .first { it.shortName.asString() == "AutoRepository" }
        val entityType = annotation.arguments.first().value as KSType
        val entityName = entityType.declaration.simpleName.asString()
        val packageName = interfaceDecl.packageName.asString()

        val file = codeGenerator.createNewFile(
            Dependencies(false, interfaceDecl.containingFile!!),
            packageName,
            "${interfaceDecl.simpleName.asString()}Impl"
        )

        file.writeText("""
            package $packageName

            class ${interfaceDecl.simpleName.asString()}Impl(
                private val db: Database
            ) : ${interfaceDecl.simpleName.asString()} {
                // Generated CRUD methods for $entityName
            }
        """.trimIndent().toByteArray())
    }
}

// build.gradle.kts — register KSP
plugins {
    kotlin("jvm") version "2.4.20"
    // Since KSP 2.3.0, KSP is versioned independently of Kotlin (no more
    // "<kotlin>-<ksp>" format) — check google/ksp releases for the latest
    id("com.google.devtools.ksp") version "2.3.12"
}

dependencies {
    ksp(project(":processor")) // your KSP processor module
}
```

## Best Practices

1. **Null safety is mandatory** — never use `!!` (non-null assertion) in production code; use `?.let`, `?:`, `requireNotNull()`, or `checkNotNull()` instead
2. **Structured concurrency** — always use `coroutineScope { }` or a defined `CoroutineScope`; never launch coroutines on `GlobalScope`
3. **Rethrow `CancellationException`** — always `catch (e: CancellationException) { throw e }` before generic catch blocks; swallowing it breaks cancellation
4. **Immutable data by default** — use `data class` with `val` properties; use `copy()` for modifications; avoid `var` unless truly mutable state
5. **Sealed types for states** — model UI state, API results, and domain events as `sealed interface`; enables exhaustive `when` expressions
6. **Flow for reactive streams** — `StateFlow` for state, `SharedFlow` for events; always `.flowOn(Dispatchers.IO)` for upstream I/O
7. **Extension functions over utils** — prefer `fun String.isValidEmail()` over `StringUtils.isValidEmail(String)`; improves readability
8. **DSL markers** — always annotate DSL builders with `@DslMarker` to prevent scope leaking between nested builders
9. **kotlinx.serialization over Jackson** — multiplatform, compile-time safe, no reflection; use `@Serializable` annotations
10. **Test with kotest + MockK** — `coEvery`/`coVerify` for suspend functions; Turbine for Flow testing; `describe`/`it` for BDD-style tests
11. **Use `Result` or `Either`** — never throw exceptions for expected business logic failures; use Arrow's `Either` for domain errors
12. **`withContext(Dispatchers.IO)`** — wrap all blocking calls (JDBC, file I/O, HTTP) in `withContext`; never block the coroutine dispatcher

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---------|-------------|-----|
| `GlobalScope.launch { }` | Unstructured — can't cancel, leaks coroutines | Use `viewModelScope`, `lifecycleScope`, or explicit `CoroutineScope` |
| `!!` (non-null assertion) | `NullPointerException` in production | `?.let { }`, `?: default`, `requireNotNull()` |
| Swallowing `CancellationException` | Breaks coroutine cancellation propagation | Always `catch (e: CancellationException) { throw e }` first |
| Blocking calls in suspend functions | Blocks the coroutine dispatcher thread | `withContext(Dispatchers.IO) { blockingCall() }` |
| `lateinit var` for non-null types | UninitializedPropertyAccessException; hides null from type system | Constructor injection, nullable types, or `by lazy` |
| Not using `@DslMarker` on builders | Outer receiver accessible in nested scope — confusing bugs | Add `@DslMarker` annotation to all DSL scope classes |
| `MutableStateFlow` as public property | External code can mutate internal state | Expose as `StateFlow` (read-only) via `.asStateFlow()` |
| Mixing `callbackFlow` without `awaitClose` | Flow never completes, resource leak | Always call `awaitClose { cleanup() }` in `callbackFlow` |
| Using `runBlocking` in suspend code | Blocks the thread — defeats purpose of coroutines | Use `coroutineScope { }` or call suspend functions directly |
| Not handling `Either` left side | Errors silently ignored | Use `.fold({ error -> }, { value -> })` or `.bind()` in `either { }` |

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| Kotlin | (query "Kotlin") | Language features, coroutines |
| Ktor | `/websites/ktor_io` | Server/client configuration |
| Spring Boot (Kotlin) | `/spring-projects/spring-boot` | Kotlin-specific Spring features |
| Arrow | (query "Arrow Kotlin") | Functional patterns, Either, Option |
| kotlinx.coroutines | (query "kotlinx coroutines") | Coroutine builders, channels |
