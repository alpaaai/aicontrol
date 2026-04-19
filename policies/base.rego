package aicontrol

import future.keywords.every
import future.keywords.if
import future.keywords.in

default decision := "allow"
default reason := "default_allow"

# Helper: true when all parameter_match conditions pass (or none specified)
params_match(policy) if {
    not policy.condition.parameter_match
}

params_match(policy) if {
    every key, val in policy.condition.parameter_match {
        glob.match(val, [], input.tool_parameters[key])
    }
}

# Helper: true if tool is blacklisted with NO parameter conditions (global tool ban)
is_blacklisted if {
    some policy in input.policies
    policy.rule_type == "tool_denylist"
    policy.action == "deny"
    input.tool_name in policy.condition.blocked_tools
    not policy.condition.parameter_match
}

# Helper: true if tool matches AND parameter condition matches (parameter-level violation)
is_parameter_violation if {
    some policy in input.policies
    policy.rule_type == "tool_denylist"
    policy.action == "deny"
    input.tool_name in policy.condition.blocked_tools
    policy.condition.parameter_match
    params_match(policy)
}

# Helper: get the first violating parameter key=value string
violation_detail := detail if {
    some policy in input.policies
    policy.rule_type == "tool_denylist"
    policy.action == "deny"
    input.tool_name in policy.condition.blocked_tools
    policy.condition.parameter_match
    params_match(policy)
    some key, val in policy.condition.parameter_match
    detail := sprintf("parameter_policy_violation: %s=%v", [key, val])
}

# Helper: true if the tool matches a review pattern
needs_review if {
    some policy in input.policies
    policy.rule_type == "tool_pattern"
    policy.action == "review"
    some pattern in policy.condition.tool_name_contains
    contains(input.tool_name, pattern)
}

# Deny: global tool blacklist (highest priority)
decision := "deny" if is_blacklisted

reason := "tool_blacklisted" if is_blacklisted

# Deny: parameter-level violation (second priority)
decision := "deny" if {
    not is_blacklisted
    is_parameter_violation
}

reason := violation_detail if {
    not is_blacklisted
    is_parameter_violation
}

# Review if tool matches a pattern and is not denied
decision := "review" if {
    not is_blacklisted
    not is_parameter_violation
    needs_review
}

reason := "requires_human_review" if {
    not is_blacklisted
    not is_parameter_violation
    needs_review
}
