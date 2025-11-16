"""
LLM client wrapper for Claude and OpenAI models.
Provides unified interface for different LLM providers.
"""

from typing import List, Dict, Optional, Union, Literal
from enum import Enum
import anthropic
import openai
import structlog
from pydantic import BaseModel

from src.config import settings

logger = structlog.get_logger(__name__)


class ModelType(str, Enum):
    """Supported LLM model types."""
    CLAUDE_OPUS = "claude-opus-4-20250514"
    CLAUDE_SONNET = "claude-sonnet-4-20250514"
    CLAUDE_HAIKU = "claude-3-5-haiku-20241022"
    GPT4 = "gpt-4-turbo-preview"
    GPT4_O = "gpt-4o"
    GPT35_TURBO = "gpt-3.5-turbo"


class Message(BaseModel):
    """Message format for LLM conversations."""
    role: Literal["system", "user", "assistant"]
    content: str


class LLMResponse(BaseModel):
    """Standardized LLM response format."""
    content: str
    model: str
    tokens_used: int
    finish_reason: str
    metadata: Dict = {}


class LLMClient:
    """
    Unified LLM client for Claude and OpenAI models.

    Supports:
    - Claude Opus 4, Sonnet 4, Haiku 3.5
    - GPT-4, GPT-4o, GPT-3.5-turbo

    Features:
    - Automatic retries with exponential backoff
    - Token usage tracking
    - Streaming support
    - Temperature and max_tokens configuration
    """

    def __init__(
        self,
        model: ModelType = ModelType.CLAUDE_SONNET,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ):
        """
        Initialize LLM client.

        Args:
            model: Model type to use
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize clients
        if model.value.startswith("claude"):
            self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            self.provider = "anthropic"
        elif model.value.startswith("gpt"):
            self.client = openai.AsyncOpenAI(
                api_key=settings.openai_api_key,
                organization=settings.openai_org_id if settings.openai_org_id else None
            )
            self.provider = "openai"
        else:
            raise ValueError(f"Unsupported model: {model}")

        logger.info("LLM client initialized", model=model.value, provider=self.provider)

    async def generate(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None
    ) -> LLMResponse:
        """
        Generate completion from messages.

        Args:
            messages: List of conversation messages
            system: System prompt (optional)
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            stop_sequences: List of sequences to stop generation

        Returns:
            LLMResponse with generated content and metadata
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        try:
            if self.provider == "anthropic":
                return await self._generate_claude(messages, system, temp, max_tok, stop_sequences)
            elif self.provider == "openai":
                return await self._generate_openai(messages, system, temp, max_tok, stop_sequences)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

        except Exception as e:
            logger.error("LLM generation failed", error=str(e), model=self.model.value)
            raise

    async def _generate_claude(
        self,
        messages: List[Message],
        system: Optional[str],
        temperature: float,
        max_tokens: int,
        stop_sequences: Optional[List[str]]
    ) -> LLMResponse:
        """Generate completion using Claude API."""
        # Convert messages to Claude format
        claude_messages = []
        for msg in messages:
            if msg.role != "system":  # Claude uses separate system parameter
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Call Claude API
        response = await self.client.messages.create(
            model=self.model.value,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system if system else None,
            messages=claude_messages,
            stop_sequences=stop_sequences if stop_sequences else None
        )

        # Extract content
        content = ""
        if response.content:
            # Claude returns list of content blocks
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text

        return LLMResponse(
            content=content,
            model=self.model.value,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            finish_reason=response.stop_reason or "complete",
            metadata={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        )

    async def _generate_openai(
        self,
        messages: List[Message],
        system: Optional[str],
        temperature: float,
        max_tokens: int,
        stop_sequences: Optional[List[str]]
    ) -> LLMResponse:
        """Generate completion using OpenAI API."""
        # Convert messages to OpenAI format
        openai_messages = []

        # Add system message if provided
        if system:
            openai_messages.append({
                "role": "system",
                "content": system
            })

        # Add conversation messages
        for msg in messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model=self.model.value,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop_sequences if stop_sequences else None
        )

        # Extract content
        content = response.choices[0].message.content or ""

        return LLMResponse(
            content=content,
            model=self.model.value,
            tokens_used=response.usage.total_tokens,
            finish_reason=response.choices[0].finish_reason,
            metadata={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        )

    async def generate_json(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict:
        """
        Generate JSON response from messages.

        Automatically adds instructions for JSON formatting and
        parses the response into a dictionary.

        Args:
            messages: List of conversation messages
            system: System prompt (optional)
            temperature: Lower temperature for more deterministic JSON
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed JSON dictionary
        """
        import json

        # Append JSON instruction to last user message
        if messages:
            last_message = messages[-1]
            if last_message.role == "user":
                last_message.content += "\n\nRespond with valid JSON only. Do not include any explanatory text outside the JSON."

        # Generate response
        response = await self.generate(
            messages=messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Parse JSON from response
        try:
            # Try to extract JSON from markdown code blocks if present
            content = response.content.strip()
            if "```json" in content:
                # Extract JSON from markdown code block
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                # Extract from generic code block
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response", error=str(e), content=response.content)
            raise ValueError(f"LLM returned invalid JSON: {e}")

    async def generate_with_retry(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        max_retries: int = 3,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion with automatic retry on failure.

        Args:
            messages: List of conversation messages
            system: System prompt (optional)
            max_retries: Maximum number of retries
            **kwargs: Additional arguments for generate()

        Returns:
            LLMResponse with generated content
        """
        import asyncio

        for attempt in range(max_retries):
            try:
                return await self.generate(messages, system, **kwargs)

            except Exception as e:
                if attempt == max_retries - 1:
                    # Last attempt failed
                    logger.error(
                        "LLM generation failed after retries",
                        error=str(e),
                        attempts=max_retries
                    )
                    raise

                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt
                logger.warning(
                    "LLM generation failed, retrying",
                    error=str(e),
                    attempt=attempt + 1,
                    wait_time=wait_time
                )
                await asyncio.sleep(wait_time)

        raise RuntimeError("Should not reach here")


# ============= Helper Functions =============

async def create_llm_client(
    model: Union[ModelType, str] = ModelType.CLAUDE_SONNET,
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> LLMClient:
    """
    Factory function to create LLM client.

    Args:
        model: Model type (enum or string)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Configured LLM client
    """
    if isinstance(model, str):
        model = ModelType(model)

    return LLMClient(model=model, temperature=temperature, max_tokens=max_tokens)


async def quick_generate(
    prompt: str,
    model: ModelType = ModelType.CLAUDE_SONNET,
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> str:
    """
    Quick helper to generate from a simple prompt.

    Args:
        prompt: User prompt
        model: Model to use
        temperature: Sampling temperature
        max_tokens: Maximum tokens

    Returns:
        Generated text content
    """
    client = LLMClient(model=model, temperature=temperature, max_tokens=max_tokens)
    response = await client.generate(
        messages=[Message(role="user", content=prompt)]
    )
    return response.content
