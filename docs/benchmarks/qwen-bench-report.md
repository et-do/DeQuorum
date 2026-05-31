# DeQuorum benchmark report

- **Model:** `qwen2.5-coder:7b`
- **Router:** `router_factory`
- **Composition:** `pick_best`
- **Questions:** 15

Each question is run three ways:

1. **Vanilla** — bare base model, generic system prompt, no DeQuorum at all.
2. **DeQuorum full** — route → retrieve approved contributions → expert + signed chain.
3. **DeQuorum no-retrieval** — router + expert persona only, contributions skipped (isolates the lift of retrieval).

Read all three. Judge honestly. Watch accuracy, citation, refusal.

---

## Bucket: `seeded` (5 questions)

### seeded #1: How do I type a generator function in Python that yields ints and returns a str?

_Expected:_ Route to python-typing, retrieve the Generator[Y, S, R] fact, answer with Generator[int, None, str] and ideally cite [F1].

**A) Vanilla baseline**

```
To create a generator function in Python that yields integers and returns a string, you can use the `yield` keyword to produce integer values during iteration. Once the generator is exhausted (i.e., all `yield` statements have been executed), you can return a string from the function.

Here's an example:

```python
def int_generator():
    for i in range(5):
        yield i  # Yield integers 0 through 4
    return "Generator finished"  # Return a string after yielding

# Using the generator
gen = int_generator()
for value in gen:
    print(value)  # Prints 0, 1, 2, 3, 4
print(next(gen))  # Raises StopIteration and prints "Generator finished"
```

In this example, `int_generator` is a generator function that yields integers from 0 to 4. After all integers are yielded, it returns the string "Generator finished".
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [python-typing(0.31)]`
_Retrieved contributions:_ 3 | _Signature chain:_ 4

```
To type a generator function in Python that yields integers (`int`) and returns a string (`str`), you should use the `Generator[YieldType, SendType, ReturnType]` syntax from the `typing` module. For your specific case, where the generator yields integers and returns a string, the type annotation would look like this:

```python
from typing import Generator

def my_generator() -> Generator[int, None, str]:
    yield 1
    yield 2
    return "Done"
```

In this example:
- `int` is the `YieldType`, indicating that the generator yields integers.
- `None` is the `SendType`, which means the generator does not consume sent values (i.e., it doesn't expect any value to be sent into the generator).
- `str` is the `ReturnType`, indicating that the generator returns a string when it completes.
```

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Routing:_ `embedding: [python-typing(0.31)]`

```
To type a generator function in Python that yields integers (`int`) and returns a string (`str`), you can use the `Generator` type from the `typing` module, as specified in PEP 484. Here's how you would define such a function:

```python
from typing import Generator

def my_generator() -> Generator[int, None, str]:
    yield 1
    yield 2
    return "Done"
```

In this example:
- `Generator[int, None, str]` specifies that the generator yields integers (`int`), does not accept any sent values (`None`), and returns a string (`str`).
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

_Routing:_ `embedding: [python-async(0.52)]`
_Retrieved contributions:_ 3 | _Signature chain:_ 4

```
`asyncio.gather` and `asyncio.wait` are both functions used to manage multiple awaitables in Python's asyncio library, but they serve different purposes and have distinct behaviors.

[F1] states that `asyncio.gather` returns when all awaitables complete (or any raises with return_exceptions=False). On the other hand, `asyncio.wait` returns sets of (done, pending) tasks after a configurable condition. This means that while `asyncio.gather` is designed to wait for all tasks to finish and then return their results or exceptions, `asyncio.wait` provides more flexibility by allowing you to specify conditions under which it should stop waiting.

In summary, use `asyncio.gather` when you need a simple way to run multiple coroutines concurrently and wait for them all to complete. Use `asyncio.wait` when you require more control over the waiting process, such as waiting until a certain number of tasks have completed or until a timeout occurs.
```

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Refused:_ `Ollama unreachable at http://localhost:11434 (is `ollama serve` running?): timed out`

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

In this example, `P` is a parameter specification that captures the parameters of the function being decorated. The decorator `my_decorator` takes any callable with signature matching `P`, and returns another callable with the same signature.

You can then use this decorator on any function:

```python
@my_decorator
def my_function(a: int, b: str) -> bool:
    return a > len(b)
```

This ensures that the signature of `my_function` is preserved when it's decorated by `my_decorator`.
```

**B) DeQuorum full (route + retrieve + sign)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

---

### seeded #4: What protocol does HTTP/3 run on?

_Expected:_ Route to http-protocol, retrieve the QUIC/UDP fact, answer 'QUIC over UDP'.

**A) Vanilla baseline**

```
HTTP/3 runs over UDP (User Datagram Protocol).
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [http-protocol(0.63)]`
_Retrieved contributions:_ 3 | _Signature chain:_ 4

```
HTTP/3 runs over the QUIC protocol, which is a UDP-based transport protocol designed to improve upon TCP in several ways, including faster connection setup and reduced latency. [F3]
```

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Routing:_ `embedding: [http-protocol(0.63)]`

```
HTTP/3 runs over UDP (User Datagram Protocol) instead of TCP (Transmission Control Protocol). This change was introduced in RFC 9000 to improve performance and scalability compared to HTTP/2, which uses TCP. The use of UDP allows for lower latency and better handling of packet loss, making it suitable for applications that require real-time communication or have high-latency networks.
```

---

### seeded #5: What are Rust's ownership rules?

_Expected:_ Route to rust-ownership, retrieve the ownership rules fact, explain single-owner + drop semantics.

**A) Vanilla baseline**

```
Rust enforces strict ownership rules to prevent data races and ensure memory safety without garbage collection. The three core rules are:

1. **Ownership**: Each value in Rust has a variable that’s called its owner.
2. **Borrowing**: When you use a value, you can borrow it by referencing it with `&`, allowing multiple parts of your code to access the same data without taking ownership.
3. **Lifetime Annotations**: These specify how long references are valid and help prevent dangling pointers.

These rules ensure that Rust programs do not have issues like null pointers or double frees.
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [rust-ownership(0.62)]`
_Retrieved contributions:_ 3 | _Signature chain:_ 4

```
Rust's ownership rules ensure memory safety without a garbage collector by following these principles:

1. **Each value has exactly one owner**: This means that at any given time, there is only one variable that owns the data.
2. **When the owner goes out of scope, the value is dropped**: Once the owner (variable) is no longer in use, Rust automatically cleans up the memory associated with the value.

These rules help prevent common programming errors such as null pointers and dangling references. [F1]
```

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Routing:_ `embedding: [rust-ownership(0.62)]`

```
Rust's ownership system is a core feature that ensures memory safety without needing a garbage collector. It operates on three main rules:

1. **Ownership**: At any given time, there can be only one owner of a value.
2. **Borrowing**: When you need to use a value but don't want to take ownership, you borrow it. There are two types of borrows:
   - **Immutable Borrow (`&T`)**: Allows multiple parts of the code to read data without mutating it.
   - **Mutable Borrow (`&mut T`)**: Allows exactly one part of the code to modify the data.
3. **Lifetime**: A lifetime is a construct that specifies how long a reference is valid. Lifetimes ensure that references are always valid as long as they need to be.

These rules help Rust prevent common programming errors like null pointers, dangling pointers, and data races. The Rust Reference provides detailed explanations of these concepts, while the Rustonomicon offers deeper insights into the implementation details and optimizations related to ownership and borrowing.
```

---

## Bucket: `unseeded` (5 questions)

### unseeded #1: How do I write a Python metaclass?

_Expected:_ Route to python-typing or python-async (probably python-typing); no retrieval matches; answer comes from base model via expert persona. Should be reasonable.

**A) Vanilla baseline**

```
To create a Python metaclass, you define a class that inherits from `type`. Here's a simple example:

```python
class MyMeta(type):
    def __new__(cls, name, bases, dct):
        print("Creating class:", name)
        return super().__new__(cls, name, bases, dct)

class MyClass(metaclass=MyMeta):
    pass

# Output: Creating class: MyClass
```

In this example, `MyMeta` is a metaclass that prints a message when a new class is created. The `__new__` method of the metaclass is called before the class is fully constructed, allowing you to modify or inspect the class definition.
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [python-packaging(0.35), python-typing(0.33)]`
_Retrieved contributions:_ 4 | _Signature chain:_ 6

```
To write a Python metaclass, you need to define a class that inherits from `type`. A metaclass is essentially a class of a class. Here's a simple example:

```python
class MyMeta(type):
    def __new__(cls, name, bases, dct):
        print("Creating class:", name)
        return super().__new__(cls, name, bases, dct)

class MyClass(metaclass=MyMeta):
    pass

# When you create an instance of MyClass, the metaclass's __new__ method will be called.
obj = MyClass()
```

In this example, `MyMeta` is a metaclass that prints a message when a class is being created. The `__new__` method is a special method in Python classes that is called to create a new instance of a class. When you define a metaclass and assign it to a class using the `metaclass` keyword, Python uses your metaclass to create instances of that class.

Metaclasses are advanced features in Python and should be used with caution as they can make code harder to understand and debug.
```

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Routing:_ `embedding: [python-packaging(0.35), python-typing(0.33)]`

```
Writing a Python metaclass involves defining a class that inherits from `type`. Metaclasses are used to create classes, and they can be customized to control the creation of new classes in various ways.

Here's a basic example of how to define a simple metaclass:

```python
# Define a custom metaclass
class MyMeta(type):
    def __new__(cls, name, bases, dct):
        # Modify or add attributes to the class being created
        dct['my_attribute'] = 'Hello from metaclass'
        return super().__new__(cls, name, bases, dct)

# Use the metaclass in a class definition
class MyClass(metaclass=MyMeta):
    pass

# Create an instance of MyClass and access the added attribute
instance = MyClass()
print(instance.my_attribute)  # Output: Hello from metaclass
```

In this example:
- `MyMeta` is a custom metaclass that inherits from `type`.
- The `__new__` method is overridden to add an attribute `my_attribute` to any class created using this metaclass.
- `MyClass` uses `MyMeta` as its metaclass, so when `MyClass` is defined, the `__new__` method of `MyMeta` is called.

Metaclasses can be used for a variety of purposes, such as:
- Adding default methods or attributes to classes.
- Implementing singletons.
- Validating class definitions at creation time.
- Creating frameworks and libraries that need to control class behavior.

It's important to understand that metaclasses are advanced Python features and should be used with caution. They can make code harder to read and debug, so they should only be used when necessary.
```

---

### unseeded #2: What is Python's GIL and how does it affect threading?

_Expected:_ Route to python-async; no matching contribution; expert prompt should still give a focused answer.

**A) Vanilla baseline**

```
Python's Global Interpreter Lock (GIL) is a mutex that protects access to Python objects, preventing multiple native threads from executing Python bytecodes at once. This lock is necessary because CPython's memory management is not thread-safe.

The GIL affects threading in the following ways:
1. It limits the true parallel execution of Python code across multiple CPU cores.
2. Threads within a single process share the same GIL, so they cannot run simultaneously on multiple CPUs.
3. For I/O-bound and high-level structured network code, the GIL is not a problem because threads can be blocked waiting for I/O operations to complete.
4. However, for CPU-bound tasks, the GIL becomes a bottleneck as only one thread can execute Python bytecode at a time.

To overcome the limitations of the GIL, Python provides other concurrency mechanisms like multiprocessing and asyncio, which allow true parallel execution on multiple cores by creating separate processes or using asynchronous programming.
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [python-async(0.39), python-packaging(0.39)]`
_Retrieved contributions:_ 6 | _Signature chain:_ 8

```
The Global Interpreter Lock, or GIL, is a mutex that protects access to Python objects, preventing multiple native threads from executing Python bytecodes at once. This lock is necessary because CPython’s memory management is not thread-safe. The GIL allows only one thread to execute in the interpreter at any given time, even on multi-core systems.

This means that threading does not provide true parallel execution of Python code due to the GIL. Instead, it can lead to a situation where threads are constantly waiting for the GIL to release, which can result in lower performance than expected. For CPU-bound tasks, this is particularly problematic because only one thread can execute at a time.

For I/O-bound tasks or when you need true parallel execution, Python provides other concurrency models like asyncio and trio, which do not rely on threads but instead use coroutines and event loops to achieve concurrent execution.
```

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Routing:_ `embedding: [python-async(0.39), python-packaging(0.39)]`

```
Python's Global Interpreter Lock (GIL) is a mutex that protects access to Python objects, preventing multiple native threads from executing Python bytecodes at once. This lock is necessary because CPython’s memory management is not thread-safe.

The GIL affects threading in the following ways:
1. **Single-threaded Execution**: Due to the GIL, only one thread can execute Python bytecode at a time, even on multi-core systems.
2. **I/O-bound and CPU-bound Tasks**: For I/O-bound tasks (like file operations or network requests), threads can still run concurrently because they spend most of their time waiting for I/O operations to complete. However, for CPU-bound tasks (like heavy computations), the GIL limits the effectiveness of threading as only one thread can execute Python code at a time.
3. **Concurrency vs Parallelism**: While threading provides concurrency (the ability to do multiple things at once), it does not provide true parallelism (executing multiple threads simultaneously on different CPU cores). For true parallel execution, you would need to use multiprocessing or other mechanisms that bypass the GIL.

To overcome these limitations, Python offers libraries like `asyncio`, `trio`, and `anyio` which allow for asynchronous programming. These libraries use coroutines instead of threads and do not rely on the GIL, thus enabling true parallel execution on multi-core systems.
```

---

### unseeded #3: How does Rust's match expression work with enums?

_Expected:_ Route to rust-ownership; no matching contribution; expert persona should still answer.

**A) Vanilla baseline**

```
Rust's `match` expression is used to handle enum values by comparing them against patterns and executing corresponding code blocks. Each arm of the `match` statement specifies a pattern and an associated block of code. The `match` expression evaluates each pattern in order until it finds one that matches the value, then executes the associated code. This allows for exhaustive handling of all possible enum variants, ensuring no cases are missed.
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [rust-ownership(0.28)]`
_Retrieved contributions:_ 2 | _Signature chain:_ 3

```
Rust's `match` expression is used for pattern matching, which is a powerful feature that allows you to handle different cases of an enum. Enums in Rust are similar to algebraic data types found in functional programming languages.

Here’s how it works:

1. **Pattern Matching**: The `match` expression takes an expression and compares it against several patterns. Each pattern can be as simple or complex as needed, including binding variables, matching specific values, or even handling multiple cases at once.

2. **Arms**: Each pattern is followed by a block of code called an arm. If the value matches the pattern, the corresponding arm's code is executed.

3. **Exhaustiveness**: Rust requires that all possible cases be handled in a `match` expression to ensure that no values are left unhandled. This helps prevent bugs where some cases might be forgotten.

Here’s an example using an enum:

```rust
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
    ChangeColor(i32, i32, i32),
}

fn process_message(msg: Message) {
    match msg {
        Message::Quit => println!("The program is quitting."),
        Message::Move { x, y } => println!("Moving to ({}, {}).", x, y),
        Message::Write(text) => println!("Writing: {}", text),
        Message::ChangeColor(r, g, b) => println!("Changing color to RGB({}, {}, {}).", r, g, b),
    }
}
```

In this example:
- `Message::Quit` matches the Quit variant of the enum.
- `Message::Move { x, y }` matches the Move variant and binds the fields `x` and `y` to variables with the same names.
- `Message::Write(text)` matches the Write variant and binds the text field to a variable named `text`.
- `Message::ChangeColor(r, g, b)` matches the ChangeColor variant and binds the RGB values to variables `r`, `g`, and `b`.

This ensures that every possible value of the enum is handled, making the code robust and error-free.
```

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Routing:_ `embedding: [rust-ownership(0.28)]`

```
Rust's `match` expression is a powerful control flow construct that allows you to handle different variants of an enum. Enums in Rust are similar to algebraic data types found in functional programming languages, providing a way to define a type by listing all possible values it can hold.

Here’s how the `match` expression works with enums:

1. **Pattern Matching**: Each arm of the `match` statement consists of a pattern and an associated code block. The patterns are checked against the value being matched, and the first matching pattern's code is executed.

2. **Enum Variants**: When you match an enum, each variant of the enum can be handled separately. You can destructure the enum to access its fields within the match arms.

3. **Exhaustiveness**: Rust requires that all possible variants are covered in a `match` statement. This ensures that your code handles every case, preventing runtime errors due to unhandled cases.

4. **Binding**: Within each arm of the `match`, you can bind variables to parts of the enum variant. This is useful when you need to use specific fields from an enum variant.

Here’s a simple example:

```rust
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
    ChangeColor(i32, i32, i32),
}

fn process_message(msg: Message) {
    match msg {
        Message::Quit => println!("The program is quitting."),
        Message::Move { x, y } => println!("Moving to ({}, {})", x, y),
        Message::Write(text) => println!("Writing message: {}", text),
        Message::ChangeColor(r, g, b) => println!("Changing color to RGB({}, {}, {})", r, g, b),
    }
}
```

In this example:
- `Message::Quit` matches the Quit variant and prints a message.
- `Message::Move { x, y }` matches the Move variant and binds the fields `x` and `y` to variables with the same names, then uses them in the print statement.
- Similarly, other variants are handled.

The `match` expression is exhaustive, meaning it must cover all possible enum variants. If you omit a case, Rust will give an error indicating that some cases are not covered.

This pattern matching mechanism is fundamental to Rust's type system and helps ensure that your code is robust and handles all possible states of your data.
```

---

### unseeded #4: What's the difference between pip and pipx?

_Expected:_ Route to python-packaging; no matching contribution; expert prompt should give a focused answer.

**A) Vanilla baseline**

```
`pip` is Python's package installer for installing and managing packages from the Python Package Index (PyPI). It installs packages globally or in a virtual environment.

`pipx` is a tool that uses `pip` to install applications in isolated environments, ensuring they don't interfere with each other or the system-wide Python installation. This makes it easier to manage and run standalone Python applications.
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [python-packaging(0.49), python-typing(0.31)]`
_Retrieved contributions:_ 6 | _Signature chain:_ 8

```
pip and pipx are both package managers for Python, but they serve different purposes and have distinct features.

**pip** [F2] is a standard package manager used to install, upgrade, and manage Python packages from the Python Package Index (PyPI) and other indexes. It can handle both source distributions (.tar.gz) and wheel files (.whl). Pip is installed with Python and is typically used for installing packages in a virtual environment or globally.

**pipx** [F2] is designed to install and run applications in isolated environments, ensuring that each application has its own dependencies and does not interfere with the system-wide Python installation. This isolation helps prevent conflicts between different projects' requirements and makes it easier to manage permissions and updates. Pipx is particularly useful for installing command-line tools or scripts that are not meant to be used as libraries.

In summary, while pip is a general-purpose package manager for Python packages, pipx is specifically designed for managing standalone applications in isolated environments.
```

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Routing:_ `embedding: [python-packaging(0.49), python-typing(0.31)]`

```
`pip` and `pipx` are both tools used for managing Python packages, but they serve different purposes and operate in distinct ways.

**Pip** is the standard package manager for Python. It allows you to install, upgrade, and manage Python packages from the Python Package Index (PyPI) and other indexes. Pip operates at a lower level than pipx and does not isolate applications or their dependencies. When you use pip to install a package, it installs it in the global Python environment, which can affect all Python scripts on your system.

**Pipx**, on the other hand, is designed for installing and running Python applications in isolated environments. It ensures that each application has its own set of dependencies, separate from the global Python environment. This isolation helps prevent conflicts between different applications' dependencies and keeps your system clean and organized. Pipx creates a virtual environment for each application it installs and runs the application within this isolated environment.

In summary, while pip is used to manage packages in general, pipx is specifically designed for installing and running standalone Python applications with their own isolated environments.
```

---

### unseeded #5: What is HTTP/2 server push?

_Expected:_ Route to http-protocol; no matching contribution; expert prompt should answer.

**A) Vanilla baseline**

```
HTTP/2 server push is a feature that allows a server to proactively send resources to a client before the client requests them. This can reduce latency and improve page load times by anticipating what resources will be needed next.
```

**B) DeQuorum full (route + retrieve + sign)**

_Routing:_ `embedding: [http-protocol(0.45)]`
_Retrieved contributions:_ 3 | _Signature chain:_ 4

```
HTTP/2 server push [F3] is a feature that allows a server to proactively send resources to the client before they are requested by the client. This can reduce latency and improve performance by allowing the browser to start loading resources as soon as possible, rather than waiting for each resource to be explicitly requested.

In HTTP/2, when a server pushes a resource, it sends an additional frame on the same connection that carries the pushed resource's data. The client then caches this resource and can use it immediately if needed, without having to wait for another request from the client.

This feature is particularly useful for resources that are likely to be requested soon after the initial page load, such as images or scripts that are referenced in the HTML document. By pushing these resources ahead of time, the server can help ensure that they are available when needed, potentially improving the overall user experience.
```

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Routing:_ `embedding: [http-protocol(0.45)]`

```
HTTP/2 server push is a feature defined in RFC 7540 that allows a server to proactively send resources to a client before the client requests them. This can significantly improve performance by reducing latency and bandwidth usage, especially for pages with many resources.

In HTTP/1.1, clients must explicitly request each resource they need, which can lead to multiple round trips between the client and server if the page requires several resources. With HTTP/2 server push, the server can predict what resources will be needed by the client based on the initial request and send them before the client asks for them.

This feature is particularly useful for reducing latency in web applications where many resources are required to render a single page. By pushing these resources ahead of time, the server can reduce the number of round trips required to load the page, thereby improving the overall performance of the application.
```

---

## Bucket: `out_of_domain` (5 questions)

### out_of_domain #1: Who won the 2022 FIFA World Cup?

_Expected:_ EmbeddingRouter should reject (no expert above threshold). Pipeline raises CompositionError. Vanilla Qwen will probably answer (correctly or not).

**A) Vanilla baseline**

```
France won the 2022 FIFA World Cup.
```

**B) DeQuorum full (route + retrieve + sign)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

---

### out_of_domain #2: What's the best way to braise short ribs?

_Expected:_ EmbeddingRouter should reject. Vanilla Qwen will answer.

**A) Vanilla baseline**

```
To braise short ribs effectively:
1. Season with salt, pepper, and your choice of spices.
2. Brown them in oil until crispy on all sides.
3. Add a liquid (like beer, wine, or beef broth) and enough water to cover.
4. Simmer gently for 2-3 hours or until tender.
5. Serve hot, often with a side of mashed potatoes or noodles.
```

**B) DeQuorum full (route + retrieve + sign)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

---

### out_of_domain #3: What were the main causes of World War I?

_Expected:_ EmbeddingRouter should reject. Vanilla Qwen will answer.

**A) Vanilla baseline**

```
The main causes of World War I included:

1. Nationalism and imperial competition among European powers.
2. Alliances between major European nations that created a web of commitments.
3. Militarism, with countries maintaining large standing armies and navies.
4. The assassination of Archduke Franz Ferdinand of Austria-Hungary by a Serbian nationalist.
5. A complex system of diplomatic entanglements that escalated the conflict.
```

**B) DeQuorum full (route + retrieve + sign)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

---

### out_of_domain #4: How do I treat a bee sting?

_Expected:_ EmbeddingRouter should reject (medical knowledge not in network). Vanilla will answer. This tests our refusal-over-hallucination on a high-stakes topic.

**A) Vanilla baseline**

```
To treat a bee sting:

1. Remove the stinger by scraping it out with a credit card or fingernail.
2. Clean the area with soap and water.
3. Apply ice to reduce swelling and pain.
4. Take over-the-counter pain relievers if needed.
5. Monitor for allergic reactions.

If symptoms persist or worsen, seek medical attention.
```

**B) DeQuorum full (route + retrieve + sign)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

---

### out_of_domain #5: What's the chemical formula for table salt?

_Expected:_ EmbeddingRouter should reject. Vanilla Qwen will answer trivially.

**A) Vanilla baseline**

```
The chemical formula for table salt is NaCl.
```

**B) DeQuorum full (route + retrieve + sign)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

**C) DeQuorum no-retrieval (router + expert prompt only)**

_Refused:_ `no qualified expert above the routing threshold — register a relevant expert or lower the threshold`

---
