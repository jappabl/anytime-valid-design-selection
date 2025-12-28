"""SQL syntax validator using sqlparse.

Validates whether generated SQL queries are syntactically correct.
Uses sqlparse library to parse SQL statements.
"""

import re
from typing import Optional, Any
import sqlparse
from sqlparse import sql
from eval_harness.core.types import ValidationResult


class SQLValidator:
    """Validates SQL query syntax.

    A SQL query is considered valid if:
    1. It parses without errors using sqlparse
    2. It contains at least one statement
    3. It contains valid SQL keywords (SELECT, INSERT, UPDATE, DELETE, etc.)
    """

    def __init__(self):
        """Initialize SQL validator."""
        pass

    def validate(self, generation: str, sample_id: str, **kwargs: Any) -> ValidationResult:
        """Validate SQL syntax.

        Args:
            generation: The generated SQL query to validate
            sample_id: Unique identifier for this sample
            **kwargs: Additional arguments (ignored for SQL validation)

        Returns:
            ValidationResult with pass/fail status and error message if failed
        """
        # Extract SQL from response (handle markdown code blocks)
        sql_query = self._extract_sql(generation)

        if not sql_query:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="No SQL query found in response"
            )

        # Parse the SQL
        try:
            parsed = sqlparse.parse(sql_query)
        except Exception as e:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode=f"Parse error: {str(e)}"
            )

        if not parsed:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="Empty SQL statement"
            )

        # Check for at least one valid statement
        if len(parsed) == 0:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="No SQL statements found"
            )

        # Check first statement contains SQL keywords
        first_stmt = parsed[0]
        has_keyword = self._has_sql_keyword(first_stmt)

        if not has_keyword:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="No valid SQL keywords found"
            )

        # Additional validation: check for obvious syntax errors
        # sqlparse is permissive, so we add some heuristics
        error = self._check_common_errors(sql_query, first_stmt)
        if error:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode=error
            )

        return ValidationResult(
            sample_id=sample_id,
            passed=True,
            failure_mode=None
        )

    def _extract_sql(self, response: str) -> str:
        """Extract SQL query from response.

        Handles:
        - Plain SQL queries
        - SQL wrapped in ```sql ... ``` markdown code blocks
        - SQL wrapped in ``` ... ``` code blocks
        """
        response = response.strip()

        # Check for markdown code blocks
        # Pattern: ```sql\n...\n``` or ```\n...\n```
        code_block_pattern = r'```(?:sql)?\s*\n(.*?)\n```'
        match = re.search(code_block_pattern, response, re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(1).strip()

        # No code block, assume entire response is SQL
        return response

    def _has_sql_keyword(self, stmt: sql.Statement) -> bool:
        """Check if statement contains valid SQL keywords."""
        # Get all tokens
        tokens = list(stmt.flatten())

        # Look for SQL keywords
        sql_keywords = {
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP',
            'ALTER', 'TRUNCATE', 'WITH', 'MERGE', 'REPLACE'
        }

        for token in tokens:
            if token.ttype in sqlparse.tokens.Keyword:
                if token.value.upper() in sql_keywords:
                    return True

        return False

    def _check_common_errors(self, sql_query: str, stmt: sql.Statement) -> Optional[str]:
        """Check for common SQL syntax errors that sqlparse might miss.

        Returns error message if found, None otherwise.
        """
        # Check for unbalanced parentheses
        if sql_query.count('(') != sql_query.count(')'):
            return "Unbalanced parentheses"

        # Check for unbalanced quotes
        # Simple check: even number of unescaped single/double quotes
        single_quotes = len(re.findall(r"(?<!\\)'", sql_query))
        double_quotes = len(re.findall(r'(?<!\\)"', sql_query))

        if single_quotes % 2 != 0:
            return "Unbalanced single quotes"
        if double_quotes % 2 != 0:
            return "Unbalanced double quotes"

        # Check for completely empty statement (only whitespace/comments)
        non_comment_tokens = [t for t in stmt.flatten()
                             if t.ttype not in (sqlparse.tokens.Comment.Single,
                                               sqlparse.tokens.Comment.Multiline,
                                               sqlparse.tokens.Whitespace,
                                               sqlparse.tokens.Newline)]

        if not non_comment_tokens:
            return "Statement contains only comments/whitespace"

        return None


class SQLValidatorFactory:
    """Factory for creating SQL validators."""

    @staticmethod
    def create() -> SQLValidator:
        """Create SQL validator instance."""
        return SQLValidator()
