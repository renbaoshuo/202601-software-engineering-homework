"""绘制界面和处理鼠标输入；规则与动作计时由 Game 管理。"""

from dataclasses import dataclass
from functools import lru_cache
import math
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pygame.gfxdraw

from game import ActionKind, Game, State


WINDOW_SIZE = (960, 720)
FONT_PATH = Path(__file__).resolve().parent / "assets" / "ArrowPuzzleSans.otf"
BG = (246, 245, 239)
INK = (30, 64, 56)
MUTED = (105, 119, 110)
PANEL = (255, 254, 250)
CELL = (226, 234, 222)
EMPTY = (240, 241, 233)
ACCENT = (232, 152, 98)
ERROR = (174, 65, 48)
DIRECTIONS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}


@dataclass(frozen=True)
class BoardLayout:
    x: int
    y: int
    cell_size: int
    rows: int
    cols: int

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.cols * self.cell_size,
                           self.rows * self.cell_size)

    def cell_at(self, position):
        if not self.rect.collidepoint(position):
            return None
        x, y = position
        return (int((y - self.y) // self.cell_size),
                int((x - self.x) // self.cell_size))

    def cell_center(self, row, col):
        return (self.x + (col + 0.5) * self.cell_size,
                self.y + (row + 0.5) * self.cell_size)


@dataclass(frozen=True)
class Button:
    label: str
    rect: pygame.Rect
    command: str
    primary: bool = True


def draw_arrow(surface, center, size, direction, color=INK):
    """用同一轮廓旋转出四个方向，不依赖字体箭头字符。"""
    dx, dy = DIRECTIONS[direction]
    points = [(-.25, -.055), (.06, -.055), (.06, -.19), (.28, 0),
              (.06, .19), (.06, .055), (-.25, .055)]
    cx, cy = center
    vertices = [(round(cx + (x * dx - y * dy) * size),
                 round(cy + (x * dy + y * dx) * size)) for x, y in points]
    pygame.gfxdraw.filled_polygon(surface, vertices, color)
    pygame.gfxdraw.aapolygon(surface, vertices, color)


class GameApp:
    def __init__(self, game=None, screen=None):
        pygame.display.init()
        pygame.font.init()
        self.screen = screen if screen is not None else pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("一箭又一箭")
        self.game = game if game is not None else Game()
        self.running = True
        # 字体随程序分发，不查找本机字体，也不依赖启动目录。
        self.font(20)

    @lru_cache(maxsize=16)
    def font(self, size):
        return pygame.font.Font(str(FONT_PATH), size)

    def text(self, value, size, position, color=INK, center=False):
        rendered = self.font(size).render(str(value), True, color)
        rect = rendered.get_rect()
        if center:
            rect.center = position
        else:
            rect.topleft = position
        self.screen.blit(rendered, rect)
        return rect

    def board_layout(self):
        rows, cols = len(self.game.board), len(self.game.board[0])
        cell_size = min(96, 432 // max(rows, cols))
        return BoardLayout((960 - cols * cell_size) // 2,
                           390 - rows * cell_size // 2, cell_size, rows, cols)

    def buttons(self):
        state = self.game.state
        if state == State.START:
            return [Button("开始游戏", pygame.Rect(88, 497, 216, 56), "start")]
        if state in (State.PLAYING, State.ANIMATING):
            return [Button("重新开始", pygame.Rect(754, 38, 142, 46), "restart", False)]
        if state == State.LEVEL_CLEARED:
            return [Button("下一关", pygame.Rect(362, 409, 236, 52), "next"),
                    Button("重玩本关", pygame.Rect(362, 475, 236, 46), "restart", False)]
        if state == State.FAILED:
            return [Button("重新开始", pygame.Rect(362, 435, 236, 52), "restart")]
        if state == State.ALL_CLEARED:
            return [Button("从第一关重玩", pygame.Rect(362, 409, 236, 52), "start"),
                    Button("返回首页", pygame.Rect(362, 475, 236, 46), "home", False)]
        return []

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if not self.running or event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        for button in self.buttons():
            if button.rect.collidepoint(event.pos):
                commands = {"start": self.game.start, "restart": self.game.restart,
                            "next": self.game.next_level, "home": self.game.go_home}
                commands[button.command]()
                return
        if self.game.state == State.PLAYING:
            cell = self.board_layout().cell_at(event.pos)
            if cell is not None:
                self.game.click_cell(*cell)

    def update(self, dt):
        self.game.update(dt)

    def run(self):
        clock = pygame.time.Clock()
        try:
            while self.running:
                # 先推进已有动作，避免把上一帧耗时算到新点击的动作上。
                self.update(clock.tick(60) / 1000)
                for event in pygame.event.get():
                    self.handle_event(event)
                if self.running:
                    self.draw()
                    pygame.display.flip()
        finally:
            self.close()

    def close(self):
        self.running = False
        self.font.cache_clear()
        pygame.quit()

    def draw_button(self, button):
        hovered = button.rect.collidepoint(pygame.mouse.get_pos())
        fill = INK if button.primary else CELL
        if hovered:
            fill = (48, 86, 70) if button.primary else (213, 225, 207)
        pygame.draw.rect(self.screen, fill, button.rect, border_radius=13)
        self.text(button.label, 19, button.rect.center,
                  PANEL if button.primary else INK, center=True)

    def draw_header(self):
        logo = pygame.Rect(64, 40, 42, 42)
        pygame.draw.rect(self.screen, INK, logo, border_radius=12)
        draw_arrow(self.screen, logo.center, 43, "R", PANEL)
        self.text("一箭又一箭", 23, (120, 35))
        self.text("单格箭头解谜", 12, (121, 67), MUTED)
        pygame.draw.line(self.screen, (221, 226, 214), (64, 106), (896, 106))

    def draw_start(self):
        self.text("观察方向，找到顺序", 16, (88, 173), MUTED)
        self.text("一箭又一箭", 50, (84, 215))
        self.text("给每一个箭头，留一条出路。", 19, (88, 291), MUTED)
        rules = ["沿箭头方向，查看通往边界的路径。",
                 "前方没有箭头，点击就能飞出。",
                 "被挡住会扣一次机会，每关有三次。",
                 "清空棋盘，就能进入下一关。"]
        for index, rule in enumerate(rules):
            y = 356 + index * 29
            pygame.draw.circle(self.screen, ACCENT, (93, y + 12), 3)
            self.text(rule, 16, (108, y), MUTED)
        self.text("3 个关卡 / 鼠标左键操作", 13, (88, 573), MUTED)
        card = pygame.Rect(554, 199, 318, 367)
        pygame.draw.rect(self.screen, (230, 232, 220), card.move(0, 6), border_radius=26)
        pygame.draw.rect(self.screen, PANEL, card, border_radius=26)
        demo = ("URR", "U.L", "LLD")
        for row, line in enumerate(demo):
            for col, direction in enumerate(line):
                rect = pygame.Rect(578 + col * 91, 226 + row * 91, 83, 83)
                fill = ACCENT if (row, col) == (0, 0) else CELL
                pygame.draw.rect(self.screen, EMPTY if direction == "." else fill,
                                 rect, border_radius=13)
                if direction != ".":
                    draw_arrow(self.screen, rect.center, 85, direction)
        self.text("观察 · 点击 · 清空", 15, (713, 529), MUTED, center=True)
        self.text("不必着急，先看清前方。", 14, (480, 658), MUTED, center=True)

    def draw_stats(self):
        game = self.game
        self.text(f"第 {game.level_index + 1} / {len(game.levels)} 关", 24, (64, 124))
        self.text(game.current_level.name, 15, (66, 161), MUTED)
        self.text("剩余箭头", 13, (594, 129), MUTED)
        self.text(f"{game.remaining_arrows:02d}", 28, (668, 114))
        self.text("剩余失误", 13, (755, 129), MUTED)
        self.text(str(game.mistakes_left), 28, (830, 114),
                  ERROR if game.mistakes_left <= 1 else INK)
        for i in range(game.current_level.max_mistakes):
            pygame.draw.circle(self.screen, ACCENT if i < game.mistakes_left else CELL,
                               (813 + i * 17, 167), 5)

    def draw_board(self):
        game, layout = self.game, self.board_layout()
        surround = layout.rect.inflate(28, 28)
        pygame.draw.rect(self.screen, (231, 233, 222), surround.move(0, 5), border_radius=27)
        pygame.draw.rect(self.screen, PANEL, surround, border_radius=27)
        action = game.active_action
        hover = layout.cell_at(pygame.mouse.get_pos()) if game.state == State.PLAYING else None
        for row, line in enumerate(game.board):
            for col, direction in enumerate(line):
                center = layout.cell_center(row, col)
                tile = pygame.Rect(0, 0, layout.cell_size - 8, layout.cell_size - 8)
                tile.center = (round(center[0]), round(center[1]))
                fill = EMPTY if direction == "." else CELL
                if direction != "." and hover == (row, col):
                    fill = (212, 226, 203)
                if action and (row, col) == (action.row, action.col):
                    if action.kind == ActionKind.BLOCKED:
                        fill = (246, 214, 197)
                pygame.draw.rect(self.screen, fill, tile, border_radius=13)
                if direction != "." and not (action and (row, col) == (action.row, action.col)):
                    draw_arrow(self.screen, center, layout.cell_size, direction)
        if action:
            self.draw_action(layout, action)

    def draw_action(self, layout, action):
        cx, cy = layout.cell_center(action.row, action.col)
        dx, dy = DIRECTIONS[action.direction]
        progress = min(1.0, action.elapsed / action.duration)
        color = INK
        if action.kind == ActionKind.EXIT:
            edge = {"U": cy - layout.rect.top, "D": layout.rect.bottom - cy,
                    "L": cx - layout.rect.left, "R": layout.rect.right - cx}[action.direction]
            # 尾部落在中心后 0.25 格，计时结束时尾部恰好到达边界。
            distance = (edge + layout.cell_size * .25) * progress
            cx, cy = cx + dx * distance, cy + dy * distance
        else:
            offset = math.sin(progress * math.pi * 6) * (1 - progress) * 7
            cx, cy = cx + dx * offset, cy + dy * offset
            color = ERROR
        old_clip = self.screen.get_clip()
        self.screen.set_clip(layout.rect)
        draw_arrow(self.screen, (cx, cy), layout.cell_size, action.direction, color)
        self.screen.set_clip(old_clip)

    def draw_game(self):
        self.draw_stats()
        self.draw_board()
        action = self.game.active_action
        if action and action.kind == ActionKind.BLOCKED:
            message, color = "前方有箭头阻挡", ERROR
        elif action:
            message, color = "路径畅通，箭头飞出", INK
        else:
            message, color = "先看前方，再点箭头", MUTED
        self.text(message, 18, (480, 648), color, center=True)
        self.text("鼠标左键点选 · 清空棋盘即可通关", 12, (480, 682), MUTED, center=True)

    def draw_result(self):
        overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        overlay.fill((246, 245, 239, 226))
        self.screen.blit(overlay, (0, 0))
        card = pygame.Rect(250, 205, 460, 356)
        pygame.draw.rect(self.screen, (223, 228, 215), card.move(0, 6), border_radius=28)
        pygame.draw.rect(self.screen, PANEL, card, border_radius=28)
        failed = self.game.state == State.FAILED
        mark = pygame.Rect(453, 232, 54, 54)
        pygame.draw.rect(self.screen, (246, 214, 197) if failed else CELL, mark, border_radius=16)
        if failed:
            self.text("!", 31, mark.center, ERROR, center=True)
        else:
            draw_arrow(self.screen, mark.center, 64, "U")
        if failed:
            title, detail = "挑战失败", "失误机会已用尽，重新观察一下。"
        elif self.game.state == State.ALL_CLEARED:
            title, detail = "全部关卡已通关", "每一个箭头，都找到了出路。"
        else:
            title = f"第 {self.game.level_index + 1} 关通关"
            detail = "棋盘已清空，继续下一关。"
        self.text(title, 31, (480, 329), center=True)
        self.text(detail, 16, (480, 376), MUTED, center=True)

    def draw(self):
        self.screen.fill(BG)
        self.draw_header()
        if self.game.state == State.START:
            self.draw_start()
        else:
            self.draw_game()
            if self.game.state in (State.LEVEL_CLEARED, State.FAILED, State.ALL_CLEARED):
                self.draw_result()
        for button in self.buttons():
            self.draw_button(button)
