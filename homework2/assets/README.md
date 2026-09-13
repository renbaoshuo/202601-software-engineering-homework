# 字体来源

`ArrowPuzzleSans.otf` 是 Noto Sans SC Regular 2.004 的字符子集，字体名称已改为 Arrow Puzzle Sans。
包含游戏界面和关卡名称所需字符、ASCII 字符。保留原版权信息，遵循同目录的 [SIL Open Font License 1.1](OFL.txt)。

- 原版权：© 2014–2021 Adobe (http://www.adobe.com/)。
- [上游字体](https://github.com/notofonts/noto-cjk/blob/main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf)
- [上游许可](https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE)
- 下载日期：2026-09-13。
- 修改：裁剪字形、重命名字体；未修改字形轮廓。字库清单见 `font-characters.txt`。

游戏运行只需 pygame-ce。更新中文文案时，用开发工具重新生成字体：

```bash
python -m pip install fonttools==4.65.0
# 从上游字体链接下载原始文件后，传入它的本地路径。
python tools/subset_font.py /path/to/NotoSansSC-Regular.otf
```

箭头、网格、按钮和装饰均由 `ui.py` 绘制，无外部图片或音效。
