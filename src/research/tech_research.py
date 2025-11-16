"""
Technology research module using Tavily API and LLMs.
Researches technology options for identified gaps.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel
import structlog
from tavily import TavilyClient

from src.config import settings
from src.llm.client import LLMClient, ModelType, Message

logger = structlog.get_logger(__name__)


class TechnologyOption(BaseModel):
    """Single technology option with metadata."""
    technology_name: str
    description: str
    pros: List[str]
    cons: List[str]
    use_cases: List[str]
    popularity_score: float  # 0-100
    learning_curve: str  # "low", "medium", "high"
    documentation_quality: str  # "excellent", "good", "fair", "poor"
    community_support: str  # "excellent", "good", "fair", "poor"
    integration_complexity: str  # "low", "medium", "high"
    sources: List[str]  # URLs of research sources


class ResearchResult(BaseModel):
    """Result of technology research for a specific category."""
    category: str
    question: str
    options: List[TechnologyOption]
    research_summary: str
    recommendation: Optional[str] = None


class TechnologyResearcher:
    """
    Researches technology options using Tavily API and LLMs.

    Process:
    1. Search for technologies using Tavily API
    2. Analyze search results with LLM
    3. Extract pros/cons and metadata
    4. Rank options by suitability
    5. Generate recommendations
    """

    def __init__(
        self,
        tavily_api_key: Optional[str] = None,
        llm_model: Optional[ModelType] = None
    ):
        """
        Initialize technology researcher.

        Args:
            tavily_api_key: Tavily API key (uses settings if not provided)
            llm_model: LLM model to use for analysis
        """
        self.tavily_client = TavilyClient(
            api_key=tavily_api_key or settings.tavily_api_key
        )
        self.llm_client = LLMClient(model=llm_model, temperature=0.3)
        logger.info("Technology researcher initialized", llm_model=self.llm_client.model.value)

    async def research_category(
        self,
        category: str,
        question: str,
        context: Dict,
        max_options: int = 3
    ) -> ResearchResult:
        """
        Research technology options for a specific category.

        Args:
            category: Technology category (e.g., "authentication", "database")
            question: Research question to answer
            context: Project context (PRD, design docs, requirements)
            max_options: Maximum number of options to return

        Returns:
            ResearchResult with technology options and recommendations
        """
        logger.info("Researching technology category", category=category)

        try:
            # Step 1: Search for technologies
            search_results = await self._search_technologies(category, question, context)

            # Step 2: Analyze results with LLM
            options = await self._analyze_search_results(
                category=category,
                question=question,
                search_results=search_results,
                context=context,
                max_options=max_options
            )

            # Step 3: Generate research summary
            summary = await self._generate_summary(category, options, context)

            # Step 4: Generate recommendation (optional)
            recommendation = await self._generate_recommendation(
                category, options, context
            ) if len(options) > 1 else None

            result = ResearchResult(
                category=category,
                question=question,
                options=options,
                research_summary=summary,
                recommendation=recommendation
            )

            logger.info(
                "Research completed",
                category=category,
                options_count=len(options)
            )

            return result

        except Exception as e:
            logger.error("Research failed", category=category, error=str(e))
            raise

    async def _search_technologies(
        self,
        category: str,
        question: str,
        context: Dict
    ) -> List[Dict]:
        """
        Search for technologies using Tavily API.

        Args:
            category: Technology category
            question: Research question
            context: Project context

        Returns:
            List of search results
        """
        # Build search query
        project_type = context.get("project_type", "web application")
        tech_stack = context.get("tech_stack", {})

        query = f"{category} technology for {project_type}"
        if tech_stack:
            # Add existing tech stack to query for compatibility
            stack_str = ", ".join(tech_stack.values())
            query += f" compatible with {stack_str}"

        logger.info("Searching technologies", query=query)

        try:
            # Use Tavily search
            response = self.tavily_client.search(
                query=query,
                search_depth="advanced",  # Deep search for comprehensive results
                max_results=5,  # Reduced from 10 to save memory
                include_domains=[
                    "github.com",
                    "stackoverflow.com",
                    "npmjs.com",
                    "pypi.org",
                    "medium.com",
                    "dev.to"
                ]
            )

            results = response.get("results", [])
            logger.info("Search completed", results_count=len(results))

            return results

        except Exception as e:
            logger.error("Tavily search failed", error=str(e))
            # Return empty results to allow fallback to LLM knowledge
            return []

    async def _analyze_search_results(
        self,
        category: str,
        question: str,
        search_results: List[Dict],
        context: Dict,
        max_options: int
    ) -> List[TechnologyOption]:
        """
        Analyze search results with LLM to extract technology options.

        Args:
            category: Technology category
            question: Research question
            search_results: Tavily search results
            context: Project context
            max_options: Maximum options to return

        Returns:
            List of TechnologyOption objects
        """
        # Build prompt for LLM analysis
        prompt = self._build_analysis_prompt(
            category=category,
            question=question,
            search_results=search_results,
            context=context,
            max_options=max_options
        )

        # Generate analysis with LLM
        messages = [Message(role="user", content=prompt)]
        response = await self.llm_client.generate_json(
            messages=messages,
            max_tokens=2048
        )

        # Parse response into TechnologyOption objects
        options = []
        for option_data in response.get("options", []):
            try:
                option = TechnologyOption(**option_data)
                options.append(option)
            except Exception as e:
                logger.warning("Failed to parse technology option", error=str(e))
                continue

        logger.info("Analyzed search results", options_count=len(options))
        return options[:max_options]

    def _build_analysis_prompt(
        self,
        category: str,
        question: str,
        search_results: List[Dict],
        context: Dict,
        max_options: int
    ) -> str:
        """Build prompt for LLM analysis of search results."""
        # Extract context information
        project_type = context.get("project_type", "web application")
        tech_stack = context.get("tech_stack", {})
        requirements = context.get("requirements", "")

        # Format search results
        results_text = ""
        if search_results:
            for i, result in enumerate(search_results[:5], 1):
                results_text += f"\n{i}. **{result.get('title', 'Untitled')}**\n"
                results_text += f"   URL: {result.get('url', 'N/A')}\n"
                content = result.get("content", "No content") or "No content"
                if len(content) > 500:
                    content = content[:500] + "..."
                results_text += f"   Content: {content}\n"
        else:
            results_text = "No web search results available. Use your knowledge base."

        # Format tech stack
        stack_text = ""
        if tech_stack:
            stack_text = "\n".join([f"- {k}: {v}" for k, v in tech_stack.items()])
        else:
            stack_text = "Not specified"

        prompt = f"""You are a senior software architect researching technology options for a project.

**Project Context:**
- Project Type: {project_type}
- Current Tech Stack:
{stack_text}
- Requirements: {requirements}

**Research Category:** {category}
**Question:** {question}

**Web Search Results:**
{results_text}

**Task:**
Analyze the search results and your knowledge to identify the {max_options} best technology options for this category.

For each technology option, provide:
1. **technology_name**: Official name of the technology
2. **description**: Brief description (1-2 sentences)
3. **pros**: List of 3-5 advantages
4. **cons**: List of 3-5 disadvantages
5. **use_cases**: List of 2-3 ideal use cases
6. **popularity_score**: Score from 0-100 based on adoption and community
7. **learning_curve**: "low", "medium", or "high"
8. **documentation_quality**: "excellent", "good", "fair", or "poor"
9. **community_support**: "excellent", "good", "fair", or "poor"
10. **integration_complexity**: "low", "medium", or "high" (considering existing tech stack)
11. **sources**: List of URLs from search results (or ["knowledge_base"] if using your knowledge)

**Important:**
- Consider compatibility with the existing tech stack
- Prioritize mature, well-supported technologies
- Consider the project requirements
- Be objective about pros and cons
- Order options from most recommended to least recommended

Respond with JSON in this exact format:
{{
  "options": [
    {{
      "technology_name": "...",
      "description": "...",
      "pros": ["...", "..."],
      "cons": ["...", "..."],
      "use_cases": ["...", "..."],
      "popularity_score": 85.0,
      "learning_curve": "medium",
      "documentation_quality": "excellent",
      "community_support": "excellent",
      "integration_complexity": "low",
      "sources": ["https://...", "https://..."]
    }}
  ]
}}
"""
        return prompt

    async def _generate_summary(
        self,
        category: str,
        options: List[TechnologyOption],
        context: Dict
    ) -> str:
        """Generate research summary."""
        prompt = f"""Summarize the research findings for {category} technology options.

**Options Identified:**
{self._format_options_for_summary(options)}

**Project Context:**
- Project Type: {context.get('project_type', 'web application')}
- Tech Stack: {context.get('tech_stack', {})}

Write a brief 2-3 paragraph summary of the research findings, highlighting:
1. Overview of the options
2. Key differentiators between them
3. General considerations for this category

Keep it concise and informative.
"""

        messages = [Message(role="user", content=prompt)]
        response = await self.llm_client.generate(messages=messages, temperature=0.5)
        return response.content.strip()

    async def _generate_recommendation(
        self,
        category: str,
        options: List[TechnologyOption],
        context: Dict
    ) -> str:
        """Generate technology recommendation."""
        prompt = f"""Based on the research for {category}, recommend the best technology option.

**Options:**
{self._format_options_for_summary(options)}

**Project Context:**
- Project Type: {context.get('project_type', 'web application')}
- Tech Stack: {context.get('tech_stack', {})}
- Requirements: {context.get('requirements', '')}

Provide a brief recommendation (2-3 sentences) explaining which option is best and why, considering:
- Project requirements
- Tech stack compatibility
- Team expertise (prefer lower learning curve)
- Long-term maintainability

Be direct and actionable.
"""

        messages = [Message(role="user", content=prompt)]
        response = await self.llm_client.generate(messages=messages, temperature=0.3)
        return response.content.strip()

    def _format_options_for_summary(self, options: List[TechnologyOption]) -> str:
        """Format options for summary/recommendation prompts."""
        formatted = ""
        for i, opt in enumerate(options, 1):
            formatted += f"\n{i}. **{opt.technology_name}**\n"
            formatted += f"   Description: {opt.description}\n"
            formatted += f"   Pros: {', '.join(opt.pros[:3])}\n"
            formatted += f"   Cons: {', '.join(opt.cons[:3])}\n"
            formatted += f"   Popularity: {opt.popularity_score}/100\n"
            formatted += f"   Learning Curve: {opt.learning_curve}\n"
        return formatted


# ============= Helper Functions =============

async def research_technology_gap(
    category: str,
    question: str,
    context: Dict,
    max_options: int = 3
) -> ResearchResult:
    """
    Quick helper to research a technology gap.

    Args:
        category: Technology category
        question: Research question
        context: Project context
        max_options: Maximum options to return

    Returns:
        ResearchResult with options
    """
    researcher = TechnologyResearcher()
    return await researcher.research_category(
        category=category,
        question=question,
        context=context,
        max_options=max_options
    )
