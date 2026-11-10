import unittest
from src.intervals import merge_intervals

class IntervalTests(unittest.TestCase):
    def test_disjoint(self):
        self.assertEqual([tuple(x) for x in merge_intervals([(4, 5), (1, 2)])], [(1, 2), (4, 5)])

if __name__ == "__main__":
    unittest.main()
