"""A real contested-fact corpus for the attribution head-to-head (§8.6).

The synthetic generator uses invented tokens, which buys exact ground truth but
raises an external-validity objection: the false twin is a fabricated flip. This
corpus instead pairs **real, verifiable facts** with their **real, documented common
misconception** as the false twin — the TruthfulQA-style regime where a model is
genuinely prone to the wrong answer. Queries and true facts are real; the false note
states the actual misconception people (and models) hold, not an invented value. Items
are drawn from well-documented common-misconception sources (e.g. the Wikipedia "List
of common misconceptions" and standard reference facts) and span geography, astronomy,
physics, biology, history, language, and everyday reasoning.

Each entry has the same `NoveltyFact` shape as the synthetic corpus, so it drops into
the same benchmark. `gold` / `false_gold` are short distinctive phrases chosen so the
keyword grader can tell a correct answer from the misconception; the corpus's
validation test asserts every pair is separable (the true note recalls the gold and
NOT the misconception, and vice versa) — otherwise the experiment would be meaningless.

Provenance and limits (see docs/research/contested-facts-datasheet.md): single-author
curation from documented misconception sources; each item is individually verifiable
but the set is not independently annotated, and n is modest. Growing it and obtaining
third-party labels is stated as open work in the paper.
"""

from __future__ import annotations

from dequorum.benchmark.novelty import NoveltyFact


def _f(
    query: str,
    subject: str,
    true_val: str,
    gold: tuple[str, ...],
    false_val: str,
    false_gold: tuple[str, ...],
    paraphrase: str,
) -> NoveltyFact:
    return NoveltyFact(
        note=f"{subject} {true_val}.",
        query=query,
        gold=gold,
        paraphrase=paraphrase,
        false_note=f"{subject} {false_val}.",
        false_gold=false_gold,
    )


# --- Geography ------------------------------------------------------------
_GEOGRAPHY: tuple[NoveltyFact, ...] = (
    _f(
        "What is the capital of Australia?",
        "The capital of Australia is",
        "Canberra",
        ("Canberra",),
        "Sydney",
        ("Sydney",),
        "Which city is Australia's seat of government?",
    ),
    _f(
        "What is the capital of Turkey?",
        "The capital of Turkey is",
        "Ankara",
        ("Ankara",),
        "Istanbul",
        ("Istanbul",),
        "Which city is the capital of Turkey?",
    ),
    _f(
        "What is the capital of Canada?",
        "The capital of Canada is",
        "Ottawa",
        ("Ottawa",),
        "Toronto",
        ("Toronto",),
        "Which city is Canada's capital?",
    ),
    _f(
        "What is the capital of Brazil?",
        "The capital of Brazil is",
        "Brasilia",
        ("Brasilia",),
        "Rio de Janeiro",
        ("Rio de Janeiro",),
        "Which city is the capital of Brazil?",
    ),
    _f(
        "What is the capital of New Zealand?",
        "The capital of New Zealand is",
        "Wellington",
        ("Wellington",),
        "Auckland",
        ("Auckland",),
        "Which city is New Zealand's capital?",
    ),
    _f(
        "What is the capital of the United States?",
        "The capital of the United States is",
        "Washington, D.C.",
        ("Washington",),
        "New York City",
        ("New York",),
        "Which city is the U.S. capital?",
    ),
    _f(
        "What is the largest U.S. state by area?",
        "The largest U.S. state by area is",
        "Alaska",
        ("Alaska",),
        "Texas",
        ("Texas",),
        "Which American state covers the most land?",
    ),
    _f(
        "What is the smallest country in the world?",
        "The smallest country in the world is",
        "Vatican City",
        ("Vatican City",),
        "Monaco",
        ("Monaco",),
        "Which sovereign state has the least land area?",
    ),
    _f(
        "What is the largest desert on Earth?",
        "The largest desert on Earth is",
        "Antarctica",
        ("Antarctica",),
        "the Sahara",
        ("Sahara",),
        "Which desert covers the greatest area worldwide?",
    ),
    _f(
        "What is the largest island in the world?",
        "The largest island in the world is",
        "Greenland",
        ("Greenland",),
        "Australia",
        ("Australia",),
        "Which landmass is the biggest island, excluding continents?",
    ),
    _f(
        "Measured from base to peak, what is the tallest mountain on Earth?",
        "Measured from its base on the ocean floor to its peak, the tallest is",
        "Mauna Kea",
        ("Mauna Kea",),
        "Mount Everest",
        ("Everest",),
        "Which mountain is tallest measured base-to-summit rather than by elevation?",
    ),
)

# --- Astronomy & physics --------------------------------------------------
_PHYSICS: tuple[NoveltyFact, ...] = (
    _f(
        "What color is the Sun when viewed from space?",
        "Viewed from space, outside Earth's atmosphere, the Sun is",
        "white",
        ("white",),
        "yellow",
        ("yellow",),
        "Seen from orbit, what is the true color of sunlight?",
    ),
    _f(
        "What causes the seasons on Earth?",
        "Earth's seasons are caused by",
        "the tilt of its axis",
        ("tilt",),
        "its changing distance from the Sun",
        ("distance",),
        "Why does Earth have summer and winter?",
    ),
    _f(
        "On average over time, which planet is closest to Earth?",
        "Averaged over its orbit, the planet closest to Earth is",
        "Mercury",
        ("Mercury",),
        "Venus",
        ("Venus",),
        "Which planet spends the most time being nearest to Earth on average?",
    ),
    _f(
        "Which is the hottest planet in the solar system?",
        "The hottest planet in the solar system is",
        "Venus",
        ("Venus",),
        "Mercury",
        ("Mercury",),
        "Which planet has the highest surface temperature?",
    ),
    _f(
        "What is the Sun mostly made of?",
        "The Sun is mostly",
        "hydrogen",
        ("hydrogen",),
        "burning fire",
        ("fire",),
        "What is the Sun's main constituent?",
    ),
    _f(
        "About how long does light from the Sun take to reach Earth?",
        "Light from the Sun takes about",
        "eight minutes to reach Earth",
        ("eight minutes",),
        "one second to reach Earth",
        ("one second",),
        "How long is sunlight's travel time to Earth?",
    ),
    _f(
        "Does sound travel faster through water or through air?",
        "Sound travels faster through",
        "water",
        ("water",),
        "air",
        ("air",),
        "In which medium does sound move more quickly, water or air?",
    ),
    _f(
        "Is glass a liquid or a solid?",
        "Glass is an amorphous",
        "solid",
        ("solid",),
        "slowly flowing liquid",
        ("liquid",),
        "Is ordinary glass classified as a solid or a liquid?",
    ),
)

# --- Biology & the human body ---------------------------------------------
_BIOLOGY: tuple[NoveltyFact, ...] = (
    _f(
        "What is the largest organ in the human body?",
        "The largest organ in the human body is the",
        "skin",
        ("skin",),
        "liver",
        ("liver",),
        "Which single organ has the greatest surface area or mass in humans?",
    ),
    _f(
        "Which blood vessels carry blood away from the heart?",
        "The blood vessels that carry blood away from the heart are the",
        "arteries",
        ("arteries",),
        "veins",
        ("veins",),
        "Do arteries or veins move blood outward from the heart?",
    ),
    _f(
        "What color is human blood inside the body?",
        "Inside the body, human blood is",
        "red",
        ("red",),
        "blue",
        ("blue",),
        "Is deoxygenated blood in the veins actually red or blue?",
    ),
    _f(
        "How many bones are in the adult human body?",
        "The number of bones in the adult human body is",
        "206",
        ("206",),
        "208",
        ("208",),
        "How many bones does a fully grown human skeleton have?",
    ),
    _f(
        "Which vitamin does the body produce when skin is exposed to sunlight?",
        "When skin is exposed to sunlight, the body produces",
        "vitamin D",
        ("vitamin D",),
        "vitamin C",
        ("vitamin C",),
        "Sunlight on the skin synthesizes which vitamin?",
    ),
    _f(
        "Are dolphins fish or mammals?",
        "Dolphins are",
        "mammals",
        ("mammals",),
        "fish",
        ("fish",),
        "Do dolphins belong to the mammals or the fish?",
    ),
    _f(
        "Are spiders insects?",
        "Spiders are",
        "arachnids",
        ("arachnids",),
        "insects",
        ("insects",),
        "Which group do spiders belong to?",
    ),
    _f(
        "How many hearts does an octopus have?",
        "An octopus has",
        "three hearts",
        ("three",),
        "one heart",
        ("one heart",),
        "What is the number of hearts in an octopus?",
    ),
    _f(
        "What do camels store in their humps?",
        "Camels store in their humps",
        "fat",
        ("fat",),
        "water",
        ("water",),
        "What substance is held inside a camel's hump?",
    ),
    _f(
        "Why do chameleons change color?",
        "Chameleons primarily change color for",
        "communication and temperature regulation",
        ("communication",),
        "camouflage against their surroundings",
        ("camouflage",),
        "What is the main reason a chameleon shifts its color?",
    ),
    _f(
        "Which gas do plants primarily absorb for photosynthesis?",
        "For photosynthesis, plants primarily absorb",
        "carbon dioxide",
        ("carbon dioxide",),
        "oxygen",
        ("oxygen",),
        "What gas do plants take in to make food from sunlight?",
    ),
    _f(
        "What is the most abundant gas in Earth's atmosphere?",
        "The most abundant gas in Earth's atmosphere is",
        "nitrogen",
        ("nitrogen",),
        "oxygen",
        ("oxygen",),
        "Which gas makes up most of the air we breathe?",
    ),
    _f(
        "Botanically, is a tomato a fruit or a vegetable?",
        "Botanically, a tomato is a",
        "fruit",
        ("fruit",),
        "vegetable",
        ("vegetable",),
        "In botanical terms, does a tomato count as a fruit or a vegetable?",
    ),
    _f(
        "Are peanuts nuts or legumes?",
        "Peanuts are",
        "legumes",
        ("legumes",),
        "true nuts",
        ("true nuts",),
        "Do peanuts belong to the legumes or the tree nuts?",
    ),
    _f(
        "How long is a goldfish's memory?",
        "A goldfish's memory lasts",
        "months",
        ("months",),
        "three seconds",
        ("three seconds",),
        "Over what span can a goldfish actually remember things?",
    ),
)

# --- Language, math, and everyday reasoning -------------------------------
_MISC: tuple[NoveltyFact, ...] = (
    _f(
        "Which language has the most native speakers in the world?",
        "The language with the most native speakers is",
        "Mandarin Chinese",
        ("Mandarin",),
        "English",
        ("English",),
        "What is the world's most spoken first language by native speakers?",
    ),
    _f(
        "What is the official language of Brazil?",
        "The official language of Brazil is",
        "Portuguese",
        ("Portuguese",),
        "Spanish",
        ("Spanish",),
        "Which language do Brazilians officially speak?",
    ),
    _f(
        "What is the official language of Austria?",
        "The official language of Austria is",
        "German",
        ("German",),
        "Austrian",
        ("Austrian",),
        "Which language is officially spoken in Austria?",
    ),
    _f(
        "What is the official currency of Switzerland?",
        "The official currency of Switzerland is the",
        "Swiss franc",
        ("franc",),
        "euro",
        ("euro",),
        "Which currency does Switzerland use?",
    ),
    _f(
        "What is the smallest prime number?",
        "The smallest prime number is",
        "2",
        ("2",),
        "1",
        ("1",),
        "Which is the least prime number?",
    ),
    _f(
        "Which weighs more, a pound of feathers or a pound of bricks?",
        "A pound of feathers and a pound of bricks weigh",
        "the same",
        ("the same",),
        "different amounts, the bricks being heavier",
        ("heavier",),
        "Between a pound of feathers and a pound of bricks, which is heavier?",
    ),
    _f(
        "How many spiders does the average person swallow per year in their sleep?",
        "The average person swallows in their sleep",
        "zero spiders per year",
        ("zero",),
        "about eight spiders per year",
        ("eight",),
        "On average, how many spiders do sleeping people swallow annually?",
    ),
    _f(
        "Was Napoleon Bonaparte unusually short?",
        "For his era, Napoleon Bonaparte was of",
        "average height",
        ("average height",),
        "unusually short stature",
        ("unusually short",),
        "Did Napoleon have a below-average or an average height for his time?",
    ),
    _f(
        "Where did fortune cookies originate?",
        "Fortune cookies originated in",
        "Japan",
        ("Japan",),
        "China",
        ("China",),
        "In which country did the fortune cookie first appear?",
    ),
    _f(
        "What makes a bull charge at a matador's cape?",
        "A bull charges at the cape because of its",
        "motion",
        ("motion",),
        "red color",
        ("red",),
        "Is it the color or the movement of the cape that provokes a bull?",
    ),
)

REAL_CONTESTED_FACTS: tuple[NoveltyFact, ...] = _GEOGRAPHY + _PHYSICS + _BIOLOGY + _MISC
