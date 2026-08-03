"""Diverse code-generation prompts with parametrized semantics.

Every prompt asks for one Python function. Random parameters change what
the function must DO (the parameters appear in the prompt text), and each
instance carries a reference solution plus deterministic test inputs.
A generation passes iff, executed in isolation, its function returns
exactly the reference outputs on all test inputs.

Difficulty is structural:
- simple:  single-pass list arithmetic with 1-2 parameters
- medium:  two-step transforms (filter + aggregate, sort + select)
- complex: stateful scans (run-length, windowing, interval merging)
- extreme: fiddly multi-rule string/number formatting with interacting rules

Prompts are deduplicated by TEXT (at temperature=0 the model's behavior is
a function of the text alone). Generation is seeded and deterministic.
"""

import numpy as np

from eval_harness.core.types import Prompt

FUNC_NAME = "solve"


def _gen_simple(rng):
    kind = int(rng.integers(0, 3))
    if kind == 0:
        k = int(rng.integers(2, 8))
        start = int(rng.integers(0, 4))
        spec = (f"takes a list of integers and returns the sum of every "
                f"{k}-th element starting at index {start} "
                f"(i.e., indices {start}, {start + k}, {start + 2 * k}, ...)")
        ref = lambda xs: sum(xs[start::k])
    elif kind == 1:
        t = int(rng.integers(-5, 20))
        d = int(rng.integers(2, 7))
        spec = (f"takes a list of integers and returns how many elements are "
                f"strictly greater than {t} and divisible by {d}")
        ref = lambda xs: sum(1 for x in xs if x > t and x % d == 0)
    else:
        m = int(rng.integers(2, 8))
        op = str(rng.choice(["negated", "doubled", "squared"]))
        fn = {"negated": lambda x: -x,
              "doubled": lambda x: 2 * x,
              "squared": lambda x: x * x}[op]
        spec = (f"takes a list of integers and returns a new list where every "
                f"element at an index divisible by {m} is {op} (index 0 "
                f"counts as divisible) and all other elements are unchanged")
        ref = lambda xs: [fn(x) if i % m == 0 else x for i, x in enumerate(xs)]

    tests = [
        [int(v) for v in rng.integers(-30, 30, int(rng.integers(4, 12)))]
        for _ in range(6)
    ]
    tests.append([])
    return spec, ref, [(t,) for t in tests]


def _gen_medium(rng):
    kind = int(rng.integers(0, 3))
    if kind == 0:
        k = int(rng.integers(1, 7))
        order = str(rng.choice(["highest", "lowest"]))
        spec = (f"takes a list of (name, score) tuples and returns the names "
                f"of the {order}-scoring {k} entries, {order} first; break "
                f"score ties alphabetically by name; if fewer than {k} items, "
                f"return all of them in that order")
        sign = -1 if order == "highest" else 1
        ref = lambda xs: [n for n, s in
                          sorted(xs, key=lambda p: (sign * p[1], p[0]))][:k]
        names = ["ann", "bob", "cat", "dan", "eve", "fay", "gus", "hal"]
        tests = []
        for _ in range(6):
            sz = int(rng.integers(0, 7))
            picks = list(rng.choice(len(names), size=sz, replace=False))
            tests.append(([(names[i], int(rng.integers(0, 8))) for i in picks],))
    elif kind == 1:
        r = int(rng.integers(1, 10))
        m = int(rng.integers(2, 6))
        spec = (f"takes a list, rotates it left by {r} positions (elements "
                f"wrap around), then returns every {m}-th element of the "
                f"rotated list starting at index 0; return [] for an empty list")
        def ref(xs, r=r, m=m):
            if not xs:
                return []
            rr = r % len(xs)
            rot = xs[rr:] + xs[:rr]
            return rot[::m]
        tests = [([int(v) for v in rng.integers(0, 50, int(rng.integers(0, 10)))],)
                 for _ in range(7)]
    else:
        sep = str(rng.choice([",", ";", "|", ":"]))
        lo = int(rng.integers(2, 10))
        spec = (f"takes a string of integer tokens separated by '{sep}' and "
                f"returns the sum of tokens whose absolute value is at least "
                f"{lo}; an empty string returns 0 (tokens may have leading '-')")
        def ref(text, sep=sep, lo=lo):
            if not text:
                return 0
            return sum(v for v in (int(t) for t in text.split(sep))
                       if abs(v) >= lo)
        tests = []
        for _ in range(6):
            vals = [str(int(v)) for v in rng.integers(-15, 16, int(rng.integers(0, 8)))]
            tests.append((sep.join(vals),))
    return spec, ref, tests


def _gen_complex(rng):
    kind = int(rng.integers(0, 3))
    if kind == 0:
        min_run = int(rng.integers(2, 9))
        order = str(rng.choice(["char_count", "count_char"]))
        fmt_desc = ("'<char><count>' (character then count)"
                    if order == "char_count"
                    else "'<count><char>' (count then character)")
        spec = (f"takes a string and run-length encodes ONLY runs of length "
                f">= {min_run}: such runs become {fmt_desc}, shorter runs are "
                f"copied verbatim")
        def ref(text, min_run=min_run, order=order):
            out, i = [], 0
            while i < len(text):
                j = i
                while j < len(text) and text[j] == text[i]:
                    j += 1
                run = j - i
                if run >= min_run:
                    out.append(f"{text[i]}{run}" if order == "char_count"
                               else f"{run}{text[i]}")
                else:
                    out.append(text[i] * run)
                i = j
            return "".join(out)
        tests = []
        for _ in range(7):
            chars = rng.choice(list("abc"), size=int(rng.integers(0, 16)))
            tests.append(("".join(chars),))
    elif kind == 1:
        w = int(rng.integers(2, 13))
        agg = str(rng.choice(["maximum", "minimum"]))
        short = str(rng.choice(["None", "0"]))
        spec = (f"takes a list of integers and returns the {agg} sum over "
                f"all contiguous windows of length {w}; if the list has fewer "
                f"than {w} elements, return {short}")
        agg_fn = max if agg == "maximum" else min
        short_val = None if short == "None" else 0
        def ref(xs, w=w, agg_fn=agg_fn, short_val=short_val):
            if len(xs) < w:
                return short_val
            return agg_fn(sum(xs[i:i + w]) for i in range(len(xs) - w + 1))
        tests = [([int(v) for v in
                   rng.integers(-20, 20, int(rng.integers(0, w + 7)))],)
                 for _ in range(7)]
    else:
        e = int(rng.integers(0, 15))
        touch = str(rng.choice(["touching", "strict"]))
        touch_desc = ("overlapping or exactly touching"
                      if touch == "touching" else
                      "strictly overlapping (sharing more than a single "
                      "boundary point)")
        spec = (f"takes a list of (start, end) integer intervals, expands "
                f"each by {e} on both sides, then repeatedly merges any "
                f"intervals that are {touch_desc}, and returns the merged "
                f"intervals as (start, end) tuples sorted by start")
        def ref(intervals, e=e, touch=touch):
            ivs = sorted([(a - e, b + e) for a, b in intervals])
            out = []
            for a, b in ivs:
                if out and (a <= out[-1][1] if touch == "touching"
                            else a < out[-1][1]):
                    out[-1] = (out[-1][0], max(out[-1][1], b))
                else:
                    out.append((a, b))
            return [tuple(iv) for iv in out]
        tests = []
        for _ in range(6):
            sz = int(rng.integers(0, 6))
            ivs = []
            for _ in range(sz):
                a = int(rng.integers(0, 60))
                ivs.append((a, a + int(rng.integers(0, 10))))
            tests.append((ivs,))
    return spec, ref, tests


def _gen_extreme(rng):
    kind = int(rng.integers(0, 2))
    if kind == 0:
        width = int(rng.integers(6, 14))
        pad = str(rng.choice(["0", "*", "_"]))
        group = int(rng.integers(2, 5))
        sep = str(rng.choice([",", ".", " "]))
        spec = (f"takes a non-negative integer and formats it as follows: "
                f"first write its decimal digits, then group the digits into "
                f"blocks of {group} FROM THE RIGHT and join blocks with '{sep}', "
                f"then left-pad the whole result with '{pad}' to a total "
                f"length of at least {width} characters")
        def ref(x, width=width, pad=pad, group=group, sep=sep):
            ds = str(x)
            blocks = []
            i = len(ds)
            while i > 0:
                blocks.append(ds[max(0, i - group):i])
                i -= group
            s = sep.join(reversed(blocks))
            return s.rjust(width, pad)
        tests = [(int(v),) for v in
                 [0, 7, int(rng.integers(10, 999)), int(rng.integers(1000, 99999)),
                  int(rng.integers(100000, 99999999)), int(rng.integers(10, 9999))]]
    else:
        keep = int(rng.integers(1, 6))
        vowels = "aeiou"
        mode = str(rng.choice(["upper", "swap"]))
        joiner = str(rng.choice([" ", "-"]))
        spec = (f"takes a lowercase string and processes words (separated by "
                f"single spaces) as follows: for each word, keep only its "
                f"first {keep} consonants (drop vowels '{vowels}' and any "
                f"consonants beyond the first {keep}); then "
                + ("uppercase the ENTIRE result of each word"
                   if mode == "upper" else
                   "uppercase only the LAST character of each non-empty word")
                + f"; join the processed words with '{joiner}' (words may "
                  f"become empty; keep their positions)")
        def ref(text, keep=keep, mode=mode, joiner=joiner):
            out_words = []
            for word in text.split(" "):
                cons = [c for c in word if c not in vowels][:keep]
                w = "".join(cons)
                if mode == "upper":
                    w = w.upper()
                elif w:
                    w = w[:-1] + w[-1].upper()
                out_words.append(w)
            return joiner.join(out_words)
        words = ["banana", "crypt", "stream", "oat", "lynx", "queue",
                 "rhythm", "aide", "frost", "glove"]
        tests = []
        for _ in range(6):
            sz = int(rng.integers(1, 5))
            picks = list(rng.choice(len(words), size=sz, replace=False))
            tests.append((" ".join(words[i] for i in picks),))
    return spec, ref, tests


_GENERATORS = {
    "simple": _gen_simple,
    "medium": _gen_medium,
    "complex": _gen_complex,
    "extreme": _gen_extreme,
}


def _prompt_text(spec: str) -> str:
    return (f"Write a Python function named `{FUNC_NAME}` that {spec}.\n\n"
            f"Return only the Python code for the function, with no "
            f"explanation, no example usage, and no printing.")


class DiverseCodeDataset:
    """Parametrized code problems at one difficulty level."""

    def __init__(self, n_prompts: int = 80, complexity: str = "medium",
                 seed: int = 42):
        self.n_prompts = n_prompts
        self.complexity = complexity
        self.seed = seed
        self.prompts = self._generate()

    def _generate(self):
        rng = np.random.default_rng(self.seed)
        gen = _GENERATORS[self.complexity]
        prompts, seen, attempts = [], set(), 0
        while len(prompts) < self.n_prompts and attempts < self.n_prompts * 200:
            attempts += 1
            spec, ref, tests = gen(rng)
            text = _prompt_text(spec)
            # Dedupe on TEXT: at temperature=0 identical text means an
            # identical (deterministic) trial.
            if text in seen:
                continue
            seen.add(text)
            expected = [ref(*args) for args in tests]
            prompts.append(Prompt(
                id=f"diverse_code_{self.complexity}_{len(prompts):04d}",
                text=text,
                metadata={
                    "complexity": self.complexity,
                    "tests": tests,
                    "expected": expected,
                },
            ))
        if len(prompts) < self.n_prompts:
            raise ValueError(
                f"Only {len(prompts)} unique prompts for '{self.complexity}'")
        return prompts

    def get_all_prompts(self):
        return self.prompts.copy()

    def __len__(self):
        return len(self.prompts)


class StratifiedDiverseCodeDataset:
    """Four difficulty strata of parametrized code problems."""

    STRATA = ["simple", "medium", "complex", "extreme"]
    STRATUM_SEED_OFFSETS = {"simple": 0, "medium": 1000,
                            "complex": 2000, "extreme": 3000}

    def __init__(self, prompts_per_stratum: int = 80, seed: int = 42):
        self.prompts_per_stratum = prompts_per_stratum
        self.seed = seed
        self.datasets = {
            s: DiverseCodeDataset(
                n_prompts=prompts_per_stratum,
                complexity=s,
                seed=seed + self.STRATUM_SEED_OFFSETS[s],
            )
            for s in self.STRATA
        }

    def get_stratum_prompts(self, stratum: str):
        return self.datasets[stratum].get_all_prompts()

    def get_all_prompts(self):
        return [p for s in self.STRATA for p in self.datasets[s].get_all_prompts()]

    def __len__(self):
        return sum(len(d) for d in self.datasets.values())
