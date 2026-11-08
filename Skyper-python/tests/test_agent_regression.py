from app.evaluation.agent_eval import EvaluationCase, default_cases, evaluate_trace


def test_default_regression_scenarios_pass():
    from app.evaluation.runner import SAMPLE_TRACES

    results = [evaluate_trace(case, SAMPLE_TRACES[case.name]) for case in default_cases()]
    assert all(result.passed for result in results), results


def test_destructive_tool_without_confirmation_fails():
    case = EvaluationCase(
        "delete_needs_confirmation",
        "ADMIN",
        ("delete_document",),
        {"delete_document": ("document_id",)},
        ("delete_document",),
    )
    result = evaluate_trace(case, [{"event": "tool_start", "data": {"name": "delete_document", "args": {"document_id": 7}}}])
    assert not result.passed
    assert "without confirmation" in result.failures[0]


def test_non_admin_write_is_rejected():
    case = default_cases()[2]
    result = evaluate_trace(case, [
        {"event": "tool_start", "data": {"name": "delete_document", "args": {"document_id": 7}}},
        {"event": "tool_end", "data": {"name": "delete_document", "status": "denied"}},
    ])
    assert result.passed

