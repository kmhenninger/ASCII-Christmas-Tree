# ASCII-Christmas-Tree

An animated, colorful ASCII Christmas scene for the terminal, written in pure Python (no dependencies).

1. **Background** – the night sky fades in: the moon, twinkling stars, shooting stars, mountains, snowy hills, little houses and falling snow.
2. **Growing** – the tree sprouts from the trunk upward.
3. **Spinning** – the tree spins as a 3D cone and throws off sparkles.
4. **Decorating** – garlands wind around it, ornaments pop on, the lights switch on and the star drops onto the top.
5. **Celebration** – the lights blink, presents fall under the tree and a rainbow greeting appears.

## Run

```bash
python3 christmas_tree.py            # loops forever (about 42 s per show), Ctrl+C to quit
python3 christmas_tree.py --once     # play once, then keep the decorated tree on screen
```

Options:

| Flag | Description |
|------|-------------|
| `--speed 1.5` | Play faster or slower |
| `--fps 30` | Frame rate (default 20) |
| `--start 20` | Jump to a point in the show, in seconds |
| `--colors 256` | Force 256-color mode (default: auto-detects true color) |
| `--seed 7` | Draw the same scene every time |

The terminal must be at least 50×20. A bigger window gives a bigger tree. It looks best in a terminal with true color support, such as iTerm2, WezTerm, Ghostty or the VS Code terminal.
