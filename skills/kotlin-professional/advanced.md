# Advanced Patterns: Kotlin Professional

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Result + Either Patterns (Arrow)

Functional error handling with Arrow's Either type.

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

// Service returning Either — use suspend-capable effect { } DSL
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

// Composing Either results
suspend fun processOrder(orderId: Long): Either<DomainError, Receipt> = effect {
    val order = orderService.findById(orderId).bind()
    val user = userService.findById(order.userId).bind()
    val payment = paymentService.charge(user, order.total).bind()
    Receipt(order, user, payment)
}.toEither()
```

### Kotlin stdlib Result (simpler cases)

```kotlin
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

---

## Repository Pattern with Coroutines

```kotlin
// Domain interface (no framework dependency)
interface UserRepository {
    suspend fun findById(id: Long): User?
    suspend fun findByEmail(email: String): User?
    suspend fun existsByEmail(email: String): Boolean
    suspend fun findAll(page: Int, size: Int): Page<User>
    suspend fun save(user: User): User
    suspend fun delete(id: Long): Boolean
    fun observeAll(): Flow<List<User>>
}

// Implementation
class PostgresUserRepository(private val db: Database) : UserRepository {

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
        user.copy(id = id.value)
    }

    override fun observeAll(): Flow<List<User>> = callbackFlow {
        val listener = object : UserChangeListener {
            override fun onChanged(users: List<User>) { trySend(users) }
        }
        registerListener(listener)
        awaitClose { unregisterListener(listener) }
    }

    private suspend fun <T> dbQuery(block: suspend () -> T): T =
        withContext(Dispatchers.IO) { block() }
}
```

---

## SharedFlow — Event Bus Pattern

```kotlin
class EventBus {
    private val _events = MutableSharedFlow<AppEvent>(
        replay = 0,
        extraBufferCapacity = 64,
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )
    val events: SharedFlow<AppEvent> = _events.asSharedFlow()

    suspend fun emit(event: AppEvent) = _events.emit(event)
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
    .flowOn(Dispatchers.IO)
```

---

## SupervisorJob — Independent Child Failures

```kotlin
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

---

## Ktor Server — Full Configuration

```kotlin
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

fun Application.configureRouting() {
    routing {
        route("/api/v1") {
            get("/health") {
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
```

---

## kotlinx.serialization — Advanced Features

```kotlin
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
    @Contextual override val createdAt: Instant,
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

// Custom Instant serializer
object InstantSerializer : KSerializer<Instant> {
    override val descriptor = PrimitiveSerialDescriptor("Instant", PrimitiveKind.STRING)

    override fun serialize(encoder: Encoder, value: Instant) {
        encoder.encodeString(value.toString())
    }

    override fun deserialize(decoder: Decoder): Instant {
        return Instant.parse(decoder.decodeString())
    }
}

// JSON configuration with contextual serializer
val json = Json {
    prettyPrint = true
    ignoreUnknownKeys = true
    encodeDefaults = true
    coerceInputValues = true
    classDiscriminator = "type"
    serializersModule = module {
        contextual(Instant::class, InstantSerializer)
    }
}
```

---

## KSP (Annotation Processing)

```kotlin
@Target(AnnotationTarget.CLASS)
@Retention(AnnotationRetention.SOURCE)
annotation class AutoRepository(val entity: KClass<*>)

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
        val entityType = interfaceDecl.annotations
            .first { it.shortName.asString() == "AutoRepository" }
            .arguments.first().value as KSType
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
            ) : ${interfaceDecl.simpleName.asString()}() {
                // Generated CRUD methods for $entityName
            }
        """.trimIndent().toByteArray())
    }
}

// build.gradle.kts
plugins {
    kotlin("jvm") version "2.4.20"
    id("com.google.devtools.ksp") version "2.3.12"
}

dependencies {
    ksp(project(":processor"))
}
```

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
