from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    decision_node,
    enforcement_node,
    prediction_node,
    policy_generation_node,
    reward_node,
    simulation_node,
    telemetry_node,
)
from app.agents.state import AgentState


def build_agent_graph() -> StateGraph:
    """
    Construct the LangGraph StateGraph describing the agent's reasoning flow.
    """
    graph = StateGraph(AgentState)

    graph.add_node("telemetry", telemetry_node)
    graph.add_node("prediction", prediction_node)
    graph.add_node("policy_generation", policy_generation_node)
    graph.add_node("simulation", simulation_node)
    graph.add_node("decision", decision_node)
    graph.add_node("enforcement", enforcement_node)
    graph.add_node("reward", reward_node)

    graph.set_entry_point("telemetry")

    graph.add_edge("telemetry", "prediction")
    graph.add_edge("prediction", "policy_generation")
    graph.add_edge("policy_generation", "simulation")
    graph.add_edge("simulation", "decision")
    graph.add_edge("decision", "enforcement")
    graph.add_edge("enforcement", "reward")
    graph.add_edge("reward", END)

    return graph


# Compile a singleton graph instance for reuse.
_compiled_graph = build_agent_graph().compile()


def get_compiled_graph():
    return _compiled_graph

