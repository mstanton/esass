#!/usr/bin/env python3
"""MCP Server for local LLM skill execution with 3-tier fallback.

This server provides tools for:
- Executing ESASS skills via local LLM (FunctionGemma)
- Semantic pattern analysis
- Skill name generation

Tier hierarchy:
1. Local (Ollama/FunctionGemma) - Primary, free
2. HuggingFace Inference API - Fallback, cheap
3. Claude - Passthrough for complex tasks
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from config import Tier, get_config, set_config, LocalLLMConfig
from tier_router import TierRouter, get_router, RoutingResult, ExecutionResult
from ollama_client import get_ollama_client
from huggingface_client import get_huggingface_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("local-llm-mcp")

# Create MCP server
server = Server("local-llm-mcp")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="execute_skill",
            description="Execute an ESASS skill using local LLM with automatic tier fallback",
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of the skill to execute",
                    },
                    "skill_description": {
                        "type": "string",
                        "description": "Description or implementation summary of the skill",
                    },
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Skill capabilities for routing (e.g., file_operations, testing)",
                    },
                    "context": {
                        "type": "object",
                        "description": "Execution context (files, parameters, etc.)",
                    },
                },
                "required": ["skill_name", "skill_description"],
            },
        ),
        Tool(
            name="analyze_pattern",
            description="Analyze a tool usage pattern for semantic meaning and clustering",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_sequence": {
                        "type": "string",
                        "description": "The tool sequence pattern (e.g., 'Read(python) -> Grep -> Edit')",
                    },
                    "support": {
                        "type": "integer",
                        "description": "Number of times this pattern occurred",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0-1)",
                    },
                },
                "required": ["pattern_sequence"],
            },
        ),
        Tool(
            name="generate_skill_name",
            description="Generate a semantic skill name from a pattern sequence",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_sequence": {
                        "type": "string",
                        "description": "The tool sequence pattern",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Associated tags for context",
                    },
                },
                "required": ["pattern_sequence"],
            },
        ),
        Tool(
            name="check_availability",
            description="Check which LLM tiers are currently available",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_routing_stats",
            description="Get routing statistics and failure counts",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool call: {name}")
    logger.debug(f"Arguments: {json.dumps(arguments, indent=2)}")

    try:
        if name == "execute_skill":
            result = await _execute_skill(
                skill_name=arguments["skill_name"],
                skill_description=arguments["skill_description"],
                capabilities=arguments.get("capabilities", []),
                context=arguments.get("context", {}),
            )

        elif name == "analyze_pattern":
            result = await _analyze_pattern(
                pattern_sequence=arguments["pattern_sequence"],
                support=arguments.get("support", 1),
                confidence=arguments.get("confidence", 1.0),
            )

        elif name == "generate_skill_name":
            result = await _generate_skill_name(
                pattern_sequence=arguments["pattern_sequence"],
                tags=arguments.get("tags", []),
            )

        elif name == "check_availability":
            result = await _check_availability()

        elif name == "get_routing_stats":
            result = await _get_routing_stats()

        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.exception(f"Error in tool {name}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _execute_skill(
    skill_name: str,
    skill_description: str,
    capabilities: List[str],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a skill using the appropriate tier."""
    router = await get_router()

    # Estimate tokens (rough: 4 chars per token)
    context_str = json.dumps(context)
    estimated_tokens = (len(skill_description) + len(context_str)) // 4

    # Get routing decision
    routing = await router.route_skill(skill_name, capabilities, estimated_tokens)
    logger.info(f"Routing {skill_name} to {routing.tier.value}: {routing.details}")

    # Execute with fallback
    async def executor(tier: Tier) -> Dict[str, Any]:
        if tier == Tier.LOCAL:
            client = await get_ollama_client()
            return await client.execute_skill(skill_name, skill_description, context)
        elif tier == Tier.HUGGINGFACE:
            client = await get_huggingface_client()
            return await client.execute_skill(skill_name, skill_description, context)
        else:
            return {"passthrough": True, "tier": "claude"}

    result = await router.execute_with_fallback(routing, executor)

    return {
        "success": result.success,
        "tier_used": result.tier_used.value,
        "fallback_used": result.fallback_used,
        "routing_reason": routing.reason.value,
        "routing_details": routing.details,
        "content": result.content,
        "tokens_used": result.tokens_used,
        "error": result.error,
    }


async def _analyze_pattern(
    pattern_sequence: str,
    support: int,
    confidence: float,
) -> Dict[str, Any]:
    """Analyze a pattern for semantic meaning."""
    router = await get_router()

    # Pattern analysis is a local-first task
    routing = router.route_by_task_type("pattern_embedding")

    async def executor(tier: Tier) -> Dict[str, Any]:
        if tier == Tier.LOCAL:
            client = await get_ollama_client()
            return await client.analyze_pattern(pattern_sequence, support, confidence)
        elif tier == Tier.HUGGINGFACE:
            client = await get_huggingface_client()
            return await client.analyze_pattern(pattern_sequence, support, confidence)
        else:
            return {"passthrough": True, "tier": "claude"}

    result = await router.execute_with_fallback(routing, executor)

    return {
        "success": result.success,
        "tier_used": result.tier_used.value,
        "analysis": result.content,
        "error": result.error,
    }


async def _generate_skill_name(
    pattern_sequence: str,
    tags: List[str],
) -> Dict[str, Any]:
    """Generate a semantic skill name."""
    router = await get_router()

    # Skill naming is a local-first task
    routing = router.route_by_task_type("skill_execution")

    async def executor(tier: Tier) -> Dict[str, Any]:
        if tier == Tier.LOCAL:
            client = await get_ollama_client()
            name = await client.generate_skill_name(pattern_sequence, tags)
            return {"name": name, "success": True}
        elif tier == Tier.HUGGINGFACE:
            client = await get_huggingface_client()
            name = await client.generate_skill_name(pattern_sequence, tags)
            return {"name": name, "success": True}
        else:
            return {"passthrough": True, "tier": "claude"}

    result = await router.execute_with_fallback(routing, executor)

    if result.success and "name" in result.content:
        return {
            "success": True,
            "skill_name": result.content["name"],
            "tier_used": result.tier_used.value,
        }
    else:
        # Fallback to hash-based name
        fallback_name = f"pattern_{hash(pattern_sequence) % 10000:04x}_skill"
        return {
            "success": False,
            "skill_name": fallback_name,
            "tier_used": result.tier_used.value,
            "error": result.error,
        }


async def _check_availability() -> Dict[str, Any]:
    """Check tier availability."""
    router = await get_router()

    availability = {}
    for tier in [Tier.LOCAL, Tier.HUGGINGFACE, Tier.CLAUDE]:
        availability[tier.value] = await router.check_tier_availability(tier)

    return {
        "availability": availability,
        "config": {
            "ollama_endpoint": get_config().ollama_endpoint,
            "ollama_model": get_config().ollama_model,
            "hf_model": get_config().hf_model,
            "hf_token_set": bool(get_config().hf_token),
        },
    }


async def _get_routing_stats() -> Dict[str, Any]:
    """Get routing statistics."""
    router = await get_router()
    return router.get_stats()


async def main():
    """Run the MCP server."""
    logger.info("Starting local-llm-mcp server...")
    logger.info(f"Config: ollama={get_config().ollama_endpoint}, model={get_config().ollama_model}")

    # Check initial availability
    router = await get_router()
    for tier in [Tier.LOCAL, Tier.HUGGINGFACE]:
        available = await router.check_tier_availability(tier)
        logger.info(f"Tier {tier.value}: {'available' if available else 'unavailable'}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
