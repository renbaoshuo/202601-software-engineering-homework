"""与图形库无关的箭头路径判断和关卡求解。"""

from typing import Sequence

from levels import Level


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
