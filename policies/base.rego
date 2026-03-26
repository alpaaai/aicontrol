package aicontrol

import future.keywords.if
import future.keywords.in

default decision := "allow"
default reason := "default_allow"

# Deny if tool is on the blacklist
decision := "deny" if {
    some policy in input.policies
    policy.rule_type == "tool_blacklist"
    policy.action == "deny"
    input.tool_name in policy.condition.blocked_tools
}

reason := "tool_blacklisted" if {
    some policy in input.policies
    policy.rule_type == "tool_blacklist"
    policy.action == "deny"
    input.tool_name in policy.condition.blocked_tools
}

# Review if tool name matches a pattern
decision := "review" if {
    decision != "deny"
    some policy in input.policies
    policy.rule_type == "tool_pattern"
    policy.action == "review"
    some pattern in policy.condition.tool_name_contains
    contains(input.tool_name, pattern)
}

reason := "requires_human_review" if {
    decision != "deny"
    some policy in input.policies
    policy.rule_type == "tool_pattern"
    policy.action == "review"
    some pattern in policy.condition.tool_name_contains
    contains(input.tool_name, pattern)
}
