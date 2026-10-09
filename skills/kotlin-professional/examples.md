# Code Examples: Kotlin Professional

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Complete kotest + MockK Test Suite

```kotlin
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
```

---

## Example 2: Flow Testing with Turbine

```kotlin
// IMPORTANT: UserViewModel uses viewModelScope (= Dispatchers.Main.immediate).
// Tests must set Main dispatcher before each test.
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

                awaitItem() shouldBe UserState.Loading
                awaitItem() shouldBe UserState.Loaded(alice)
            }
        }

        it("should emit Error on failure") {
            val repository = mockk<UserRepository>()
            coEvery { repository.findById(99L) } throws RuntimeException("Network error")

            val viewModel = UserViewModel(repository)

            viewModel.state.test {
                awaitItem() shouldBe UserState.Idle
                viewModel.loadUser(99L)
                awaitItem() shouldBe UserState.Loading
                val error = awaitItem()
                error shouldBeInstanceOf UserState.Error::class
            }
        }
    }
})
```

---

## Example 3: Compose Multiplatform UI

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
```

---

## Example 4: expect/actual — Platform-Specific Implementations

```kotlin
// commonMain
expect class PlatformContext
expect fun getPlatformName(): String

// androidMain
actual typealias PlatformContext = android.content.Context
actual fun getPlatformName(): String = "Android ${Build.VERSION.SDK_INT}"

// iosMain
actual typealias PlatformContext = platform.Foundation.NSObject
actual fun getPlatformName(): String =
    platform.UIKit.UIDevice.currentDevice.systemName + " " +
        platform.UIKit.UIDevice.currentDevice.systemVersion
```

---

## Example 5: Shared ViewModel (commonMain)

```kotlin
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
                val page = repository.findAll(0, 50)
                _state.value = UserListState.Loaded(page.items)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _state.value = UserListState.Error(e.message ?: "Failed to load users")
            }
        }
    }

    fun selectUser(id: Long) { /* navigation */ }
    fun retry() { loadUsers() }
}
```

---

## Example 6: Data Class in Map Operations

```kotlin
data class OrderItem(val price: BigDecimal, val quantity: Int)
data class OrderSummary(val orderId: Long, val total: BigDecimal, val itemCount: Int)

val summaries: List<OrderSummary> = orders.map { order ->
    OrderSummary(
        orderId = order.id,
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

---

## Example 7: Extension Functions

```kotlin
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
```

---

## Example 8: Sealed Class for State Machines

```kotlin
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

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Advanced techniques:** See [`advanced.md`](advanced.md) for deep dives and edge cases
