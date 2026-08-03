"""LangGraph wiring for single agent-run execution."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.graphs.contracts import AgentGraphStateDict
from app.graphs.nodes import (
    build_prompt_node,
    final_response_node,
    handoff_gate_node,
    handoff_record_node,
    llm_call_node,
    llm_follow_up_node,
    memory_load_node,
    tool_execute_node,
    tool_finalize_node,
    tool_prepare_node,
)
from app.graphs.routing import (
    route_after_handoff_gate,
    route_after_llm_call,
    route_after_llm_follow_up,
    route_after_tool_execute,
    route_after_tool_finalize,
    route_after_tool_prepare,
)


def build_agent_graph() -> StateGraph:
    builder = StateGraph(AgentGraphStateDict)
    builder.add_node("memory_load", memory_load_node)
    builder.add_node("handoff_gate", handoff_gate_node)
    builder.add_node("handoff_record", handoff_record_node)
    builder.add_node("build_prompt", build_prompt_node)
    builder.add_node("llm_call", llm_call_node)
    builder.add_node("tool_prepare", tool_prepare_node)
    builder.add_node("tool_execute", tool_execute_node)
    builder.add_node("tool_finalize", tool_finalize_node)
    builder.add_node("llm_follow_up", llm_follow_up_node)
    builder.add_node("final_response", final_response_node)

    builder.add_edge(START, "memory_load")
    builder.add_edge("memory_load", "handoff_gate")
    builder.add_conditional_edges(
        "handoff_gate",
        route_after_handoff_gate,
        {
            "handoff_record": "handoff_record",
            "build_prompt": "build_prompt",
            "final_response": "final_response",
        },
    )
    builder.add_edge("handoff_record", END)
    builder.add_edge("build_prompt", "llm_call")
    builder.add_conditional_edges(
        "llm_call",
        route_after_llm_call,
        {
            "tool_prepare": "tool_prepare",
            "final_response": "final_response",
        },
    )
    builder.add_conditional_edges(
        "tool_prepare",
        route_after_tool_prepare,
        {
            "tool_execute": "tool_execute",
            "final_response": "final_response",
        },
    )
    builder.add_conditional_edges(
        "tool_execute",
        route_after_tool_execute,
        {
            "tool_finalize": "tool_finalize",
            "final_response": "final_response",
        },
    )
    builder.add_conditional_edges(
        "tool_finalize",
        route_after_tool_finalize,
        {
            "llm_follow_up": "llm_follow_up",
            "final_response": "final_response",
        },
    )
    builder.add_conditional_edges(
        "llm_follow_up",
        route_after_llm_follow_up,
        {"final_response": "final_response"},
    )
    builder.add_edge("final_response", END)
    return builder


@lru_cache
def get_compiled_agent_graph():
    return build_agent_graph().compile()


def clear_compiled_agent_graph_cache() -> None:
    get_compiled_agent_graph.cache_clear()
