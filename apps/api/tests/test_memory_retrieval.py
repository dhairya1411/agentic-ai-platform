"""Memory authorization and hybrid ranking tests require no external vector service."""

from uuid import uuid4

from agentic_ai_api.memory.retrieval import MemoryRecord, access_allowed, hybrid_rank


def test_access_requires_all_tags_and_project_scope() -> None:
    project, other_project = uuid4(), uuid4()
    record = MemoryRecord(uuid4(), "Jira ABC-1 is blocked", "jira", project, frozenset({"engineering", "lead"}))
    assert access_allowed(record, frozenset({"engineering", "lead"}), project)
    assert not access_allowed(record, frozenset({"engineering"}), project)
    assert not access_allowed(record, frozenset({"engineering", "lead"}), other_project)


def test_hybrid_rank_excludes_unauthorized_memory_and_rewards_keyword_match() -> None:
    allowed = MemoryRecord(uuid4(), "Jira ABC-1 is blocked by frontend", "jira", None, frozenset())
    restricted = MemoryRecord(uuid4(), "Payroll budget is blocked", "finance", None, frozenset({"finance"}))
    hits = hybrid_rank("Why is ABC-1 blocked?", [(allowed, 0.8), (restricted, 0.99)], frozenset(), None, 5)
    assert [hit.memory_id for hit in hits] == [allowed.id]
    assert hits[0].lexical_score > 0
