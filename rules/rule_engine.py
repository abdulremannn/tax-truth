import json
import operator

OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
    "in": lambda a, b: a in b,
    "truthy": lambda a, b: bool(a),
}


def _get(data: dict, path: str):
    val = data
    for part in path.split("."):
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val


def evaluate_condition(data: dict, condition: dict) -> bool:
    field = condition["field"]
    op = condition["op"]
    expected = condition.get("value")
    actual = _get(data, field)
    if actual is None:
        return False
    return OPS[op](actual, expected)


def evaluate_rule(data: dict, rule: dict) -> bool:
    """
    rule = {"all": [...conditions]} or {"any": [...conditions]}
    conditions can nest {"all":...} / {"any":...}
    """
    if "all" in rule:
        return all(_eval_node(data, n) for n in rule["all"])
    if "any" in rule:
        return any(_eval_node(data, n) for n in rule["any"])
    return evaluate_condition(data, rule)


def _eval_node(data: dict, node: dict) -> bool:
    if "all" in node or "any" in node:
        return evaluate_rule(data, node)
    return evaluate_condition(data, node)


def match_strategies(client_data: dict, strategies: list[dict]) -> list[dict]:
    """
    strategies: [{id, name, rule_definition}, ...]
    Returns matched strategies with reason.
    """
    matched = []
    for s in strategies:
        rule = s.get("rule_definition")
        if not rule:
            continue
        if evaluate_rule(client_data, rule):
            matched.append({"id": s["id"], "name": s["name"]})
    return matched


def load_strategies_from_file(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
