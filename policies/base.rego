package aicontrol

import future.keywords.every
import future.keywords.if
import future.keywords.in

default decision := "allow"
default reason := "default_allow"

# Helper: compare a single policy value against an actual parameter value.
# Uses glob only when val contains wildcard chars (* or ?); otherwise exact equality.
# The string "null" in a policy matches a JSON null parameter value.
param_value_matches(val, actual) if {
    not contains(val, "*")
    not contains(val, "?")
    actual == val
}

# String "null" in policy condition matches a JSON null actual value
param_value_matches("null", actual) if {
    actual == null
}

param_value_matches(val, actual) if {
    contains(val, "*")
    val != "*"
    glob.match(val, [], actual)
}

param_value_matches(val, actual) if {
    contains(val, "?")
    val != "?"
    glob.match(val, [], actual)
}

# Bare "*" or "?" — exact literal match only
param_value_matches("*", actual) if { actual == "*" }
param_value_matches("?", actual) if { actual == "?" }

# Helper: true when all parameter_match conditions pass (or none specified)
params_match(policy) if {
    not policy.condition.parameter_match
}

params_match(policy) if {
    every key, val in policy.condition.parameter_match {
        param_value_matches(val, input.tool_parameters[key])
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

# ── Compound sub-condition helpers ─────────────────────────────────────────────

# Sub-condition parameter_match passes when none defined or all values match
sub_condition_params_match(sub_cond) if {
    not sub_cond.parameter_match
}

sub_condition_params_match(sub_cond) if {
    every key, val in sub_cond.parameter_match {
        param_value_matches(val, input.tool_parameters[key])
    }
}

# Sub-condition numeric_conditions pass when none defined or all ops pass
sub_condition_numeric_match(sub_cond) if {
    not sub_cond.numeric_conditions
}

sub_condition_numeric_match(sub_cond) if {
    every cond in sub_cond.numeric_conditions {
        numeric_op_passes(cond.operator, input.tool_parameters[cond.parameter], cond.value)
    }
}

# A sub-condition passes when both its parameter_match and numeric_conditions pass
sub_condition_passes(sub_cond) if {
    sub_condition_params_match(sub_cond)
    sub_condition_numeric_match(sub_cond)
}

# Helper: true when ALL sub-conditions in all_of pass
all_of_match(policy) if {
    every sub_cond in policy.condition.all_of {
        sub_condition_passes(sub_cond)
    }
}

# Helper: true when ANY sub-condition in any_of passes
any_of_match(policy) if {
    some sub_cond in policy.condition.any_of
    sub_condition_passes(sub_cond)
}

# Per-policy compound violation check (used in is_compound_violation and violation detail)
policy_compound_violation(policy) if {
    policy.condition.all_of
    all_of_match(policy)
}

policy_compound_violation(policy) if {
    policy.condition.any_of
    any_of_match(policy)
}

# ── Tool name matching (primary name + aliases) ────────────────────────────────

# Helper: true if input.tool_name matches a policy's primary tool or any alias
tool_matches(policy) if {
    input.tool_name in policy.condition.blocked_tools
}

tool_matches(policy) if {
    policy.condition.tool_aliases
    input.tool_name in policy.condition.tool_aliases
}

# ── Primary violation helpers ──────────────────────────────────────────────────

# Helper: true if tool is blacklisted with NO conditions (global tool ban)
is_blacklisted if {
    some policy in input.policies
    policy.rule_type == "tool_denylist"
    policy.action == "deny"
    tool_matches(policy)
    not policy.condition.parameter_match
    not policy.condition.numeric_conditions
    not policy.condition.all_of
    not policy.condition.any_of
    not policy.condition.time_conditions
}

# Helper: true if tool matches AND parameter condition matches (parameter-level violation)
is_parameter_violation if {
    some policy in input.policies
    policy.rule_type == "tool_denylist"
    policy.action == "deny"
    tool_matches(policy)
    policy.condition.parameter_match
    params_match(policy)
}

# Helper: true if tool matches AND all numeric conditions match
is_numeric_violation if {
    some policy in input.policies
    policy.rule_type == "tool_denylist"
    policy.action == "deny"
    tool_matches(policy)
    policy.condition.numeric_conditions
    numeric_conditions_match(policy)
}

# Helper: true if tool matches AND compound all_of/any_of condition matches
is_compound_violation if {
    some policy in input.policies
    policy.rule_type == "tool_denylist"
    policy.action == "deny"
    tool_matches(policy)
    policy_compound_violation(policy)
}

# Helper: get the first violating parameter key=value string
violation_detail := detail if {
    details := {d |
        some policy in input.policies
        policy.rule_type == "tool_denylist"
        policy.action == "deny"
        tool_matches(policy)
        policy.condition.parameter_match
        params_match(policy)
        some key, val in policy.condition.parameter_match
        d := sprintf("parameter_policy_violation: %s=%v", [key, val])
    }
    count(details) > 0
    detail := min(details)
}

# Helper: get one violating numeric condition as a detail string
numeric_violation_detail := detail if {
    details := {d |
        some policy in input.policies
        policy.rule_type == "tool_denylist"
        policy.action == "deny"
        tool_matches(policy)
        policy.condition.numeric_conditions
        numeric_conditions_match(policy)
        some cond in policy.condition.numeric_conditions
        numeric_op_passes(cond.operator, input.tool_parameters[cond.parameter], cond.value)
        d := sprintf("numeric_policy_violation: %s %s %v", [cond.parameter, cond.operator, cond.value])
    }
    count(details) > 0
    detail := min(details)
}

# ── Temporal condition helpers ─────────────────────────────────────────────────

# Helper: current day of week is in the policy's deny_days list
day_is_denied(policy) if {
    policy.condition.time_conditions.deny_days
    input.current_time.day_of_week in policy.condition.time_conditions.deny_days
}

# Helper: current hour falls within the policy's deny_hours window (inclusive from, exclusive to)
hour_is_denied(policy) if {
    policy.condition.time_conditions.deny_hours
    input.current_time.hour >= policy.condition.time_conditions.deny_hours.from
    input.current_time.hour < policy.condition.time_conditions.deny_hours.to
}

# Per-policy time violation check (day or hour triggers the violation)
policy_time_violation(policy) if { day_is_denied(policy) }
policy_time_violation(policy) if { hour_is_denied(policy) }

# Helper: true if tool matches AND a time condition fires
is_time_violation if {
    some policy in input.policies
    policy.rule_type == "tool_denylist"
    policy.action == "deny"
    tool_matches(policy)
    policy.condition.time_conditions
    policy_time_violation(policy)
}

# Helper: detail string for time violation
time_violation_detail := detail if {
    details := {d |
        some policy in input.policies
        policy.rule_type == "tool_denylist"
        policy.action == "deny"
        tool_matches(policy)
        policy.condition.time_conditions
        policy_time_violation(policy)
        d := sprintf("time_policy_violation: %s", [policy.name])
    }
    count(details) > 0
    detail := min(details)
}

# Helper: get the policy name for the first matching compound violation
compound_violation_detail := detail if {
    details := {d |
        some policy in input.policies
        policy.rule_type == "tool_denylist"
        policy.action == "deny"
        tool_matches(policy)
        policy_compound_violation(policy)
        d := sprintf("compound_policy_violation: %s", [policy.name])
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

reason := "tool_denylisted" if is_blacklisted

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

# Deny: compound AND/OR violation (fourth priority)
decision := "deny" if {
    not is_blacklisted
    not is_parameter_violation
    not is_numeric_violation
    is_compound_violation
}

reason := compound_violation_detail if {
    not is_blacklisted
    not is_parameter_violation
    not is_numeric_violation
    is_compound_violation
}

# Deny: temporal condition violation (fifth priority)
decision := "deny" if {
    not is_blacklisted
    not is_parameter_violation
    not is_numeric_violation
    not is_compound_violation
    is_time_violation
}

reason := time_violation_detail if {
    not is_blacklisted
    not is_parameter_violation
    not is_numeric_violation
    not is_compound_violation
    is_time_violation
}

# Review if tool matches a pattern and is not denied
decision := "review" if {
    not is_blacklisted
    not is_parameter_violation
    not is_numeric_violation
    not is_compound_violation
    not is_time_violation
    needs_review
}

reason := "requires_human_review" if {
    not is_blacklisted
    not is_parameter_violation
    not is_numeric_violation
    not is_compound_violation
    not is_time_violation
    needs_review
}
