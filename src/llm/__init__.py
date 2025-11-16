"""
LLM client wrapper for Tech Spec Agent.
Supports both Anthropic Claude and OpenAI models.
"""

from src.llm.client import LLMClient, ModelType

__all__ = ["LLMClient", "ModelType"]
