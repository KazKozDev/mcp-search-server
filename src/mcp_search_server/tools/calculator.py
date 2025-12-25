"""
Calculator tool for mathematical computations.
Supports basic arithmetic, trigonometry, logarithms, and more.
"""

import re
import ast
import math
import asyncio
import operator
from typing import Union, Dict, Any


class Calculator:
    """Calculator for safe mathematical operations with MCP support."""

    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Math constants
    CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        "inf": math.inf,
        "nan": math.nan,
    }

    # Safe math functions
    MATH_FUNCTIONS = {
        # Basic functions
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        # Power and logarithmic functions
        "sqrt": math.sqrt,
        "pow": math.pow,
        "exp": math.exp,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        # Trigonometric functions
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "atan2": math.atan2,
        # Hyperbolic functions
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        "asinh": math.asinh,
        "acosh": math.acosh,
        "atanh": math.atanh,
        # Angular conversion
        "degrees": math.degrees,
        "radians": math.radians,
        # Other functions
        "ceil": math.ceil,
        "floor": math.floor,
        "factorial": math.factorial,
        "gcd": math.gcd,
        "lcm": math.lcm,
    }

    def __init__(self):
        """Initialize calculator."""
        pass

    def _preprocess_expression(self, expression: str) -> str:
        """
        Preprocess expression to handle special cases.

        Args:
            expression: Raw mathematical expression

        Returns:
            Preprocessed expression
        """
        # Remove all whitespace
        expression = expression.replace(" ", "")

        # Handle implicit multiplication for parentheses
        # )(  -> )*(
        expression = re.sub(r"\)\(", r")*(", expression)
        # )digit -> )*digit
        expression = re.sub(r"\)(\d)", r")*\1", expression)

        # digit( -> digit*( BUT only if not part of function name like log10(
        # We need to check what's before the digit
        def replace_digit_paren(match):
            start = match.start()
            # Check if this digit is part of a function name
            for func_name in self.MATH_FUNCTIONS.keys():
                if func_name[-1].isdigit():
                    # Function ends with digit (log10, log2)
                    func_start = start - len(func_name) + 1
                    if func_start >= 0 and expression[func_start : start + 1] == func_name:
                        return match.group(0)  # Don't modify
            return match.group(1) + "*("

        expression = re.sub(r"(\d)\(", replace_digit_paren, expression)

        # Handle implicit multiplication for constants only (e.g., 2pi -> 2*pi)
        for const_name in self.CONSTANTS.keys():
            expression = re.sub(rf"(\d)({const_name})(?!\w)", r"\1*\2", expression)
            expression = re.sub(rf"({const_name})(\d)", r"\1*\2", expression)

        return expression

    def _safe_eval(self, expression: str) -> Union[int, float]:
        """
        Safely evaluate mathematical expressions.

        Args:
            expression: Mathematical expression as string

        Returns:
            Result of calculation

        Raises:
            ValueError: If expression is invalid or unsafe
        """
        # Preprocess the expression
        expression = self._preprocess_expression(expression)

        try:
            # Parse the expression into AST
            node = ast.parse(expression, mode="eval")

            # Evaluate the expression safely
            result = self._eval_node(node.body)

            return result

        except Exception as e:
            raise ValueError(f"Error in expression '{expression}': {str(e)}")

    def _eval_node(self, node):
        """Recursively evaluate AST nodes."""
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        elif isinstance(node, ast.Name):
            # Handle constants
            if node.id in self.CONSTANTS:
                return self.CONSTANTS[node.id]
            raise ValueError(f"Unknown variable: {node.id}")
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op = self.OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op = self.OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            return op(operand)
        elif isinstance(node, ast.Call):
            # Handle function calls
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name not in self.MATH_FUNCTIONS:
                    raise ValueError(f"Unsupported function: {func_name}")

                func = self.MATH_FUNCTIONS[func_name]
                args = [self._eval_node(arg) for arg in node.args]

                return func(*args)
            else:
                raise ValueError("Complex function calls not supported")
        else:
            raise ValueError(f"Unsupported operation: {type(node).__name__}")

    def calculate(self, expression: str) -> str:
        """
        Perform calculation and return result as string.

        Args:
            expression: Mathematical expression

        Returns:
            Calculation result or error message
        """
        try:
            if not expression or not isinstance(expression, str):
                return "Error: Empty expression or wrong data type"

            result = self._safe_eval(expression)

            # Format result nicely
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                elif abs(result) < 1e-10:  # Very small numbers
                    result = 0
                else:
                    # Round to reasonable precision
                    result = round(result, 10)

            return f"{expression} = {result}"

        except ValueError as e:
            return f"Error: {str(e)}"
        except ZeroDivisionError:
            return "Error: Division by zero"
        except Exception as e:
            return f"Error: {str(e)}"

    async def calculate_async(self, expression: str) -> Dict[str, Any]:
        """
        Async wrapper for calculation with detailed results.

        Args:
            expression: Mathematical expression

        Returns:
            Dictionary with result and metadata
        """
        try:
            if not expression or not isinstance(expression, str):
                return {
                    "success": False,
                    "expression": expression,
                    "result": None,
                    "error": "Empty expression or wrong data type",
                }

            # Run calculation in thread pool to avoid blocking
            result = await asyncio.to_thread(self._safe_eval, expression)

            # Format result
            formatted_result = result
            if isinstance(result, float):
                if result.is_integer():
                    formatted_result = int(result)
                elif abs(result) < 1e-10:
                    formatted_result = 0
                else:
                    formatted_result = round(result, 10)

            return {
                "success": True,
                "expression": expression,
                "result": formatted_result,
                "formatted": f"{expression} = {formatted_result}",
                "type": type(formatted_result).__name__,
                "error": None,
            }

        except ValueError as e:
            return {"success": False, "expression": expression, "result": None, "error": str(e)}
        except ZeroDivisionError:
            return {
                "success": False,
                "expression": expression,
                "result": None,
                "error": "Division by zero",
            }
        except Exception as e:
            return {"success": False, "expression": expression, "result": None, "error": str(e)}


# Create a global instance
calculator = Calculator()
