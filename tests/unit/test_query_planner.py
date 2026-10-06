from packages.reasoning.planner import QueryPlanner


def test_query_planner_person_and_decision():
    planner = QueryPlanner()
    plan = planner.plan_query("What did Rahul decide about authentication last month?")
    assert plan.person == "Rahul"
    assert plan.topic == "Authentication"
    assert plan.type == "decision"
    assert plan.time_range == "last month"


def test_query_planner_entities_and_historical_reasoning():
    planner = QueryPlanner()
    plan = planner.plan_query("Why are we using PostgreSQL instead of MongoDB?")
    assert "PostgreSQL" in plan.entities
    assert "MongoDB" in plan.entities
    assert plan.type == "decision"
    assert plan.intent == "historical_reasoning"


def test_query_planner_issues_and_actions():
    planner = QueryPlanner()
    plan1 = planner.plan_query("What timeout issues are unresolved in Redis?")
    assert plan1.type == "issue"
    assert "Redis" in plan1.entities
    assert plan1.intent == "issue_tracking"

    plan2 = planner.plan_query("What actions did Priya commit to by Friday?")
    assert plan2.person == "Priya"
    assert plan2.type == "action"
    assert plan2.time_range == "by friday"
