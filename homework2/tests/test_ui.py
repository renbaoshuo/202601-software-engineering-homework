"""使用 SDL 虚拟显示器验证鼠标事件、绘制和界面流程。"""

import ast
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from game import ActionKind, Game, State
from levels import LEVELS, Level
from ui import BoardLayout, GameApp


class BoardLayoutTests(unittest.TestCase):
    def setUp(self):
        self.layout = BoardLayout(x=50, y=70, cell_size=20, rows=2, cols=3)

    def test_t15_outer_edges_are_half_open(self):
        points = {
            (50, 70): (0, 0),
            (109, 70): (0, 2),
            (50, 109): (1, 0),
            (109, 109): (1, 2),
            (49, 70): None,
            (50, 69): None,
            (110, 70): None,
            (50, 110): None,
            (110, 110): None,
            (-1, 70): None,
            (50, -1): None,
        }
        for point, expected in points.items():
            with self.subTest(point=point):
                self.assertEqual(self.layout.cell_at(point), expected)
        self.assertEqual(self.layout.rect, pygame.Rect(50, 70, 60, 40))

    def test_t15_grid_lines_belong_to_cell_on_right_or_below(self):
        for point, expected in [
            ((69, 89), (0, 0)),
            ((70, 89), (0, 1)),
            ((69, 90), (1, 0)),
            ((70, 90), (1, 1)),
            ((90, 90), (1, 2)),
        ]:
            with self.subTest(point=point):
                self.assertEqual(self.layout.cell_at(point), expected)

    def test_cell_centers_round_trip_on_rectangular_board(self):
        for row in range(2):
            for col in range(3):
                with self.subTest(row=row, col=col):
                    center = self.layout.cell_center(row, col)
                    self.assertEqual(self.layout.cell_at(center), (row, col))


class GameAppTests(unittest.TestCase):
    def setUp(self):
        self.app = None

    def tearDown(self):
        if self.app is not None:
            self.app.close()

    def make_app(self, levels=None):
        if self.app is not None:
            self.app.close()
        if levels is None:
            levels = (
                Level(1, "第一关", ("U.L", "..R")),
                Level(2, "第二关", ("U.L", "..R")),
            )
        self.app = GameApp(game=Game(levels=levels))
        return self.app

    def mouse_down(self, point, button=1):
        self.app.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=point, button=button)
        )

    def click_button(self, command):
        buttons = [button for button in self.app.buttons() if button.command == command]
        self.assertEqual(len(buttons), 1, f"按钮命令应唯一：{command}")
        self.mouse_down(buttons[0].rect.center)

    def click_cell(self, row, col):
        self.mouse_down(self.app.board_layout().cell_center(row, col))

    def finish_action(self):
        action = self.app.game.active_action
        self.assertIsNotNone(action)
        self.app.update(action.duration + 0.01)

    def snapshot(self):
        game = self.app.game
        action = game.active_action
        return (
            game.state,
            game.level_index,
            tuple(tuple(row) for row in game.board),
            game.mistakes_left,
            game.remaining_arrows,
            None
            if action is None
            else (
                action.kind,
                action.row,
                action.col,
                action.direction,
                action.elapsed,
                action.duration,
            ),
        )

    def clear_sample_level(self):
        for row, col in [(0, 0), (0, 2), (1, 2)]:
            self.click_cell(row, col)
            self.assertEqual(self.app.game.active_action.kind, ActionKind.EXIT)
            self.finish_action()

    def build_scene(self, scene):
        mistakes = 1 if scene == "failed" else 3
        levels = [Level(1, "第一关", ("U.L", "..R"), mistakes)]
        if scene != "all_cleared":
            levels.append(Level(2, "第二关", ("U.L", "..R")))
        self.make_app(levels=tuple(levels))
        if scene != "start":
            self.click_button("start")
        if scene in ("exit", "blocked", "failed"):
            self.click_cell(0, 0 if scene == "exit" else 2)
            if scene == "failed":
                self.finish_action()
            else:
                self.app.update(self.app.game.active_action.duration / 2)
        elif scene in ("level_cleared", "all_cleared"):
            self.clear_sample_level()
        expected_states = {
            "start": State.START,
            "playing": State.PLAYING,
            "exit": State.ANIMATING,
            "blocked": State.ANIMATING,
            "failed": State.FAILED,
            "level_cleared": State.LEVEL_CLEARED,
            "all_cleared": State.ALL_CLEARED,
        }
        self.assertEqual(self.app.game.state, expected_states[scene])

    def test_t09_only_left_button_down_selects_an_arrow(self):
        self.make_app()
        self.click_button("start")
        point = self.app.board_layout().cell_center(0, 2)
        before = self.snapshot()
        events = [
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=point, button=3),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=point, button=2),
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=point, button=1),
            pygame.event.Event(
                pygame.MOUSEMOTION, pos=point, rel=(3, 0), buttons=(1, 0, 0)
            ),
        ]
        for event in events:
            with self.subTest(event=event.type, button=getattr(event, "button", None)):
                self.app.handle_event(event)
                self.assertEqual(self.snapshot(), before)

    def test_t09_empty_outside_and_removed_cells_have_no_effect(self):
        self.make_app()
        self.click_button("start")
        layout = self.app.board_layout()
        points = [
            layout.cell_center(1, 0),
            (layout.rect.left - 1, layout.rect.centery),
            (layout.rect.right, layout.rect.centery),
            (layout.rect.centerx, layout.rect.top - 1),
            (layout.rect.centerx, layout.rect.bottom),
            (-1, -1),
        ]
        before = self.snapshot()
        for point in points:
            with self.subTest(point=point):
                self.mouse_down(point)
                self.assertEqual(self.snapshot(), before)
        self.click_cell(0, 0)
        self.finish_action()
        self.assertEqual(self.app.game.board[0][0], ".")
        before = self.snapshot()
        self.click_cell(0, 0)
        self.assertEqual(self.snapshot(), before)

    def test_t09_holding_or_dragging_does_not_repeat_a_click(self):
        self.make_app()
        self.click_button("start")
        self.click_cell(0, 2)
        self.finish_action()
        self.assertEqual(self.app.game.mistakes_left, 2)
        before = self.snapshot()
        for _ in range(12):
            self.app.handle_event(
                pygame.event.Event(
                    pygame.MOUSEMOTION,
                    pos=self.app.board_layout().cell_center(0, 2),
                    rel=(0, 0),
                    buttons=(1, 0, 0),
                )
            )
            self.app.update(1 / 60)
        self.app.handle_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONUP,
                pos=self.app.board_layout().cell_center(0, 2),
                button=1,
            )
        )
        self.assertEqual(self.snapshot(), before)

    def test_t10_repeated_animation_clicks_are_ignored_and_not_queued(self):
        for col, kind, arrows, mistakes in [
            (0, ActionKind.EXIT, 2, 3),
            (2, ActionKind.BLOCKED, 3, 2),
        ]:
            with self.subTest(kind=kind):
                self.make_app()
                self.click_button("start")
                self.click_cell(0, col)
                self.assertEqual(self.app.game.active_action.kind, kind)
                before = self.snapshot()
                for _ in range(4):
                    for row, other_col in [(0, col), (0, 0), (0, 2), (1, 2)]:
                        self.click_cell(row, other_col)
                        self.assertEqual(self.snapshot(), before)
                self.finish_action()
                self.assertEqual(self.app.game.remaining_arrows, arrows)
                self.assertEqual(self.app.game.mistakes_left, mistakes)
                self.assertEqual(self.app.game.state, State.PLAYING)
                after = self.snapshot()
                self.app.update(10)
                self.assertEqual(self.snapshot(), after)

    def test_t11_restart_button_cancels_both_animation_kinds(self):
        for scene in ("exit", "blocked"):
            with self.subTest(scene=scene):
                self.build_scene(scene)
                self.assertGreater(self.app.game.active_action.elapsed, 0)
                self.click_button("restart")
                self.assertEqual(self.app.game.state, State.PLAYING)
                self.assertEqual(self.app.game.board, [list("U.L"), list("..R")])
                self.assertEqual(self.app.game.remaining_arrows, 3)
                self.assertEqual(self.app.game.mistakes_left, 3)
                self.assertIsNone(self.app.game.active_action)
                before = self.snapshot()
                self.app.update(10)
                self.assertEqual(self.snapshot(), before)

    def test_t10_run_ignores_queued_clicks_on_animation_completion_frame(self):
        for col, arrows, mistakes in ((0, 2, 3), (2, 3, 2)):
            with self.subTest(col=col):
                self.make_app()
                self.click_button("start")
                self.click_cell(0, col)
                action = self.app.game.active_action
                self.app.update(action.duration - 0.001)
                pygame.event.clear()
                for row, target_col in ((0, col), (1, 2)):
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN,
                        pos=self.app.board_layout().cell_center(row, target_col), button=1))

                # 第一帧处理排队点击并结束旧动作，第二帧才退出。
                def quit_after_frame():
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

                with patch("pygame.time.Clock") as clock:
                    clock.return_value.tick.return_value = 16
                    with patch("pygame.display.flip", side_effect=quit_after_frame):
                        self.app.run()
                self.assertEqual(self.app.game.state, State.PLAYING)
                self.assertIsNone(self.app.game.active_action)
                self.assertEqual(self.app.game.remaining_arrows, arrows)
                self.assertEqual(self.app.game.mistakes_left, mistakes)

    def test_first_click_does_not_consume_previous_frame_time(self):
        for col in (0, 2):
            with self.subTest(col=col):
                self.make_app()
                self.click_button("start")
                event = pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                          pos=self.app.board_layout().cell_center(0, col), button=1)
                self.app.step((event,), 1)
                action = self.app.game.active_action
                self.assertIsNotNone(action)
                self.assertEqual(action.elapsed, 0)
                self.assertEqual(self.app.game.state, State.ANIMATING)
                self.assertEqual(self.app.game.remaining_arrows, 3)

    def test_t11_restart_and_new_click_do_not_reuse_cancelled_action_time(self):
        for col in (0, 2):
            with self.subTest(col=col):
                self.make_app()
                self.click_button("start")
                self.click_cell(0, col)
                previous_action = self.app.game.active_action
                self.app.update(previous_action.duration - 0.001)
                restart = next(button for button in self.app.buttons() if button.command == "restart")
                events = (
                    pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=restart.rect.center, button=1),
                    pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                       pos=self.app.board_layout().cell_center(0, col), button=1),
                )
                self.app.step(events, 1)
                self.assertIsNot(self.app.game.active_action, previous_action)
                self.assertEqual(self.app.game.active_action.elapsed, 0)
                self.assertEqual(self.app.game.state, State.ANIMATING)
                self.assertEqual(self.app.game.remaining_arrows, 3)
                self.assertEqual(self.app.game.mistakes_left, 3 if col == 0 else 2)

    def test_t18_quit_stops_frame_updates_and_later_input(self):
        for scene in ("exit", "blocked"):
            with self.subTest(scene=scene):
                self.build_scene(scene)
                before = self.snapshot()
                events = (
                    pygame.event.Event(pygame.QUIT),
                    pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                       pos=self.app.board_layout().cell_center(0, 0), button=1),
                )
                self.app.step(events, 1)
                self.assertFalse(self.app.running)
                self.assertEqual(self.snapshot(), before)

    def test_buttons_are_processed_before_board_hit_detection(self):
        self.build_scene("playing")
        button = next(button for button in self.app.buttons() if button.command == "restart")
        x, y = button.rect.center
        overlapping_board = BoardLayout(x=x - 10, y=y - 10, cell_size=20, rows=1, cols=1)
        with patch.object(self.app, "board_layout", return_value=overlapping_board):
            with patch.object(self.app.game, "click_cell", wraps=self.app.game.click_cell) as click:
                self.mouse_down((x, y))
                click.assert_not_called()
        self.assertEqual(self.app.game.state, State.PLAYING)
        self.assertIsNone(self.app.game.active_action)

    def test_t15_grid_intersection_selects_exactly_one_cell(self):
        self.make_app(levels=(Level(1, "边界", ("LR", "UD")),))
        self.click_button("start")
        layout = self.app.board_layout()
        self.mouse_down((layout.x + layout.cell_size, layout.y + layout.cell_size))
        action = self.app.game.active_action
        self.assertIsNotNone(action)
        self.assertEqual((action.row, action.col), (1, 1))
        self.finish_action()
        self.assertEqual(self.app.game.board, [list("LR"), list("U.")])
        self.assertEqual(self.app.game.remaining_arrows, 3)

    def test_t04_result_buttons_replay_current_level_and_advance(self):
        self.build_scene("level_cleared")
        self.click_button("restart")
        self.assertEqual(self.app.game.state, State.PLAYING)
        self.assertEqual(self.app.game.level_index, 0)
        self.assertEqual(self.app.game.remaining_arrows, 3)
        self.clear_sample_level()
        self.click_button("next")
        self.assertEqual(self.app.game.state, State.PLAYING)
        self.assertEqual(self.app.game.level_index, 1)
        self.assertEqual(self.app.game.board, [list("U.L"), list("..R")])
        self.assertEqual(self.app.game.mistakes_left, 3)

    def test_t05_failure_restart_keeps_current_level(self):
        self.make_app(
            levels=(
                Level(1, "第一关", ("U.L", "..R")),
                Level(2, "第二关", ("RL",), 1),
            )
        )
        self.click_button("start")
        self.clear_sample_level()
        self.click_button("next")
        self.click_cell(0, 0)
        self.finish_action()
        self.assertEqual(self.app.game.state, State.FAILED)
        self.assertEqual(self.app.game.mistakes_left, 0)
        self.click_button("restart")
        self.assertEqual(self.app.game.state, State.PLAYING)
        self.assertEqual(self.app.game.level_index, 1)
        self.assertEqual(self.app.game.board, [list("RL")])
        self.assertEqual(self.app.game.mistakes_left, 1)

    def test_t14_final_result_replays_first_level_or_returns_home(self):
        self.build_scene("level_cleared")
        self.click_button("next")
        self.clear_sample_level()
        self.assertEqual(self.app.game.state, State.ALL_CLEARED)
        self.assertNotIn("next", [button.command for button in self.app.buttons()])
        self.click_button("start")
        self.assertEqual(self.app.game.state, State.PLAYING)
        self.assertEqual(self.app.game.level_index, 0)
        self.assertEqual(self.app.game.remaining_arrows, 3)
        self.clear_sample_level()
        self.click_button("next")
        self.clear_sample_level()
        self.click_button("home")
        self.assertEqual(self.app.game.state, State.START)
        self.click_button("start")
        self.assertEqual(self.app.game.state, State.PLAYING)
        self.assertEqual(self.app.game.level_index, 0)

    def test_result_screen_does_not_change_underlying_board_on_click(self):
        for scene in ("failed", "level_cleared", "all_cleared"):
            with self.subTest(scene=scene):
                self.build_scene(scene)
                rect = self.app.board_layout().rect
                point = (rect.left + 1, rect.top + 1)
                self.assertFalse(any(button.rect.collidepoint(point) for button in self.app.buttons()))
                before = self.snapshot()
                self.mouse_down(point)
                self.assertEqual(self.snapshot(), before)

    def test_t17_every_screen_draws_without_mutating_game(self):
        for scene in ("start", "playing", "exit", "blocked", "level_cleared", "failed", "all_cleared"):
            with self.subTest(scene=scene):
                self.build_scene(scene)
                before = self.snapshot()
                self.app.draw()
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.app.screen.get_size(), (960, 720))

    def test_gameplay_button_does_not_overlap_board(self):
        self.build_scene("playing")
        for button in self.app.buttons():
            with self.subTest(command=button.command):
                self.assertTrue(button.label)
                self.assertTrue(self.app.screen.get_rect().contains(button.rect))
                self.assertFalse(button.rect.colliderect(self.app.board_layout().rect))

    def test_builtin_boards_do_not_cover_status_text(self):
        self.make_app(levels=LEVELS)
        self.click_button("start")
        for index, level in enumerate(LEVELS):
            # 走实际关卡流程，用渲染所得文字矩形检查大棋盘遮挡回归。
            with self.subTest(level=level.id):
                rectangles = []
                original_text = self.app.text

                def record_text(*args, **kwargs):
                    rect = original_text(*args, **kwargs)
                    rectangles.append(rect)
                    return rect

                with patch.object(self.app, "text", side_effect=record_text):
                    self.app.draw_stats()
                for rect in rectangles:
                    self.assertFalse(rect.colliderect(self.app.board_layout().rect))
                if index < len(LEVELS) - 1:
                    from game import solve_level
                    for row, col in solve_level(level):
                        self.click_cell(row, col)
                        self.finish_action()
                    self.click_button("next")

    def test_t17_resources_load_from_an_unrelated_working_directory(self):
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                self.make_app()
                self.app.draw()
                self.click_button("start")
                self.app.draw()
            finally:
                os.chdir(original_directory)

    def test_t17_bundled_font_covers_chinese_interface_text(self):
        self.make_app()
        root = Path(__file__).resolve().parents[1]
        font_path = root / "assets" / "ArrowPuzzleSans.otf"
        font = pygame.font.Font(str(font_path), 24)
        characters = set()
        for filename in ("ui.py", "levels.py"):
            tree = ast.parse((root / filename).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    characters.update(character for character in node.value if character.isprintable())
        self.assertTrue(characters)
        for character in characters:
            with self.subTest(character=character):
                self.assertIsNotNone(font.metrics(character)[0])

    def test_t18_quit_works_in_every_state_and_both_animations(self):
        for scene in ("start", "playing", "exit", "blocked", "level_cleared", "failed", "all_cleared"):
            with self.subTest(scene=scene):
                self.build_scene(scene)
                self.assertTrue(pygame.display.get_init())
                self.assertTrue(pygame.font.get_init())
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                self.app.run()
                self.assertFalse(self.app.running)
                self.assertFalse(pygame.display.get_init())
                self.assertFalse(pygame.font.get_init())


if __name__ == "__main__":
    unittest.main()
