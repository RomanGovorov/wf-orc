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
class UserService(private val scope: CoroutineScope) {
    fun loadUser(id: Long) {
        scope.launch {
            try {
                val user = fetchUser(id)
                _state.value = UserState.Loaded(user)
            } catch (e: CancellationException) {
                throw e // always rethrow CancellationException
            } catch (e: Exception) {
                _state.value = UserState.Error(e)
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
class UserViewModel : ViewModel() {
    private val _state = MutableStateFlow<UserState>(UserState.Loading)
    val state: StateFlow<UserState> = _state.asStateFlow()

    fun loadUser(id: Long) {
        viewModelScope.launch {
            _state.value = UserState.Loading
            try {
                val user = repository.getUser(id)
                _state.value = UserState.Loaded(user)
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
    val id: Long,
    val name: String,
    val email: String,
    val role: Role = Role.USER,
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
data class OrderSummary(val orderId: Long, val total: BigDecimal, val itemCount: Int)

val summaries: List<OrderSummary> = orders.map { order ->
    OrderSummary(
        orderId = order.id,
        total = order.items.sumOf { it.price * it.quantity },
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

@HtmlDsl
class HTML {
    private val children = mutableListOf<Tag>()

    fun head(block: Head.() -> Unit) { children.add(Head().apply(block)) }
    fun body(block: Body.() -> Unit) { children.add(Body().apply(block)) }

    fun render(): String = children.joinToString("\n") { it.render() }
}

@HtmlDsl
class Body {
    private val elements = mutableListOf<String>()

    fun h1(text: String) { elements.add("<h1>$text</h1>") }
    fun p(text: String) { elements.add("<p>$text</p>") }
    fun a(href: String, text: String) { elements.add("""<a href="$href">$text</a>""") }

    fun render(): String = "<body>\n${elements.joinToString("\n")}\n</body>"
}

@HtmlDsl
class Head {
    var title: String = ""
    fun render(): String = "<head><title>$title</title></head>"
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
                call.respond(mapOf("status" to "UP", "timestamp" to Instant.now()))
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
                        val user = userService.findById(id)
                            ?: throw NotFoundException("User not found: $id")
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
    val createdAt: Instant
)

@Serializable
data class ErrorResponse(val message: String)
```

### 7. kotlinx.serialization

```kotlin
import kotlinx.serialization.*
import kotlinx.serialization.json.*

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
    override val createdAt: Instant,
    val subject: String,
    val body: String
) : Notification()

@Serializable
@SerialName("push")
data class PushNotification(
    override val id: String,
    override val createdAt: Instant,
    val title: String,
    val payload: Map<String, String>
) : Notification()

// Serializes with discriminator: {"type": "email", "id": "...", ...}

// Custom serializer
@Serializable(with = InstantSerializer::class)
data class Event(val timestamp: Instant, val name: String)

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
    val hasNext: Boolean = false // default encoded only when true
)
```

### 8. Result + Either Patterns (Arrow)

```kotlin
import arrow.core.Either
import arrow.core.left
import arrow.core.right
import arrow.core.raise.either
import arrow.core.raise.ensure

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

// Service returning Either
class UserService(private val repo: UserRepository) {

    fun findById(id: Long): Either<DomainError, User> = either {
        val user = repo.findById(id) ?: raise(DomainError.NotFound(id.toString()))
        ensure(user.isActive) { DomainError.Unauthorized("User is deactivated") }
        user
    }

    fun create(request: CreateUserRequest): Either<DomainError, User> = either {
        ensure(request.name.isNotBlank()) {
            DomainError.ValidationError("name", "must not be blank")
        }
        ensure(request.email.isValidEmail()) {
            DomainError.ValidationError("email", "invalid format")
        }
        ensure(!repo.existsByEmail(request.email)) {
            DomainError.ValidationError("email", "already taken")
        }
        repo.save(User(name = request.name, email = request.email))
    }
}

// Composing Either results
fun processOrder(orderId: Long): Either<DomainError, Receipt> = either {
    val order = orderService.findById(orderId).bind()
    val user = userService.findById(order.userId).bind()
    val payment = paymentService.charge(user, order.total).bind()
    Receipt(order, user, payment)
}

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
            it[name] = user.name
            it[email] = user.email
            it[createdAt] = user.createdAt
        }
        user.copy(id = id)
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
class UserViewModelTest : DescribeSpec({
    describe("loadUser") {
        it("should emit Loading then Loaded state") {
            val repository = mockk<UserRepository>()
            coEvery { repository.getUser(1L) } returns User(id = 1, name = "Alice", email = "a@b.com")

            val viewModel = UserViewModel(repository)

            viewModel.state.test {
                awaitItem() shouldBe UserState.Loading // initial

                viewModel.loadUser(1L)

                awaitItem() shouldBe UserState.Loading // emitted by loadUser
                awaitItem() shouldBe UserState.Loaded(User(id = 1, name = "Alice", email = "a@b.com"))
            }
        }

        it("should emit Error on failure") {
            val repository = mockk<UserRepository>()
            coEvery { repository.getUser(99L) } throws RuntimeException("Network error")

            val viewModel = UserViewModel(repository)

            viewModel.state.test {
                awaitItem() // skip initial
                viewModel.loadUser(99L)
                awaitItem() // Loading
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
                model = user.avatarUrl,
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

// iosMain
actual typealias PlatformContext = cocoapods.NSObject // simplified
actual fun getPlatformName(): String = UIDevice.currentDevice.systemName() + " " + UIDevice.currentDevice.systemVersion

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
            repository.findAll(0, 50)
                .onRight { _state.value = UserListState.Loaded(it.items) }
                .onLeft { _state.value = UserListState.Error(it.message) }
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
    kotlin("jvm") version "2.0.21"
    id("com.google.devtools.ksp") version "2.0.21-1.0.28"
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

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| Kotlin | (query "Kotlin") | Language features, coroutines |
| Ktor | `/websites/ktor_io` | Server/client configuration |
| Spring Boot (Kotlin) | `/spring-projects/spring-boot` | Kotlin-specific Spring features |
| Arrow | (query "Arrow Kotlin") | Functional patterns, Either, Option |
| kotlinx.coroutines | (query "kotlinx coroutines") | Coroutine builders, channels |

Use `mcp__context7__resolve-library-id` then `mcp__context7__query-docs`.
