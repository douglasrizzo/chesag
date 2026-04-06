from chesag.agents import AGENTS


def test_agent_registry_excludes_abstract_base_agent() -> None:
  assert "base" not in AGENTS
