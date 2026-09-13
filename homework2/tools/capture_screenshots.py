"""通过界面事件通关并保存画面；这是自动化检查，不是本人试玩。"""

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="使用 SDL 虚拟显示器")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "screenshots")
    args = parser.parse_args()
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    from game import ActionKind, State, solve_level
    from ui import GameApp, pygame

    app = GameApp()
    clock = pygame.time.Clock()
    args.output.mkdir(parents=True, exist_ok=True)

    def frame():
        dt = 1 / 60 if args.headless else clock.tick(60) / 1000
        app.step(pygame.event.get(), dt)
        if not app.running:
            raise SystemExit("窗口已关闭，检查终止")
        app.draw()
        pygame.display.flip()

    def save(name):
        app.draw()
        pygame.display.flip()
        pygame.image.save(app.screen, str(args.output / f"{name}.png"))

    def click(position):
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=1))
        frame()

    def button(command):
        click(next(b.rect.center for b in app.buttons() if b.command == command))

    def finish():
        while app.game.active_action:
            frame()

    try:
        save("start")
        button("start")
        save("level-1")
        click(app.board_layout().cell_center(0, 2))
        assert app.game.active_action.kind == ActionKind.BLOCKED
        save("blocked")
        finish()
        for _ in range(2):
            click(app.board_layout().cell_center(0, 2))
            finish()
        assert app.game.state == State.FAILED
        save("failed")
        button("restart")
        for index, level in enumerate(app.game.levels):
            assert app.game.level_index == index
            assert app.game.mistakes_left == level.max_mistakes
            # 每关先通过按钮重开一次，再走完整解序。
            button("restart")
            save(f"level-{index + 1}")
            solution = solve_level(level)
            assert solution is not None
            for row, col in solution:
                before = app.game.remaining_arrows
                click(app.board_layout().cell_center(row, col))
                assert app.game.active_action.kind == ActionKind.EXIT
                finish()
                assert app.game.remaining_arrows == before - 1
            assert app.game.remaining_arrows == 0
            if index < len(app.game.levels) - 1:
                assert app.game.state == State.LEVEL_CLEARED
                save(f"cleared-{index + 1}")
                button("next")
        assert app.game.state == State.ALL_CLEARED
        save("all-cleared")
        button("home")
        assert app.game.state == State.START
        button("start")
        assert app.game.level_index == 0 and app.game.remaining_arrows == 8
        print(f"3 个关卡已通过界面事件通关；失败、各关重开和返回首页检查通过。截图：{args.output}")
    finally:
        app.close()


if __name__ == "__main__":
    main()
