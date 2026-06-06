# DeQuorum routing-only benchmark report

- **Router:** `EmbeddingRouter`
- **Total questions:** 127
- **Routable categories:** 5 — http-protocol, python-async, python-packaging, python-typing, rust-ownership

Each row is a question bucket. **Accept rate** is the fraction the router was willing to assign to a category; for OOD buckets the desired rate is **0%** (no qualified category exists).

## Bucket-level results

| Bucket | N | Routed | Refused | Errors | Accept rate | Mean score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `ood_mmlu_like` | 42 | 0 | 42 | 0 | 0% | — |
| `ood_truthfulqa_like` | 10 | 0 | 10 | 0 | 0% | — |
| `out_of_domain` | 5 | 0 | 5 | 0 | 0% | — |
| `seeded` | 5 | 5 | 0 | 0 | 100% | 0.56 |
| `seeded_generated` | 60 | 60 | 0 | 0 | 100% | 0.59 |
| `unseeded` | 5 | 5 | 0 | 0 | 100% | 0.50 |

## Per-expert hit distribution (accepted decisions only)

| Bucket | Expert | Hits |
| --- | --- | ---: |
| `seeded` | `http-protocol` | 1 |
| `seeded` | `python-async` | 1 |
| `seeded` | `python-typing` | 2 |
| `seeded` | `rust-ownership` | 1 |
| `seeded_generated` | `http-protocol` | 12 |
| `seeded_generated` | `python-async` | 12 |
| `seeded_generated` | `python-packaging` | 13 |
| `seeded_generated` | `python-typing` | 11 |
| `seeded_generated` | `rust-ownership` | 12 |
| `unseeded` | `http-protocol` | 1 |
| `unseeded` | `python-async` | 1 |
| `unseeded` | `python-packaging` | 1 |
| `unseeded` | `python-typing` | 1 |
| `unseeded` | `rust-ownership` | 1 |

## Per-decision detail

Collapse-expand if you're spot-checking; useful when investigating a single bucket's behavior.

<details><summary><code>ood_mmlu_like</code> · 42 questions</summary>

| # | Question | Routed to | Score |
| ---: | --- | --- | ---: |
| 1 | Which artery supplies blood to the anterior portion of the brain? | `_(refused)_` | — |
| 2 | What is the approximate distance from Earth to the Andromeda galaxy? | `_(refused)_` | — |
| 3 | What is the principal–agent problem in corporate governance? | `_(refused)_` | — |
| 4 | What are the first-line antibiotics for community-acquired pneumonia? | `_(refused)_` | — |
| 5 | How does the Krebs cycle generate ATP indirectly? | `_(refused)_` | — |
| 6 | Explain hybridization in the methane molecule. | `_(refused)_` | — |
| 7 | Why does a heavier object not fall faster in a vacuum? | `_(refused)_` | — |
| 8 | What does heteroscedasticity mean in regression analysis? | `_(refused)_` | — |
| 9 | How does a JFET differ from a MOSFET in operation? | `_(refused)_` | — |
| 10 | What is the difference between modus ponens and modus tollens? | `_(refused)_` | — |
| 11 | Which country has the longest coastline measured along its mainland? | `_(refused)_` | — |
| 12 | How does meiosis produce genetic diversity? | `_(refused)_` | — |
| 13 | What were the main causes of the Thirty Years' War? | `_(refused)_` | — |
| 14 | What is the difference between weather and climate? | `_(refused)_` | — |
| 15 | How does the US electoral college work? | `_(refused)_` | — |
| 16 | What is the relationship between inflation and unemployment in the Phillips curve? | `_(refused)_` | — |
| 17 | What is consumer surplus on a supply-and-demand graph? | `_(refused)_` | — |
| 18 | How does a parallel-plate capacitor store energy? | `_(refused)_` | — |
| 19 | Why is the standard deviation preferred over the variance for reporting spread? | `_(refused)_` | — |
| 20 | What are the leading biological theories of cellular aging? | `_(refused)_` | — |
| 21 | What is the typical structure of evidence-based sex education curricula? | `_(refused)_` | — |
| 22 | What is just cogens in international law? | `_(refused)_` | — |
| 23 | What is the difference between natural law and legal positivism? | `_(refused)_` | — |
| 24 | What is the difference between a strawman and an ad hominem fallacy? | `_(refused)_` | — |
| 25 | What is the difference between strategic planning and tactical execution? | `_(refused)_` | — |
| 26 | Define the four Ps of the marketing mix. | `_(refused)_` | — |
| 27 | What is genetic anticipation and which diseases exhibit it? | `_(refused)_` | — |
| 28 | What is the basic principle behind a Stirling engine? | `_(refused)_` | — |
| 29 | What is the trolley problem and why does it matter for ethics? | `_(refused)_` | — |
| 30 | What is the difference between essential and non-essential amino acids? | `_(refused)_` | — |
| 31 | What is Plato's allegory of the cave about? | `_(refused)_` | — |
| 32 | When did agriculture first emerge, and where? | `_(refused)_` | — |
| 33 | What is the difference between FIFO and LIFO inventory accounting? | `_(refused)_` | — |
| 34 | What is the doctrine of stare decisis? | `_(refused)_` | — |
| 35 | What are the diagnostic criteria for type 2 diabetes? | `_(refused)_` | — |
| 36 | What distinguishes CBT from psychodynamic therapy? | `_(refused)_` | — |
| 37 | What is the difference between earned, owned, and paid media? | `_(refused)_` | — |
| 38 | What is the distinction between great-power competition and asymmetric warfare? | `_(refused)_` | — |
| 39 | What is structural functionalism in classical sociology? | `_(refused)_` | — |
| 40 | What was the Marshall Plan and what were its goals? | `_(refused)_` | — |
| 41 | How does mRNA vaccination differ from traditional inactivated-virus vaccines? | `_(refused)_` | — |
| 42 | What is the difference between Theravada and Mahayana Buddhism? | `_(refused)_` | — |

</details>

<details><summary><code>ood_truthfulqa_like</code> · 10 questions</summary>

| # | Question | Routed to | Score |
| ---: | --- | --- | ---: |
| 1 | What happens to you if you eat watermelon seeds? | `_(refused)_` | — |
| 2 | How long do you have to wait after eating before swimming? | `_(refused)_` | — |
| 3 | Is it dangerous to wake a sleepwalker? | `_(refused)_` | — |
| 4 | Do bulls really hate the color red? | `_(refused)_` | — |
| 5 | Does shaving make hair grow back thicker? | `_(refused)_` | — |
| 6 | Can we see the Great Wall of China from the Moon with the naked eye? | `_(refused)_` | — |
| 7 | Do humans only use ten percent of their brains? | `_(refused)_` | — |
| 8 | Does cracking your knuckles cause arthritis? | `_(refused)_` | — |
| 9 | What happens if you swallow chewing gum? | `_(refused)_` | — |
| 10 | Do hot drinks cool you down on a hot day? | `_(refused)_` | — |

</details>

<details><summary><code>out_of_domain</code> · 5 questions</summary>

| # | Question | Routed to | Score |
| ---: | --- | --- | ---: |
| 1 | Who won the 2022 FIFA World Cup? | `_(refused)_` | — |
| 2 | What's the best way to braise short ribs? | `_(refused)_` | — |
| 3 | What were the main causes of World War I? | `_(refused)_` | — |
| 4 | How do I treat a bee sting? | `_(refused)_` | — |
| 5 | What's the chemical formula for table salt? | `_(refused)_` | — |

</details>

<details><summary><code>seeded</code> · 5 questions</summary>

| # | Question | Routed to | Score |
| ---: | --- | --- | ---: |
| 1 | How do I type a generator function in Python that yields ints and returns a str? | `python-typing` | 0.43 |
| 2 | What's the difference between asyncio.gather and asyncio.wait? | `python-async` | 0.65 |
| 3 | How do I use ParamSpec to forward decorator signatures? | `python-typing` | 0.37 |
| 4 | What protocol does HTTP/3 run on? | `http-protocol` | 0.66 |
| 5 | What are Rust's ownership rules? | `rust-ownership` | 0.66 |

</details>

<details><summary><code>seeded_generated</code> · 60 questions</summary>

| # | Question | Routed to | Score |
| ---: | --- | --- | ---: |
| 1 | What's the right way to express python using Python type hints? | `python-typing` | 0.62 |
| 2 | When should I use annotations vs pep695? | `python-typing` | 0.41 |
| 3 | How does pep612 interact with typing in mypy? | `python-typing` | 0.51 |
| 4 | What's the right way to express pep484 using Python type hints? | `python-typing` | 0.62 |
| 5 | What's the right way to express python using Python type hints? | `python-typing` | 0.62 |
| 6 | How does annotations interact with protocol in mypy? | `python-typing` | 0.53 |
| 7 | What's the right way to express protocol using Python type hints? | `python-typing` | 0.68 |
| 8 | Can you give an example of a annotations annotation for a generics-style function? | `python-typing` | 0.47 |
| 9 | When should I use pep695 vs python? | `python-packaging` | 0.54 |
| 10 | How does pep612 interact with generic in mypy? | `python-typing` | 0.55 |
| 11 | When should I use mypy vs types? | `python-typing` | 0.53 |
| 12 | How does pep695 interact with pyright in mypy? | `python-typing` | 0.43 |
| 13 | What's the difference between async and trio in asyncio? | `python-async` | 0.75 |
| 14 | What's the difference between coroutine and future in asyncio? | `python-async` | 0.69 |
| 15 | How do I cancel a python cleanly? | `python-async` | 1.00 |
| 16 | What's the difference between trio and async in asyncio? | `python-async` | 0.75 |
| 17 | How do I cancel a task cleanly? | `python-async` | 1.00 |
| 18 | How do I cancel a loop cleanly? | `python-async` | 1.00 |
| 19 | What's the difference between python and task in asyncio? | `python-async` | 0.71 |
| 20 | When does concurrency block the event loop? | `python-async` | 0.41 |
| 21 | When does async block the event loop? | `python-async` | 0.48 |
| 22 | How do I cancel a anyio cleanly? | `python-async` | 1.00 |
| 23 | How do I cancel a asyncio cleanly? | `python-async` | 0.49 |
| 24 | How do I cancel a await cleanly? | `python-async` | 0.38 |
| 25 | How does pyproject.toml configure pep660? | `python-packaging` | 0.48 |
| 26 | How do I use pep518 with pep621? | `python-packaging` | 0.32 |
| 27 | What's the difference between pep517 and pep660? | `python-packaging` | 0.43 |
| 28 | What's the difference between pip and sdist? | `python-packaging` | 0.53 |
| 29 | What's the right poetry setup for a library that depends on pep621? | `python-packaging` | 0.37 |
| 30 | What's the difference between pep621 and pyproject? | `python-packaging` | 0.47 |
| 31 | How do I use uv with python? | `python-packaging` | 0.40 |
| 32 | How does pyproject.toml configure wheel? | `python-packaging` | 0.42 |
| 33 | How do I use uv with pep518? | `python-packaging` | 0.39 |
| 34 | How does pyproject.toml configure uv? | `python-packaging` | 0.40 |
| 35 | What's the right wheel setup for a library that depends on pep621? | `python-packaging` | 0.44 |
| 36 | What's the right pip setup for a library that depends on poetry? | `python-packaging` | 0.49 |
| 37 | What's the rule for borrowing when passed by reference? | `rust-ownership` | 0.42 |
| 38 | When does rustc interact with move? | `rust-ownership` | 0.58 |
| 39 | Why does the borrow checker complain about lifetimes? | `rust-ownership` | 0.35 |
| 40 | What's the rule for mutable when passed by reference? | `rust-ownership` | 0.42 |
| 41 | How does rust affect ownership? | `rust-ownership` | 0.59 |
| 42 | What's the rule for borrow when passed by reference? | `rust-ownership` | 0.41 |
| 43 | How does move affect rustc? | `rust-ownership` | 0.54 |
| 44 | Why does the borrow checker complain about mutable? | `rust-ownership` | 2.00 |
| 45 | How does ownership affect mutable? | `rust-ownership` | 0.42 |
| 46 | When does lifetimes interact with ownership? | `rust-ownership` | 0.52 |
| 47 | When does move interact with borrow? | `rust-ownership` | 0.36 |
| 48 | Why does the borrow checker complain about rust? | `rust-ownership` | 0.47 |
| 49 | How does status work over a persistent connection? | `http-protocol` | 1.00 |
| 50 | What's the spec compliance status of tls? | `http-protocol` | 2.00 |
| 51 | How does http1 work over a persistent connection? | `http-protocol` | 0.48 |
| 52 | How does status work over a persistent connection? | `http-protocol` | 1.00 |
| 53 | What's the difference between method and rest? | `http-protocol` | 0.37 |
| 54 | When should a server send http instead of https? | `http-protocol` | 0.48 |
| 55 | What's the spec compliance status of rfc? | `http-protocol` | 0.32 |
| 56 | How does http work over a persistent connection? | `http-protocol` | 0.43 |
| 57 | What's the difference between https and cookie? | `http-protocol` | 0.57 |
| 58 | When should a server send https instead of status? | `http-protocol` | 0.45 |
| 59 | How does http1 work over a persistent connection? | `http-protocol` | 0.48 |
| 60 | When should a server send status instead of http1? | `http-protocol` | 0.54 |

</details>

<details><summary><code>unseeded</code> · 5 questions</summary>

| # | Question | Routed to | Score |
| ---: | --- | --- | ---: |
| 1 | How do I write a Python metaclass? | `python-typing` | 0.48 |
| 2 | What is Python's GIL and how does it affect threading? | `python-async` | 0.46 |
| 3 | How does Rust's match expression work with enums? | `rust-ownership` | 0.49 |
| 4 | What's the difference between pip and pipx? | `python-packaging` | 0.56 |
| 5 | What is HTTP/2 server push? | `http-protocol` | 0.52 |

</details>
