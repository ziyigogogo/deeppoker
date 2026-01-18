"""
DeepPoker Agents - AI Agent Framework

This module provides the base agent interface and sample implementations
for integration with LLM RL frameworks like VERL.
"""

from deeppoker.agents.base import BaseAgent
from deeppoker.agents.random_agent import RandomAgent

__all__ = ["BaseAgent", "RandomAgent"]
