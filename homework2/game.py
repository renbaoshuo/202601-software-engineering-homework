"""与图形库无关的路径判断、关卡求解和游戏状态。"""

from dataclasses import dataclass
from enum import Enum, auto
import math
from typing import Sequence

from levels import LEVELS, Level, validate_levels


DIRECTIONS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


def can_exit(board: Sequence[Sequence[str]], row: int, col: int) -> bool:
    """从相邻格检查到边界；无效坐标或空格返回 False。"""
    if not board or not 0 <= row < len(board) or not 0 <= col < len(board[0]):
        return False
    direction = board[row][col]
    if direction not in DIRECTIONS:
        return False
    dr, dc = DIRECTIONS[direction]
    row, col = row + dr, col + dc
    while 0 <= row < len(board) and 0 <= col < len(board[0]):
        if board[row][col] != ".":
            return False
        row, col = row + dr, col + dc
    return True


def solve_level(level: Level) -> list[tuple[int, int]] | None:
    """返回合法消除顺序；删除只会减少阻挡，贪心即可验证可解性。"""
    board = [list(row) for row in level.rows]
    solution: list[tuple[int, int]] = []
    remaining = sum(cell != "." for row in board for cell in row)
    while remaining:
        progress = False
        for row in range(len(board)):
            for col in range(len(board[0])):
                if can_exit(board, row, col):
                    board[row][col] = "."
                    solution.append((row, col))
                    remaining -= 1
                    progress = True
        if not progress:
            return None
    return solution


class State(Enum):
    START = auto()
    PLAYING = auto()
    ANIMATING = auto()
    LEVEL_CLEARED = auto()
    FAILED = auto()
    ALL_CLEARED = auto()


class ActionKind(Enum):
    EXIT = auto()
    BLOCKED = auto()


@dataclass
class Action:
    kind: ActionKind
    row: int
    col: int
    direction: str
    elapsed: float = 0.0
    duration: float = 0.32


class Game:
    def __init__(self, levels: Sequence[Level] = LEVELS) -> None:
        self.levels = tuple(levels)
        validate_levels(self.levels)
        self.level_index = 0
        self.board = [list(row) for row in self.current_level.rows]
        self.mistakes_left = self.current_level.max_mistakes
        self.state = State.START
        self.active_action: Action | None = None

    @property
    def current_level(self) -> Level:
        return self.levels[self.level_index]

    @property
    def remaining_arrows(self) -> int:
        return sum(cell != "." for row in self.board for cell in row)

    def _load_level(self, index: int) -> None:
        self.active_action = None
        self.level_index = index
        self.board = [list(row) for row in self.current_level.rows]
        self.mistakes_left = self.current_level.max_mistakes
        self.state = State.PLAYING

    def start(self) -> None:
        """从首页或全部通关结果进入第一关。"""
        if self.state in (State.START, State.ALL_CLEARED):
            self._load_level(0)

    def restart(self) -> None:
        """重开当前关；清除动作对象，旧动作不会再更新棋盘。"""
        if self.state in (State.PLAYING, State.ANIMATING, State.FAILED, State.LEVEL_CLEARED):
            self._load_level(self.level_index)

    def next_level(self) -> None:
        if self.state == State.LEVEL_CLEARED and self.level_index + 1 < len(self.levels):
            self._load_level(self.level_index + 1)

    def go_home(self) -> None:
        if self.state == State.ALL_CLEARED:
            self.active_action = None
            self.state = State.START

    def click_cell(self, row: int, col: int) -> None:
        if self.state != State.PLAYING:
            return
        if not 0 <= row < len(self.board) or not 0 <= col < len(self.board[0]):
            return
        direction = self.board[row][col]
        if direction not in DIRECTIONS:
            return
        kind = ActionKind.EXIT if can_exit(self.board, row, col) else ActionKind.BLOCKED
        if kind == ActionKind.BLOCKED:
            self.mistakes_left = max(0, self.mistakes_left - 1)
        self.active_action = Action(kind, row, col, direction,
                                    duration=0.32 if kind == ActionKind.EXIT else 0.26)
        self.state = State.ANIMATING

    def update(self, dt: float) -> None:
        """按秒推进一次动作；动画结束时一次性修改棋盘并切换状态。"""
        if self.state != State.ANIMATING or self.active_action is None:
            return
        if not math.isfinite(dt) or dt <= 0:
            return
        action = self.active_action
        action.elapsed = min(action.duration, action.elapsed + dt)
        if action.elapsed < action.duration:
            return
        self.active_action = None
        if action.kind == ActionKind.EXIT:
            self.board[action.row][action.col] = "."
            if self.remaining_arrows == 0:
                self.state = (State.ALL_CLEARED if self.level_index == len(self.levels) - 1
                              else State.LEVEL_CLEARED)
                return
        elif self.mistakes_left == 0:
            self.state = State.FAILED
            return
        self.state = State.PLAYING
