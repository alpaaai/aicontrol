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
        input.tool_parameters[key] == val
    }
}

# Helper: true if the tool is on any blacklist
is_blacklisted if {
    some policy in input.policies
    policy.rule_type == "tool_blacklist"
    policy.action == "deny"
    input.tool_name in policy.condition.blocked_tools
    params_match(policy)
}

# Helper: true if the tool matches a review pattern
needs_review if {
    some policy in input.policies
    policy.rule_type == "tool_pattern"
    policy.action == "review"
    some pattern in policy.condition.tool_name_contains
    contains(input.tool_name, pattern)
}

# Deny if tool is on the blacklist (highest priority)
decision := "deny" if is_blacklisted

reason := "tool_blacklisted" if is_blacklisted

# Review if tool matches a pattern and is not blacklisted
decision := "review" if {
    not is_blacklisted
    needs_review
}

reason := "requires_human_review" if {
    not is_blacklisted
    needs_review
}
