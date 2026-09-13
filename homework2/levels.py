"""不可变关卡模板与内置布局。"""

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Level:
    id: int
    name: str
    rows: tuple[str, ...]
    max_mistakes: int = 3

    def __post_init__(self) -> None:
        if not isinstance(self.rows, (tuple, list)) or not self.rows:
            raise ValueError("棋盘不能为空")
        if any(not isinstance(row, str) or not row for row in self.rows):
            raise ValueError("每行必须是非空字符串")
        rows = tuple(self.rows)
        if any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("棋盘各行必须等宽")
        if any(cell not in ".UDLR" for row in rows for cell in row):
            raise ValueError("棋盘只允许使用 .、U、D、L、R")
        if not any(cell != "." for row in rows for cell in row):
            raise ValueError("棋盘至少需要一个箭头")
        if type(self.max_mistakes) is not int or self.max_mistakes <= 0:
            raise ValueError("失误次数必须是正整数")
        if type(self.id) is not int:
            raise ValueError("关卡编号必须是整数")
        object.__setattr__(self, "rows", rows)


def validate_levels(levels: Sequence[Level]) -> None:
    """检查关卡集合，单个布局由 Level 构造时检查。"""
    if not levels:
        raise ValueError("至少需要一个关卡")
    if any(not isinstance(level, Level) for level in levels):
        raise ValueError("关卡集合只能包含 Level")
    if len({level.id for level in levels}) != len(levels):
        raise ValueError("关卡编号不能重复")


LEVELS = (
    Level(1, "认识阻挡", ("..RD", "U..D", ".R.D", "L..R")),
    Level(2, "交叉观察", ("..LLD", "R.U..", "U..U.", "U..RR", "..U.R")),
    Level(3, "连续解锁", ("LD.LR.", "...R.R", ".DL.L.", "U....U", "DLLL..", "LLULL.")),
)

validate_levels(LEVELS)
