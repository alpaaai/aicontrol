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

# Helper: evaluate a single numeric operator
numeric_op_passes("gt", actual, threshold) if { actual > threshold }
numeric_op_passes("gte", actual, threshold) if { actual >= threshold }
numeric_op_passes("lt", actual, threshold) if { actual < threshold }
numeric_op_passes("lte", actual, threshold) if { actual <= threshold }
numeric_op_passes("eq", actual, threshold) if { actual == threshold }

# Helper: true when ALL numeric_conditions in a policy pass (AND logic)
numeric_conditions_match(policy) if {
    every cond in policy.condition.numeric_conditions {
        numeric_op_passes(cond.operator, input.tool_parameters[cond.parameter], cond.value)
    }
}

# Helper: true if tool is blacklisted with NO parameter or numeric conditions (global tool ban)
is_blacklisted if {
    some policy in input.policies
    policy.rule_type == "tool_denylist"
    policy.action == "deny"
    input.tool_name in policy.condition.blocked_tools
    not policy.condition.parameter_match
    not policy.condition.numeric_conditions
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

# Helper: true if tool matches AND all numeric conditions match
is_numeric_violation if {
    some policy in input.policies
    policy.rule_type == "tool_denylist"
    policy.action == "deny"
    input.tool_name in policy.condition.blocked_tools
    policy.condition.numeric_conditions
    numeric_conditions_match(policy)
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

# Helper: get one violating numeric condition as a detail string (min over set avoids multi-output conflict)
numeric_violation_detail := detail if {
    details := {d |
        some policy in input.policies
        policy.rule_type == "tool_denylist"
        policy.action == "deny"
        input.tool_name in policy.condition.blocked_tools
        policy.condition.numeric_conditions
        numeric_conditions_match(policy)
        some cond in policy.condition.numeric_conditions
        numeric_op_passes(cond.operator, input.tool_parameters[cond.parameter], cond.value)
        d := sprintf("numeric_policy_violation: %s %s %v", [cond.parameter, cond.operator, cond.value])
    }
    count(details) > 0
    detail := min(details)
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

# Deny: numeric condition violation (third priority)
decision := "deny" if {
    not is_blacklisted
    not is_parameter_violation
    is_numeric_violation
}

reason := numeric_violation_detail if {
    not is_blacklisted
    not is_parameter_violation
    is_numeric_violation
}

# Review if tool matches a pattern and is not denied
decision := "review" if {
    not is_blacklisted
    not is_parameter_violation
    not is_numeric_violation
    needs_review
}

reason := "requires_human_review" if {
    not is_blacklisted
    not is_parameter_violation
    not is_numeric_violation
    needs_review
}
