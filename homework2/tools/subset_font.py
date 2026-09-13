"""从下载的 Noto Sans SC 字体生成游戏字库；只在修改文案后使用。"""

import ast
from pathlib import Path
import sys

from fontTools import subset
from fontTools.ttLib import TTFont


def build(source: str) -> None:
    root = Path(__file__).resolve().parents[1]
    characters = set(chr(code) for code in range(32, 127))
    for filename in ("ui.py", "levels.py"):
        tree = ast.parse((root / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                characters.update(c for c in node.value if c.isprintable())
    options = subset.Options()
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    font = TTFont(source)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text="".join(sorted(characters)))
    subsetter.subset(font)
    names = {1: "Arrow Puzzle Sans", 2: "Regular", 3: "ArrowPuzzleSans-Regular-1.0",
             4: "Arrow Puzzle Sans Regular", 6: "ArrowPuzzleSans-Regular",
             16: "Arrow Puzzle Sans", 17: "Regular"}
    for record in font["name"].names:
        if record.nameID in names:
            record.string = names[record.nameID].encode(record.getEncoding())
    if "CFF " in font:
        font["CFF "].cff.fontNames = ["ArrowPuzzleSans-Regular"]
        top = font["CFF "].cff.topDictIndex[0]
        top.FamilyName = "Arrow Puzzle Sans"
        top.FullName = "Arrow Puzzle Sans Regular"
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    font.save(assets / "ArrowPuzzleSans.otf")
    (assets / "font-characters.txt").write_text("".join(sorted(characters)) + "\n", encoding="utf-8")
    print(f"已生成字库，包含 {len(characters)} 个字符")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("用法：python tools/subset_font.py 原始字体.otf")
    build(sys.argv[1])
