# tests/test_logic.py
import unittest
# Import all necessary components from the structured library
from tools import var, def_pred, print_truth_table
from logic_core.base_expressions import Constant, Variable
from logic_core.connectives import Not, And, Or, Implies, Iff
from logic_core.quantifiers import ForAll, Exists, Predicate

class TestLogicalFramework(unittest.TestCase):

    def setUp(self):
        """Set up common variables and predicates for tests."""
        self.p = var("P")
        self.q = var("Q")
        self.context = {"P": True, "Q": False}
        self.x = var("x")
        self.is_even = def_pred("IsEven", lambda n: n % 2 == 0)

    # --- Basic Expression Tests ---

    def test_constants(self):
        self.assertTrue(Constant(True).evaluate({}))
        self.assertFalse(Constant(False).evaluate({}))

    def test_variable(self):
        self.assertTrue(self.p.evaluate(self.context))
        self.assertFalse(self.q.evaluate(self.context))
        with self.assertRaises(ValueError):
            var("Z").evaluate(self.context) # Variable not in context

    # --- Propositional Connective Tests ---

    def test_not(self):
        self.assertFalse((~self.p).evaluate(self.context))
        self.assertTrue((~self.q).evaluate(self.context))

    def test_and(self):
        # T & F = F
        self.assertFalse((self.p & self.q).evaluate(self.context))
        # T & T = T
        self.assertTrue((self.p & Constant(True)).evaluate(self.context))

    def test_implies(self):
        # T -> F = F (The only way implication is false)
        self.assertFalse((self.p >> self.q).evaluate(self.context))
        # F -> T = T
        self.assertTrue((self.q >> self.p).evaluate(self.context))

    def test_iff(self):
        # T <=> F = F
        self.assertFalse((self.p == self.q).evaluate(self.context))
        # F <=> F = T
        self.assertTrue((self.q == Constant(False)).evaluate(self.context))

    # --- Predicate and Quantifier Tests ---

    def test_predicate_evaluation(self):
        # IsEven(4) -> True
        expr = self.is_even(Constant(4))
        self.assertTrue(expr.evaluate({}))
        # IsEven(3) -> False
        expr = self.is_even(Constant(3))
        self.assertFalse(expr.evaluate({}))

    def test_universal_quantifier(self):
        D_true = [2, 4, 6]
        D_false = [2, 3, 4] # 3 is not even

        # ForAll(x, IsEven(x), [2, 4, 6]) -> True
        self.assertTrue(ForAll(self.x, self.is_even(self.x), D_true).evaluate({}))
        # ForAll(x, IsEven(x), [2, 3, 4]) -> False
        self.assertFalse(ForAll(self.x, self.is_even(self.x), D_false).evaluate({}))

    def test_existential_quantifier(self):
        D_true = [1, 3, 6] # 6 is even
        D_false = [1, 3, 5] # No even numbers

        # Exists(x, IsEven(x), [1, 3, 6]) -> True
        self.assertTrue(Exists(self.x, self.is_even(self.x), D_true).evaluate({}))
        # Exists(x, IsEven(x), [1, 3, 5]) -> False
        self.assertFalse(Exists(self.x, self.is_even(self.x), D_false).evaluate({}))


if __name__ == '__main__':
    # Run the tests
    # In a terminal, navigate to the Logic_Engine_Project folder and run:
    # python -m unittest tests.test_logic 
    unittest.main(argv=['first-arg-is-ignored'], exit=False)