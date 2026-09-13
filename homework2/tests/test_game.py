"""PRD 中的路径、关卡和状态约定。测试不依赖图形库。"""

from dataclasses import FrozenInstanceError
import unittest

from game import DIRECTIONS, can_exit, solve_level
from levels import LEVELS, Level, validate_levels


PRD_SOLUTIONS = (
    ((1, 0), (3, 0), (3, 3), (2, 3), (1, 3), (0, 3), (0, 2), (2, 1)),
    ((0, 2), (0, 3), (1, 2), (1, 0), (2, 0), (2, 3), (3, 0), (3, 4),
     (3, 3), (4, 2), (4, 4), (0, 4)),
    ((0, 0), (0, 4), (1, 5), (1, 3), (3, 0), (3, 5), (5, 0), (4, 0),
     (4, 1), (4, 2), (4, 3), (5, 1), (2, 1), (0, 1), (0, 3), (2, 2),
     (2, 4), (5, 2), (5, 3), (5, 4)),
)


class PathTests(unittest.TestCase):
    def test_t07_clear_and_blocked_paths_in_four_directions(self):
        for direction, (dr, dc) in DIRECTIONS.items():
            board = [["."] * 7 for _ in range(7)]
            board[3][3] = direction
            with self.subTest(direction=direction, blocker=None):
                self.assertTrue(can_exit(board, 3, 3))
            for distance in (1, 3):
                for blocker in DIRECTIONS:
                    with self.subTest(direction=direction, distance=distance, blocker=blocker):
                        row, col = 3 + dr * distance, 3 + dc * distance
                        board[row][col] = blocker
                        self.assertFalse(can_exit(board, 3, 3))
                        board[row][col] = "."

    def test_t03_outward_edges_do_not_wrap(self):
        board = [list("LU.R"), list("L..R"), list(".D.R")]
        for row, col in ((0, 1), (2, 1), (1, 0), (1, 3)):
            with self.subTest(row=row, col=col):
                self.assertTrue(can_exit(board, row, col))

    def test_t08_arrows_behind_and_off_path_do_not_block(self):
        for direction, (dr, dc) in DIRECTIONS.items():
            with self.subTest(direction=direction):
                board = [["L"] * 5 for _ in range(5)]
                board[2][2] = direction
                for distance in (1, 2):
                    board[2 + dr * distance][2 + dc * distance] = "."
                self.assertTrue(can_exit(board, 2, 2))

    def test_invalid_coordinates_and_empty_cells_are_ignored(self):
        board = [list("U."), list(".R")]
        for row, col in ((-1, 1), (1, -1), (2, 0), (0, 2), (0, 1)):
            with self.subTest(row=row, col=col):
                self.assertFalse(can_exit(board, row, col))
        self.assertFalse(can_exit([], 0, 0))

    def test_t12_removed_blocker_changes_current_path(self):
        board = [list("R..U")]
        self.assertFalse(can_exit(board, 0, 0))
        board[0][3] = "."
        self.assertTrue(can_exit(board, 0, 0))


class LevelTests(unittest.TestCase):
    def test_invalid_layouts_are_rejected(self):
        for rows in ((), ("",), ("U", "RR"), ("UX",), ("...",), (None,), "U"):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                Level(1, "测试", rows)

    def test_mistake_budget_is_a_positive_integer(self):
        for count in (0, -1, 1.5, True, "3"):
            with self.subTest(count=count), self.assertRaises(ValueError):
                Level(1, "测试", ("U",), count)

    def test_level_collection_requires_unique_ids(self):
        with self.assertRaises(ValueError):
            validate_levels(())
        with self.assertRaises(ValueError):
            validate_levels((LEVELS[0], LEVELS[0]))
        with self.assertRaises(ValueError):
            validate_levels(("U",))
        validate_levels(LEVELS)

    def test_templates_are_immutable_and_copy_input_rows(self):
        rows = ["U"]
        level = Level(1, "测试", rows)
        rows[0] = "D"
        self.assertEqual(level.rows, ("U",))
        with self.assertRaises(FrozenInstanceError):
            level.rows = ("D",)

    def test_t13_prd_solutions_clear_all_three_levels(self):
        expected_counts = (8, 12, 20)
        expected_exits = (3, 3, 4)
        for level, solution, count, exits in zip(LEVELS, PRD_SOLUTIONS, expected_counts, expected_exits):
            with self.subTest(level=level.id):
                board = [list(row) for row in level.rows]
                self.assertEqual({cell for row in board for cell in row} - {"."}, set(DIRECTIONS))
                self.assertEqual(sum(cell != "." for row in board for cell in row), count)
                self.assertEqual(sum(can_exit(board, r, c) for r in range(len(board))
                                     for c in range(len(board[0]))), exits)
                for row, col in solution:
                    self.assertNotEqual(board[row][col], ".")
                    self.assertTrue(can_exit(board, row, col), (level.id, row, col))
                    board[row][col] = "."
                self.assertTrue(all(cell == "." for row in board for cell in row))

    def test_solver_clears_levels_without_changing_templates(self):
        templates = tuple(level.rows for level in LEVELS)
        for level in LEVELS:
            with self.subTest(level=level.id):
                solution = solve_level(level)
                self.assertIsNotNone(solution)
                board = [list(row) for row in level.rows]
                for row, col in solution:
                    self.assertTrue(can_exit(board, row, col))
                    board[row][col] = "."
                self.assertTrue(all(cell == "." for row in board for cell in row))
        self.assertEqual(tuple(level.rows for level in LEVELS), templates)

    def test_solver_reports_deadlocks(self):
        self.assertIsNone(solve_level(Level(1, "相向", ("R.L",))))
        self.assertIsNone(solve_level(Level(1, "部分可消除", ("R.L", ".D."))))


if __name__ == "__main__":
    unittest.main()
