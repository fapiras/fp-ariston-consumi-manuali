"""Self-contained parser tests without a Home Assistant installation."""
import ast
import math
import unittest
from pathlib import Path

SOURCE = Path(__file__).parents[1] / "custom_components/fp_ariston_consumi/reader.py"
MODULE = ast.parse(SOURCE.read_text(encoding="utf-8"))
func = next(node for node in MODULE.body if isinstance(node, ast.FunctionDef) and node.name == "parse_period_report")
code = compile(ast.Module(body=[func], type_ignores=[]), str(SOURCE), "exec")
scope = {"Any": object, "PERIOD_KEYS": ("day_kwh", "week_kwh", "month_kwh", "year_kwh"), "math": math}
exec(code, scope)
parse = scope["parse_period_report"]

class ParserTests(unittest.TestCase):
    def test_valid(self):
        data = [{"v": [0.3, 0.2]}, {"v": [1, 2]}, {"v": [5, 10]}, {"v": [100, 200]}]
        self.assertEqual(parse(data), {"day_kwh": 0.5, "week_kwh": 3.0, "month_kwh": 15.0, "year_kwh": 300.0})

    def test_missing_period(self):
        with self.assertRaises(ValueError):
            parse([{"v": [1]}])

    def test_invalid_nan(self):
        with self.assertRaises(ValueError):
            parse([{"v": [math.nan]}] * 4)

    def test_invalid_negative(self):
        with self.assertRaises(ValueError):
            parse([{"v": [-3]}] * 4)

    def test_invalid_boolean(self):
        with self.assertRaises(ValueError):
            parse([{"v": [True]}] * 4)

    def test_invalid_empty(self):
        with self.assertRaises(ValueError):
            parse([{"v": []}] * 4)

    def test_null_filtered(self):
        self.assertEqual(parse([{"v": [None, 1]}] * 4)["month_kwh"], 1.0)

if __name__ == "__main__":
    unittest.main()
