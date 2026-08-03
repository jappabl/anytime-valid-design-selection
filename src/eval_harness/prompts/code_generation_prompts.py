"""Code generation prompts for real-LLM validation.

Task: Generate Python functions that pass provided unit tests.
Designed to achieve ~10-20% failure rates on GPT-4o-mini.

Difficulty progression (targeting overall p≈0.15):
- Simple: Basic list/string operations → p≈0.05
- Medium: Data transformations, edge cases → p≈0.12
- Complex: Algorithms with multiple conditions → p≈0.20
- Extreme: Complex algorithms, edge cases → p≈0.30
"""

from typing import Literal
import numpy as np

from eval_harness.core.types import Prompt


class CodeGenerationDataset:
    """Code generation prompts with test cases."""

    def __init__(
        self,
        n_prompts: int = 100,
        complexity: Literal["simple", "medium", "complex", "extreme"] = "medium",
        seed: int = 42,
    ):
        self.n_prompts = n_prompts
        self.complexity = complexity
        self.seed = seed
        self.prompts = self._generate_prompts()

    def _generate_prompts(self) -> list[Prompt]:
        rng = np.random.default_rng(self.seed)
        prompts = []

        for i in range(self.n_prompts):
            problem, tests, solution = self._generate_problem(i, rng)
            prompt_text = self._create_prompt_text(problem, tests)

            prompts.append(
                Prompt(
                    id=f"code_{self.complexity}_{i:04d}",
                    text=prompt_text,
                    metadata={
                        "problem": problem,
                        "tests": tests,
                        "solution": solution,
                        "complexity": self.complexity,
                    },
                )
            )

        return prompts

    def _generate_problem(self, idx: int, rng: np.random.Generator) -> tuple[str, str, str]:
        if self.complexity == "simple":
            return self._generate_simple_problem(idx, rng)
        elif self.complexity == "medium":
            return self._generate_medium_problem(idx, rng)
        elif self.complexity == "complex":
            return self._generate_complex_problem(idx, rng)
        else:
            return self._generate_extreme_problem(idx, rng)

    def _generate_simple_problem(self, idx: int, rng: np.random.Generator) -> tuple[str, str, str]:
        """Simple: Basic operations."""

        problems = [
            (
                "Write a function `reverse_string(s)` that returns the reverse of string s.",
                """assert reverse_string("hello") == "olleh"
assert reverse_string("") == ""
assert reverse_string("a") == "a"
assert reverse_string("12345") == "54321\"""",
                "def reverse_string(s):\n    return s[::-1]"
            ),
            (
                "Write a function `sum_list(nums)` that returns the sum of a list of numbers.",
                """assert sum_list([1, 2, 3]) == 6
assert sum_list([]) == 0
assert sum_list([-1, 1]) == 0
assert sum_list([10]) == 10""",
                "def sum_list(nums):\n    return sum(nums)"
            ),
            (
                "Write a function `count_vowels(s)` that counts vowels (a,e,i,o,u) in a string.",
                """assert count_vowels("hello") == 2
assert count_vowels("") == 0
assert count_vowels("aeiou") == 5
assert count_vowels("xyz") == 0""",
                "def count_vowels(s):\n    return sum(1 for c in s.lower() if c in 'aeiou')"
            ),
        ]

        choice = rng.integers(0, len(problems))
        return problems[choice]

    def _generate_medium_problem(self, idx: int, rng: np.random.Generator) -> tuple[str, str, str]:
        """Medium: Data transformations with edge cases."""

        problems = [
            (
                "Write a function `group_by_length(words)` that groups a list of words by their length. Return a dict where keys are lengths and values are lists of words with that length.",
                """assert group_by_length(["a", "bb", "ccc", "dd"]) == {1: ["a"], 2: ["bb", "dd"], 3: ["ccc"]}
assert group_by_length([]) == {}
assert group_by_length(["hello"]) == {5: ["hello"]}
assert group_by_length(["cat", "dog", "rat"]) == {3: ["cat", "dog", "rat"]}""",
                """def group_by_length(words):
    result = {}
    for word in words:
        length = len(word)
        if length not in result:
            result[length] = []
        result[length].append(word)
    return result"""
            ),
            (
                "Write a function `remove_duplicates(nums)` that removes duplicates from a list while preserving order. Return a new list.",
                """assert remove_duplicates([1, 2, 2, 3, 1]) == [1, 2, 3]
assert remove_duplicates([]) == []
assert remove_duplicates([1, 1, 1]) == [1]
assert remove_duplicates([1, 2, 3]) == [1, 2, 3]""",
                """def remove_duplicates(nums):
    seen = set()
    result = []
    for num in nums:
        if num not in seen:
            seen.add(num)
            result.append(num)
    return result"""
            ),
        ]

        choice = rng.integers(0, len(problems))
        return problems[choice]

    def _generate_complex_problem(self, idx: int, rng: np.random.Generator) -> tuple[str, str, str]:
        """Complex: Algorithms with conditions."""

        problem = (
            "Write a function `find_pairs_with_sum(nums, target)` that finds all pairs of indices (i, j) where i < j and nums[i] + nums[j] == target. Return a list of tuples.",
            """assert find_pairs_with_sum([1, 2, 3, 4], 5) == [(0, 3), (1, 2)]
assert find_pairs_with_sum([1, 1, 1], 2) == [(0, 1), (0, 2), (1, 2)]
assert find_pairs_with_sum([1, 2, 3], 10) == []
assert find_pairs_with_sum([], 5) == []
assert find_pairs_with_sum([5], 10) == []""",
            """def find_pairs_with_sum(nums, target):
    pairs = []
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                pairs.append((i, j))
    return pairs"""
        )

        return problem

    def _generate_extreme_problem(self, idx: int, rng: np.random.Generator) -> tuple[str, str, str]:
        """Extreme: Complex algorithms."""

        problem = (
            "Write a function `longest_increasing_subsequence(nums)` that returns the length of the longest strictly increasing subsequence. For example, in [10,9,2,5,3,7,101,18], one LIS is [2,3,7,101] with length 4.",
            """assert longest_increasing_subsequence([10,9,2,5,3,7,101,18]) == 4
assert longest_increasing_subsequence([0,1,0,3,2,3]) == 4
assert longest_increasing_subsequence([7,7,7,7,7,7,7]) == 1
assert longest_increasing_subsequence([]) == 0
assert longest_increasing_subsequence([1]) == 1
assert longest_increasing_subsequence([1,2,3,4,5]) == 5""",
            """def longest_increasing_subsequence(nums):
    if not nums:
        return 0
    dp = [1] * len(nums)
    for i in range(1, len(nums)):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)"""
        )

        return problem

    def _create_prompt_text(self, problem: str, tests: str) -> str:
        return f"""{problem}

Your function must pass these test cases:
```python
{tests}
```

Generate ONLY the Python function definition. Do not include test code, explanations, or any other text."""

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        idx = rng.integers(0, len(self.prompts))
        return self.prompts[idx]

    def get_all_prompts(self) -> list[Prompt]:
        return self.prompts.copy()

    def __len__(self) -> int:
        return len(self.prompts)

    def __getitem__(self, idx: int) -> Prompt:
        return self.prompts[idx]


class StratifiedCodeDataset:
    """Code generation prompts stratified by difficulty."""

    def __init__(
        self,
        prompts_per_stratum: int = 25,
        seed: int = 42,
        strata: list[Literal["simple", "medium", "complex", "extreme"]] = None,
    ):
        self.prompts_per_stratum = prompts_per_stratum
        self.seed = seed
        self.strata = strata or ["simple", "medium", "complex", "extreme"]
        self.stratum_prompts: dict[str, list[Prompt]] = {}
        self._generate_stratified_prompts()
        self.all_prompts = []
        for stratum in self.strata:
            self.all_prompts.extend(self.stratum_prompts[stratum])

    def _generate_stratified_prompts(self):
        SEED_OFFSETS = {"simple": 0, "medium": 1000, "complex": 2000, "extreme": 3000}
        for stratum in self.strata:
            stratum_seed = self.seed + SEED_OFFSETS[stratum]
            dataset = CodeGenerationDataset(
                n_prompts=self.prompts_per_stratum,
                complexity=stratum,
                seed=stratum_seed,
            )
            self.stratum_prompts[stratum] = dataset.prompts

    def get_stratum_prompts(self, stratum: str) -> list[Prompt]:
        return self.stratum_prompts[stratum]

    def get_prompt_stratum(self, prompt: Prompt) -> str:
        return prompt.metadata["complexity"]

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        idx = rng.integers(0, len(self.all_prompts))
        return self.all_prompts[idx]

    def get_all_prompts(self) -> list[Prompt]:
        return self.all_prompts.copy()

    def __len__(self) -> int:
        return len(self.all_prompts)

    def __getitem__(self, idx: int) -> Prompt:
        return self.all_prompts[idx]
