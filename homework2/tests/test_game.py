"""PRD 中的路径、关卡和状态约定。测试不依赖图形库。"""

from dataclasses import FrozenInstanceError
import unittest

from game import ActionKind, DIRECTIONS, Game, State, can_exit, solve_level
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


class GameTests(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.start()

    def assert_initial_level(self, game, index):
        level = game.levels[index]
        self.assertEqual(game.level_index, index)
        self.assertEqual(game.board, [list(row) for row in level.rows])
        self.assertEqual(game.mistakes_left, level.max_mistakes)
        self.assertEqual(game.remaining_arrows, sum(cell != "." for row in level.rows for cell in row))
        self.assertEqual(game.state, State.PLAYING)
        self.assertIsNone(game.active_action)

    def clear_current_level(self, game):
        solution = solve_level(game.current_level)
        self.assertIsNotNone(solution)
        for row, col in solution:
            game.click_cell(row, col)
            self.assertEqual(game.active_action.kind, ActionKind.EXIT)
            game.update(game.active_action.duration)

    def test_initial_state_and_start(self):
        game = Game()
        self.assertEqual(game.state, State.START)
        game.click_cell(1, 0)
        game.restart()
        game.next_level()
        game.update(1)
        self.assertEqual(game.state, State.START)
        self.assertIsNone(game.active_action)
        game.start()
        self.assert_initial_level(game, 0)

    def test_t01_success_waits_for_animation_then_deletes_once(self):
        game = self.game
        game.click_cell(1, 0)
        action = game.active_action
        self.assertEqual((action.kind, action.row, action.col, action.direction),
                         (ActionKind.EXIT, 1, 0, "U"))
        self.assertEqual(game.state, State.ANIMATING)
        self.assertEqual(game.remaining_arrows, 8)
        game.update(action.duration / 2)
        self.assertEqual(game.board[1][0], "U")
        self.assertEqual(game.remaining_arrows, 8)
        game.update(action.duration / 2)
        self.assertEqual(game.board[1][0], ".")
        self.assertEqual(game.remaining_arrows, 7)
        self.assertEqual(game.mistakes_left, 3)
        self.assertEqual(game.state, State.PLAYING)
        self.assertIsNone(game.active_action)
        game.update(10)
        self.assertEqual(game.remaining_arrows, 7)

    def test_t02_collision_charges_once_and_preserves_all_positions(self):
        game = self.game
        before = [row[:] for row in game.board]
        game.click_cell(0, 2)
        self.assertEqual(game.active_action.kind, ActionKind.BLOCKED)
        self.assertEqual(game.mistakes_left, 2)
        self.assertEqual(game.board, before)
        self.assertEqual(game.remaining_arrows, 8)
        game.update(0.13)
        self.assertEqual(game.state, State.ANIMATING)
        game.update(0.13)
        self.assertEqual(game.state, State.PLAYING)
        self.assertEqual(game.board, before)
        self.assertEqual(game.mistakes_left, 2)

    def test_t03_four_outward_edges_animate_and_clear(self):
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                game = Game((Level(1, "边界", (direction,)),))
                game.start()
                game.click_cell(0, 0)
                self.assertEqual(game.active_action.kind, ActionKind.EXIT)
                self.assertEqual(game.state, State.ANIMATING)
                game.update(1)
                self.assertEqual(game.remaining_arrows, 0)
                self.assertEqual(game.state, State.ALL_CLEARED)
                self.assertEqual(game.mistakes_left, 3)

    def test_t04_next_level_restores_its_layout_and_budget(self):
        game = self.game
        game.click_cell(0, 2)
        game.update(1)
        self.clear_current_level(game)
        self.assertEqual(game.state, State.LEVEL_CLEARED)
        self.assertEqual(game.mistakes_left, 2)
        self.assertEqual(game.level_index, 0)
        game.click_cell(0, 2)
        game.update(10)
        self.assertEqual(game.state, State.LEVEL_CLEARED)
        game.next_level()
        self.assert_initial_level(game, 1)

    def test_t05_failure_waits_for_feedback_and_locks_input(self):
        game = self.game
        for remaining in (2, 1, 0):
            game.click_cell(0, 2)
            self.assertEqual(game.mistakes_left, remaining)
            self.assertEqual(game.state, State.ANIMATING)
            for _ in range(4):
                game.click_cell(0, 2)
            self.assertEqual(game.mistakes_left, remaining)
            game.update(1)
        self.assertEqual(game.state, State.FAILED)
        game.click_cell(0, 2)
        game.click_cell(1, 0)
        game.update(10)
        self.assertEqual(game.mistakes_left, 0)
        self.assertEqual(game.remaining_arrows, 8)
        self.assertIsNone(game.active_action)
        game.restart()
        self.assert_initial_level(game, 0)

    def test_t06_restart_restores_current_level(self):
        game = self.game
        self.clear_current_level(game)
        game.next_level()
        game.click_cell(1, 0)
        game.update(1)
        game.click_cell(0, 2)
        game.update(1)
        self.assertEqual(game.mistakes_left, 2)
        self.assertEqual(game.remaining_arrows, 11)
        game.restart()
        self.assert_initial_level(game, 1)

    def test_t09_empty_outside_and_removed_cells_are_noops(self):
        game = self.game
        for row, col in ((-1, 0), (0, -1), (4, 0), (0, 4), (0, 0)):
            game.click_cell(row, col)
            self.assert_initial_level(game, 0)
        game.click_cell(1, 0)
        game.update(1)
        game.click_cell(1, 0)
        self.assertEqual(game.state, State.PLAYING)
        self.assertEqual(game.remaining_arrows, 7)
        self.assertEqual(game.mistakes_left, 3)

    def test_t10_animation_ignores_all_further_clicks_without_queueing(self):
        for first in ((1, 0), (0, 2)):
            with self.subTest(first=first):
                game = Game()
                game.start()
                game.click_cell(*first)
                action = game.active_action
                budget = game.mistakes_left
                for _ in range(10):
                    game.click_cell(*first)
                    game.click_cell(3, 0)
                self.assertIs(game.active_action, action)
                self.assertEqual(game.mistakes_left, budget)
                game.update(100)
                game.update(100)
                self.assertEqual(game.state, State.PLAYING)
                self.assertEqual(game.board[3][0], "L")
                self.assertEqual(game.remaining_arrows, 7 if first == (1, 0) else 8)

    def test_t11_restart_cancels_both_animation_kinds(self):
        for cell in ((1, 0), (0, 2)):
            with self.subTest(cell=cell):
                game = self.game
                game.click_cell(*cell)
                action = game.active_action
                game.update(0.1)
                game.restart()
                self.assert_initial_level(game, 0)
                game.update(100)
                self.assert_initial_level(game, 0)
                self.assertEqual(action.elapsed, 0.1)

    def test_t11_cancelled_collision_cannot_fail_restarted_game(self):
        game = Game((Level(1, "一次失误", ("RD",), 1),))
        game.start()
        game.click_cell(0, 0)
        self.assertEqual(game.mistakes_left, 0)
        game.restart()
        game.update(10)
        self.assert_initial_level(game, 0)

    def test_t12_cleared_blocker_allows_previously_blocked_arrow(self):
        game = Game((Level(1, "阻挡", ("R.D",)),))
        game.start()
        game.click_cell(0, 0)
        game.update(1)
        self.assertEqual(game.mistakes_left, 2)
        game.click_cell(0, 2)
        game.update(1)
        game.click_cell(0, 0)
        self.assertEqual(game.active_action.kind, ActionKind.EXIT)
        game.update(1)
        self.assertEqual(game.state, State.ALL_CLEARED)
        self.assertEqual(game.mistakes_left, 2)

    def test_t13_all_prd_solutions_follow_game_lifecycle(self):
        game = self.game
        for index, solution in enumerate(PRD_SOLUTIONS):
            self.assert_initial_level(game, index)
            for remaining, (row, col) in enumerate(solution, start=1):
                game.click_cell(row, col)
                self.assertEqual(game.state, State.ANIMATING)
                self.assertEqual(game.remaining_arrows, len(solution) - remaining + 1)
                self.assertEqual(game.active_action.kind, ActionKind.EXIT)
                game.update(1)
                self.assertEqual(game.remaining_arrows, len(solution) - remaining)
                self.assertEqual(game.mistakes_left, 3)
            expected = State.ALL_CLEARED if index == 2 else State.LEVEL_CLEARED
            self.assertEqual(game.state, expected)
            game.next_level()
        self.assertEqual(game.level_index, 2)
        self.assertEqual(game.state, State.ALL_CLEARED)

    def test_t14_final_result_replays_first_level_or_returns_home(self):
        for operation in ("replay", "home"):
            with self.subTest(operation=operation):
                game = Game((Level(1, "第一关", ("L",)), Level(2, "末关", ("R",))))
                game.start()
                self.clear_current_level(game)
                game.next_level()
                self.clear_current_level(game)
                game.next_level()
                game.click_cell(0, 0)
                game.restart()
                game.update(10)
                self.assertEqual(game.state, State.ALL_CLEARED)
                self.assertEqual(game.level_index, 1)
                if operation == "home":
                    game.go_home()
                    self.assertEqual(game.state, State.START)
                    game.click_cell(0, 0)
                    self.assertIsNone(game.active_action)
                game.start()
                self.assert_initial_level(game, 0)

    def test_t16_repeated_restart_and_transition_preserve_templates(self):
        templates = tuple(level.rows for level in LEVELS)
        game = self.game
        for index in range(len(LEVELS)):
            for _ in range(3):
                row, col = solve_level(game.current_level)[0]
                game.click_cell(row, col)
                game.update(1)
                game.restart()
                self.assert_initial_level(game, index)
            self.clear_current_level(game)
            game.next_level()
        self.assertEqual(tuple(level.rows for level in LEVELS), templates)

    def test_runtime_boards_and_input_collection_are_independent(self):
        levels = list(LEVELS)
        first, second = Game(levels), Game(levels)
        levels.clear()
        first.start()
        second.start()
        first.click_cell(1, 0)
        first.update(1)
        self.assert_initial_level(second, 0)
        self.assertEqual(first.current_level.rows, LEVELS[0].rows)

    def test_level_specific_budget_is_used(self):
        game = Game((Level(1, "第一关", ("L",), 1), Level(2, "第二关", ("R",), 5)))
        game.start()
        self.assertEqual(game.mistakes_left, 1)
        self.clear_current_level(game)
        game.next_level()
        self.assertEqual(game.mistakes_left, 5)

    def test_invalid_transitions_during_play_do_not_reset_progress(self):
        game = self.game
        game.click_cell(1, 0)
        action = game.active_action
        game.start()
        game.next_level()
        game.go_home()
        self.assertIs(game.active_action, action)
        self.assertEqual(game.state, State.ANIMATING)
        game.update(1)
        game.start()
        game.next_level()
        game.go_home()
        self.assertEqual(game.state, State.PLAYING)
        self.assertEqual(game.remaining_arrows, 7)

    def test_invalid_time_does_not_corrupt_animation(self):
        game = self.game
        game.click_cell(1, 0)
        for dt in (-1, 0, float("nan"), float("inf")):
            game.update(dt)
            self.assertEqual(game.active_action.elapsed, 0)
            self.assertEqual(game.state, State.ANIMATING)
        game.update(1)
        self.assertEqual(game.remaining_arrows, 7)

    def test_cleared_nonfinal_level_can_be_replayed(self):
        game = self.game
        self.clear_current_level(game)
        game.restart()
        self.assert_initial_level(game, 0)

    def test_game_rejects_empty_and_duplicate_level_collections(self):
        for levels in ((), (LEVELS[0], LEVELS[0])):
            with self.subTest(levels=levels), self.assertRaises(ValueError):
                Game(levels)


if __name__ == "__main__":
    unittest.main()
