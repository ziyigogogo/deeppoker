# DeepPoker

**DeepPoker R1** - A Texas Hold'em poker game engine with FastAPI WebSocket server and AI agent framework.

## Features

- Pure Python game core logic (no external poker dependencies)
- FastAPI + WebSocket server architecture
- AI Agent interface for LLM RL integration
- Complete Texas Hold'em rules implementation

## Installation

```bash
pip install deeppoker
```

Or with uv:

```bash
uv add deeppoker
```

## Quick Start

```python
from deeppoker import Card, Deck, Player, TexasHoldemGame

# Create players
players = [Player(f"Player {i}", chips=1000) for i in range(4)]

# Create and start a game
game = TexasHoldemGame(players, small_blind=10, big_blind=20)
game.start_hand()
```

## Development

Clone the repository and install development dependencies:

```bash
git clone https://github.com/ziyigogogo/deeppoker.git
cd deeppoker
uv sync --all-extras
```

Run tests:

```bash
uv run pytest
```

Start the server:

```bash
uv run deeppoker
```

## API Reference

### Core Classes

- `Card` - Represents a playing card
- `Deck` - A deck of 52 cards
- `Player` - A poker player with chips
- `TexasHoldemGame` - Main game engine
- `HandRank` - Hand ranking enumeration
- `evaluate_hand` - Hand evaluation function

### Agents

- `BaseAgent` - Abstract base class for AI agents
- `RandomAgent` - Random action agent for testing

## Publishing

发布新版本到 PyPI（维护者使用）：

```bash
# 1. 更新 pyproject.toml 中的 version
# 2. 更新 deeppoker/__init__.py 中的 __version__
# 3. 提交更改
git add . && git commit -m "Bump version to x.x.x"

# 4. 打 tag 并推送
git tag vx.x.x
git push && git push --tags
```

GitHub Actions 会自动构建并发布到 PyPI。

## License

MIT License - see [LICENSE](LICENSE) for details.
