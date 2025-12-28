"""SQL query generation prompts.

Generates diverse SQL query prompts for testing LLM SQL generation capabilities.
Covers various SQL features: SELECT, JOIN, GROUP BY, subqueries, CTEs, etc.
"""

import random
import hashlib
from typing import List
import numpy as np
from eval_harness.core.types import Prompt


class SQLPromptGenerator:
    """Generates diverse SQL query prompts."""

    def __init__(self, seed: int = 42):
        """Initialize prompt generator.

        Args:
            seed: Random seed for reproducibility
        """
        self.rng = random.Random(seed)

    def generate_prompts(self, n: int = 100) -> List[str]:
        """Generate n diverse SQL prompts.

        Args:
            n: Number of prompts to generate

        Returns:
            List of SQL query prompts
        """
        # Define prompt templates by category
        templates = {
            'basic_select': self._basic_select_templates(),
            'joins': self._join_templates(),
            'aggregates': self._aggregate_templates(),
            'subqueries': self._subquery_templates(),
            'ctes': self._cte_templates(),
            'window_functions': self._window_function_templates(),
            'complex': self._complex_templates(),
        }

        # Calculate number of prompts per category
        categories = list(templates.keys())
        prompts_per_category = n // len(categories)
        remainder = n % len(categories)

        prompts = []

        # Generate prompts from each category
        for i, category in enumerate(categories):
            category_templates = templates[category]
            count = prompts_per_category + (1 if i < remainder else 0)

            # Sample with replacement if needed
            for _ in range(count):
                template = self.rng.choice(category_templates)
                prompts.append(template)

        # Shuffle to mix categories
        self.rng.shuffle(prompts)

        return prompts

    def _basic_select_templates(self) -> List[str]:
        """Basic SELECT query templates."""
        return [
            "Write a SQL query to select all columns from the 'users' table.",
            "Write a SQL query to select the 'name' and 'email' columns from the 'customers' table.",
            "Write a SQL query to select distinct 'country' values from the 'orders' table.",
            "Write a SQL query to select all products where price is greater than 100.",
            "Write a SQL query to select employees with salary between 50000 and 100000.",
            "Write a SQL query to select the first 10 rows from the 'transactions' table.",
            "Write a SQL query to select all orders placed in 2024.",
            "Write a SQL query to find all users whose name starts with 'A'.",
            "Write a SQL query to select products ordered by price in descending order.",
            "Write a SQL query to count the total number of customers.",
        ]

    def _join_templates(self) -> List[str]:
        """JOIN query templates."""
        return [
            "Write a SQL query to join 'orders' and 'customers' tables on customer_id.",
            "Write a SQL query to find all orders with customer names using INNER JOIN.",
            "Write a SQL query to left join 'employees' and 'departments' tables.",
            "Write a SQL query to find customers who have never placed an order (LEFT JOIN).",
            "Write a SQL query to join three tables: orders, customers, and products.",
            "Write a SQL query to find employees and their managers using a self-join.",
            "Write a SQL query to find all possible combinations of products and categories (CROSS JOIN).",
            "Write a SQL query to right join 'sales' and 'regions' tables.",
            "Write a SQL query to find matching records between 'table_a' and 'table_b' on id.",
            "Write a SQL query to join 'students' and 'courses' through an enrollment junction table.",
        ]

    def _aggregate_templates(self) -> List[str]:
        """Aggregate function templates."""
        return [
            "Write a SQL query to calculate the average salary by department.",
            "Write a SQL query to find the total revenue for each product category.",
            "Write a SQL query to count the number of orders per customer.",
            "Write a SQL query to find the maximum and minimum prices in the products table.",
            "Write a SQL query to calculate the sum of sales grouped by year and month.",
            "Write a SQL query to find the top 5 customers by total order value.",
            "Write a SQL query to count distinct users who made purchases in 2024.",
            "Write a SQL query to find departments with more than 10 employees.",
            "Write a SQL query to calculate the average order value by customer segment.",
            "Write a SQL query to find the median salary (using percentile functions).",
        ]

    def _subquery_templates(self) -> List[str]:
        """Subquery templates."""
        return [
            "Write a SQL query to find customers whose total spending is above average.",
            "Write a SQL query to find employees who earn more than their department average.",
            "Write a SQL query to select products that have never been ordered (using NOT IN).",
            "Write a SQL query to find the second highest salary using a subquery.",
            "Write a SQL query to find customers who ordered the most expensive product.",
            "Write a SQL query to find departments where all employees earn over 50000 (using ALL).",
            "Write a SQL query to find orders larger than any order from customer 'ABC' (using ANY).",
            "Write a SQL query to find employees in departments with over 100 total salary spend.",
            "Write a SQL query to select products with above-median prices using a subquery.",
            "Write a SQL query to find customers who have ordered every product (division).",
        ]

    def _cte_templates(self) -> List[str]:
        """Common Table Expression (CTE) templates."""
        return [
            "Write a SQL query using a CTE to calculate running totals of sales.",
            "Write a SQL query with a CTE to find the top 10 customers by revenue.",
            "Write a SQL query using multiple CTEs to analyze customer purchase patterns.",
            "Write a SQL query with a recursive CTE to generate a sequence from 1 to 100.",
            "Write a SQL query using a CTE to calculate year-over-year growth rates.",
            "Write a SQL query with a CTE to find employees and their reporting hierarchy.",
            "Write a SQL query using CTEs to compute intermediate aggregations before final query.",
            "Write a SQL query with a CTE to deduplicate records based on timestamp.",
            "Write a SQL query using a recursive CTE to traverse a tree structure.",
            "Write a SQL query with CTEs to calculate customer lifetime value.",
        ]

    def _window_function_templates(self) -> List[str]:
        """Window function templates."""
        return [
            "Write a SQL query using ROW_NUMBER() to rank employees by salary within each department.",
            "Write a SQL query using RANK() to find the top 3 products by sales in each category.",
            "Write a SQL query using LAG() to calculate the difference from the previous month's sales.",
            "Write a SQL query using LEAD() to compare current and next quarter revenue.",
            "Write a SQL query using SUM() OVER() to calculate running totals.",
            "Write a SQL query using AVG() OVER() to compute moving averages over 7 days.",
            "Write a SQL query using DENSE_RANK() to assign ranks without gaps.",
            "Write a SQL query using NTILE() to divide customers into quartiles by spending.",
            "Write a SQL query using FIRST_VALUE() and LAST_VALUE() to compare against period boundaries.",
            "Write a SQL query using PERCENT_RANK() to find percentile rankings of sales.",
        ]

    def _complex_templates(self) -> List[str]:
        """Complex multi-feature query templates."""
        return [
            "Write a SQL query to find the top 5 products by revenue for each category, with month-over-month growth.",
            "Write a SQL query combining CTEs, window functions, and joins to analyze customer cohort retention.",
            "Write a SQL query to calculate the percentage of total sales for each product within its category.",
            "Write a SQL query to find customers who made purchases in consecutive months (using window functions).",
            "Write a SQL query to identify gaps in sequential order numbers using LEAD().",
            "Write a SQL query to pivot monthly sales data into columns (using CASE and aggregates).",
            "Write a SQL query to find the longest streak of daily active users.",
            "Write a SQL query to calculate customer churn rate by cohort using window functions.",
            "Write a SQL query to find products that are frequently bought together (market basket analysis).",
            "Write a SQL query to calculate the median, 25th, and 75th percentiles of prices by category.",
            "Write a SQL query to find employees who have been in the same department for over 5 years.",
            "Write a SQL query to identify outliers in sales data (values more than 2 standard deviations from mean).",
            "Write a SQL query to calculate the average time between repeat purchases for each customer.",
            "Write a SQL query to find the top 10% of customers by lifetime value within each region.",
            "Write a SQL query to analyze seasonal trends by comparing same month across years.",
            "Write a SQL query to find products with declining sales over the last 3 months.",
            "Write a SQL query to calculate the conversion funnel metrics at each stage.",
            "Write a SQL query to identify duplicate records based on multiple columns with fuzzy matching.",
            "Write a SQL query to calculate the weighted average rating for each product.",
            "Write a SQL query to find the busiest hour of the day for each day of the week.",
        ]


def get_sql_prompts(n: int = 100, seed: int = 42) -> List[str]:
    """Convenience function to generate SQL prompts.

    Args:
        n: Number of prompts to generate
        seed: Random seed for reproducibility

    Returns:
        List of SQL query prompts
    """
    generator = SQLPromptGenerator(seed=seed)
    return generator.generate_prompts(n)


class SQLPromptDataset:
    """Dataset wrapper for SQL prompts compatible with eval harness."""

    def __init__(self, n_prompts: int = 100, seed: int = 42):
        """Initialize SQL prompt dataset.

        Args:
            n_prompts: Number of prompts to generate
            seed: Random seed for reproducibility
        """
        self.n_prompts = n_prompts
        self.seed = seed
        # Generate prompt strings
        prompt_strings = get_sql_prompts(n=n_prompts, seed=seed)
        # Convert to Prompt objects
        self.prompts = [
            Prompt(
                id=hashlib.sha256(prompt_str.encode()).hexdigest()[:12],
                text=prompt_str,
                metadata={'task': 'sql_generation', 'index': i}
            )
            for i, prompt_str in enumerate(prompt_strings)
        ]

    def __len__(self) -> int:
        """Return number of prompts."""
        return len(self.prompts)

    def __getitem__(self, idx: int) -> Prompt:
        """Get prompt at index.

        Returns:
            Prompt object
        """
        return self.prompts[idx]

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        """Sample a random prompt uniformly.

        Args:
            rng: NumPy random generator

        Returns:
            Prompt object
        """
        idx = rng.integers(0, len(self.prompts))
        return self.prompts[idx]

    def get_all_prompts(self) -> List[Prompt]:
        """Return all prompts as a list.

        Returns:
            List of Prompt objects
        """
        return self.prompts.copy()
