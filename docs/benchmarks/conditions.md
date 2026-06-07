# DeQuorum benchmark report

- **Model:** `qwen2.5-coder:7b`
- **Router:** `router_factory`
- **Questions:** 5

Each question is run three ways:

1. **Vanilla** — bare base model, generic system prompt, no DeQuorum at all.
2. **DeQuorum full** — route → retrieve approved contributions → category-grounded answer with signed contribution chain.
3. **DeQuorum no-retrieval** — router + category persona only, contributions skipped (isolates the lift of retrieval).

Read all three. Judge honestly. Watch accuracy, refusal.

---

## Bucket: `seeded` (5 questions)

### seeded #1: How do I type a generator function in Python that yields ints and returns a str?

_Expected:_ Route to python-typing, retrieve the Generator[Y, S, R] fact, answer with Generator[int, None, str] and ideally cite [F1].

**A) Vanilla baseline**

```
To create a generator function in Python that yields integers and returns a string, you can use the `yield` keyword to produce integer values during iteration. Once the generator is exhausted (i.e., all values have been yielded), you can return a string from the function.

Here's an example:

```python
def int_generator():
    for i in range(5):
        yield i  # Yield integers 0 through 4
    return "Generator finished"  # Return a string after yielding all integers

# Using the generator
gen = int_generator()
for value in gen:
    print(value)  # Prints 0, 1, 2, 3, 4
print(next(gen))  # Raises StopIteration and prints "Generator finished"
```

In this example, `int_generator` is a generator function that yields integers from 0 to 4. After yielding all values, it returns the string "Generator finished". When you try to get another value after the generator has been exhausted, it raises a `StopIteration` exception and prints the returned string.
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [programming/python/typing(0.42)]`
_Retrieved contributions:_ 3 | _Signature chain:_ 3

```
To type a generator function in Python that yields integers (`int`) and returns a string (`str`), you should use the `Generator[YieldType, SendType, ReturnType]` syntax from the `typing` module. In this case, since your generator does not consume sent values, the `SendType` is `None`. Here's how you can annotate such a function:

```python
from typing import Generator

def my_generator() -> Generator[int, None, str]:
    yield 1
    yield 2
    return "Done"
```

In this example:
- `int` specifies the type of values yielded by the generator.
- `None` indicates that the generator does not accept any sent values.
- `str` is the return type of the generator.

This annotation helps with static type checking and makes your code more robust and easier to understand.
```

**C) DeQuorum no-retrieval (router + category persona only)**

_Routing:_ `embedding: [programming/python/typing(0.42)]`

```
To type a generator function in Python that yields integers (`int`) and returns a string (`str`), you can use the `Generator` type from the `typing` module. Here's how you would define such a function:

```python
from typing import Generator

def my_generator() -> Generator[int, None, str]:
    yield 1
    yield 2
    return "Done"
```

In this example:
- The generator yields integers (`int`).
- It does not accept any values from the caller (hence `None` as the second type argument).
- It returns a string (`str`) when it completes.
```

---

### seeded #2: What's the difference between asyncio.gather and asyncio.wait?

_Expected:_ Route to python-async, retrieve the gather-vs-wait fact, explain the completion semantics difference.

**A) Vanilla baseline**

```
`asyncio.gather` is used to run multiple coroutines concurrently and wait for all of them to complete. It returns a list of results in the order of the input coroutines.

`asyncio.wait`, on the other hand, is more flexible. It can be used to wait for any or all of a set of coroutines/tasks to complete. It returns two sets: one with completed tasks and another with pending tasks.
```

**B) DeQuorum full (route + retrieve + sign)**

_Refused:_ `Ollama unreachable at http://ollama:11434 (is `ollama serve` running?): timed out`

**C) DeQuorum no-retrieval (router + category persona only)**

_Refused:_ `Ollama unreachable at http://ollama:11434 (is `ollama serve` running?): timed out`

---

### seeded #3: How do I use ParamSpec to forward decorator signatures?

_Expected:_ Route to python-typing, retrieve PEP 612 fact, explain ParamSpec usage.

**A) Vanilla baseline**

```
To use `ParamSpec` for forwarding decorator signatures in Python, you need to import it from `typing`. Here’s how you can create a decorator that preserves the signature of the function it decorates:

```python
from typing import Callable, ParamSpec

P = ParamSpec('P')

def my_decorator(func: Callable[P, Any]) -> Callable[P, Any]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        # Your decorator logic here
        return func(*args, **kwargs)
    return wrapper
```

In this example, `P` is a parameter specification that captures the type of arguments and return type of the function. The decorator `my_decorator` takes any callable with signature matching `P`, wraps it in a `wrapper` function that also matches `P`, and returns the wrapped function.

This ensures that the decorated function retains its original type hints, making your code more robust and easier to understand.
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [programming/python/typing(0.37)]`
_Retrieved contributions:_ 2 | _Signature chain:_ 2

```
To use `ParamSpec` for forwarding decorator signatures, you first need to import it from the `typing` module. `ParamSpec` is used to capture the type parameters of a function signature and then re-use them in another function or decorator.

Here's an example of how you can create a decorator that preserves the type information of the function it decorates:

```python
from typing import Callable, ParamSpec

P = ParamSpec('P')

def log_decorator(func: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned: {result}")
        return result
    return wrapper

@log_decorator
def add(a: int, b: int) -> int:
    return a + b

# Usage
result = add(3, 4)
print(result)
```

In this example:
- `P` is defined as a `ParamSpec`, capturing the type parameters of any function it's used with.
- The `log_decorator` takes a callable `func` with signature `Callable[P, R]`.
- Inside the decorator, a `wrapper` function is defined that matches the signature of `func` using `P.args` and `P.kwargs`.
- The `wrapper` function logs the arguments and return value before calling the original `func`.

This way, the type information about the parameters and return type of the decorated function is preserved.
```

**C) DeQuorum no-retrieval (router + category persona only)**

_Refused:_ `Ollama unreachable at http://ollama:11434 (is `ollama serve` running?): timed out`

---

### seeded #4: What protocol does HTTP/3 run on?

_Expected:_ Route to http-protocol, retrieve the QUIC/UDP fact, answer 'QUIC over UDP'.

**A) Vanilla baseline**

```
HTTP/3 runs over UDP (User Datagram Protocol).
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [web-and-protocols/http(0.64)]`
_Retrieved contributions:_ 3 | _Signature chain:_ 3

```
HTTP/3 operates over the QUIC (Quick UDP Internet Connections) protocol, which is a transport layer network protocol designed to provide fast and secure communication between applications. Unlike TCP, QUIC uses UDP for its transport mechanism, which allows it to bypass some of the overhead associated with TCP's connection setup and teardown processes. This makes HTTP/3 particularly well-suited for environments where low latency and high throughput are critical, such as in modern web applications and services that require rapid data exchange.
```

**C) DeQuorum no-retrieval (router + category persona only)**

_Routing:_ `embedding: [web-and-protocols/http(0.64)]`

```
HTTP/3 runs over UDP (User Datagram Protocol) rather than TCP (Transmission Control Protocol), as specified in RFC 9000. This change from TCP to UDP allows for lower latency and potentially higher throughput, making it suitable for applications that require fast response times and can tolerate packet loss or reordering.
```

---

### seeded #5: What are Rust's ownership rules?

_Expected:_ Route to rust-ownership, retrieve the ownership rules fact, explain single-owner + drop semantics.

**A) Vanilla baseline**

```
Rust enforces strict ownership rules to prevent data races and ensure memory safety without garbage collection. The three core rules are:

1. **Ownership**: Each value in Rust has a variable that’s called its owner.
2. **Borrowing**: When you use a value, you can borrow it by referencing it with `&`, `&mut` for mutable references.
3. **Lifetime Annotations**: These specify how long a reference is valid.

These rules ensure that data is always safely managed and prevents common programming errors like null pointers or dangling references.
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [programming/rust/ownership(0.70)]`
_Retrieved contributions:_ 3 | _Signature chain:_ 3

```
Rust's ownership rules ensure memory safety without needing a garbage collector by managing data through three core concepts: owned, borrowed, and moved values.

1. **Owned Values**: An owned value is one that has exclusive control over its data. When an owned value goes out of scope, Rust automatically deallocates the memory it uses. This prevents dangling pointers and double frees.

2. **Borrowed Values**: Borrowed values are references to data that is owned by someone else. They allow you to access data without taking ownership of it. There are two types of borrowed values:
   - **Immutable Borrow (`&T`)**: Allows reading the data but not modifying it.
   - **Mutable Borrow (`&mut T`)**: Allows both reading and modifying the data.

3. **Moved Values**: When you assign an owned value to another variable, or pass it as a parameter to a function, the original owner loses control of the data. This transfer is called moving. After a move, the original variable can no longer be used until the new owner has finished with the data.

These rules are enforced at compile time by Rust's type system and borrowing checker, ensuring that references always point to valid memory and that data is not accessed after it has been freed.
```

**C) DeQuorum no-retrieval (router + category persona only)**

_Routing:_ `embedding: [programming/rust/ownership(0.70)]`

```
Rust's ownership system is a core feature that ensures memory safety without needing a garbage collector. It has three main rules:

1. **Each value in Rust has a variable that’s called its owner.**
   - This means there is always exactly one owner at any given time.

2. **When the owner goes out of scope, the value will be dropped.**
   - This happens automatically when the variable goes out of scope, ensuring that memory is properly cleaned up.

3. **There can only be one mutable reference or multiple immutable references to a particular data in a particular scope.**
   - This prevents data races and ensures that data is not being modified while it's being read by another part of the program.

These rules are enforced at compile time, which means Rust programs will not compile if they violate these ownership rules. This helps prevent common programming errors such as null pointers, dangling pointers, and race conditions.

For more detailed information on Rust's ownership system, you can refer to the official Rust Reference under "Ownership" and the Rustonomicon for a deeper dive into how Rust manages memory and lifetimes.
```

---
