PLAN_SYSTEM = """You are a senior software engineer creating actionable engineering tasks from Acceptance Criteria (AC).
You must optimize for: (1) concrete implementation steps, (2) each task fits 1-4 hours, (3) minimal duplication across ACs.
Output MUST be valid JSON only. No markdown. No extra text.
"""

PLAN_USER = """Read the AC and propose work_units (not final tasks yet).
Rules:
- Each work_unit must fit 1-4 hours by itself.
- Prefer separating by "change surface": util / api / validation / db_migration / ui / test / logging_security / docs.
- DO NOT create DB work_unit unless AC truly requires persistence/schema changes.
- Include canonical_key for each work_unit (stable key to deduplicate across ACs).
- Max 6 work_units per AC. If more, merge related ones while still <=4h.

Return JSON:
{{
  "ac_index": {ac_index},
  "ac_text": {ac_text_json},
  "work_units": [
    {{
      "surface": "util|api|validation|db_migration|ui|test|logging_security|docs|ops",
      "title_hint": "short",
      "what_to_change": "specific modules/files/endpoint/schema involved",
      "acceptance_checks": ["...","..."],
      "estimate_hours": 1,
      "canonical_key": "e.g. util:auth:password_hash_bcrypt"
    }}
  ]
}}
"""

GENERATE_SYSTEM = """You convert work_units into Techkan-compatible tasks.
Output MUST be valid JSON only. No markdown. No extra text.
"""

GENERATE_USER = """Create tasks from work_units.
Rules:
- Each task must be 1-4 hours (integer).
- Task fields must match exactly:
  title, category, subcategory, status, priority, estimate_hours, assignee, related_task_titles, period, description, canonical_key, depends_on_keys, flags
- category must be "Task"
- status must be "Todo"
- subcategory must be one of: [Code][BE], [Code][FE], [Code][DB], [Test], [Doc], [Ops]
- priority: Low|Medium|High
- description must include:
  Goal, Changes (concrete), Acceptance checks (bullet-like)
- Use depends_on_keys to reference shared tasks when needed.

Input plan JSON:
{plan_json}

Return JSON:
{{
  "ac_index": {ac_index},
  "tasks": [
    {{
      "title": "...",
      "category": "Task",
      "subcategory": "[Code][BE]",
      "status": "Todo",
      "priority": "Medium",
      "estimate_hours": 2,
      "assignee": "",
      "related_task_titles": [],
      "period": "",
      "description": "Goal:...\\nChanges:...\\nAcceptance checks:...",
      "canonical_key": "...",
      "depends_on_keys": [],
      "flags": []
    }}
  ]
}}
"""

JUDGE_SYSTEM = """You are a strict reviewer. You must output JSON only. No extra text.
"""

JUDGE_USER = """Review the generated tasks for this AC with gate rules.
Gate rules (fail if any):
- any estimate_hours is outside 1-4
- any task is too vague (missing concrete change surface or acceptance checks)
- a task mixes multiple surfaces (util+api+db+migration+test all in one)
- duplication likely (canonical_key overlaps with registry keys)
- too many tasks: > {max_tasks_per_ac}

Return JSON:
{{
  "pass": true|false,
  "issues": [
    {{
      "type": "HOURS|VAGUE|MIXED_SURFACE|DUPLICATE|TOO_MANY",
      "detail": "..."
    }}
  ],
  "repair_instructions": "If fail, give concise fix instructions."
}}
"""

REPAIR_SYSTEM = """You rewrite tasks to satisfy gate rules. Output JSON only. No extra text.
"""

REPAIR_USER = """Fix the tasks using the judge issues and instructions.
Constraints:
- Keep tasks 1-4 hours.
- Split mixed-surface tasks into separate ones.
- Remove duplicates by referencing existing tasks via depends_on_keys.
- Ensure each description has Goal/Changes/Acceptance checks.
- Limit tasks to <= {max_tasks_per_ac}.

Registry keys already exist (do NOT re-create these):
{registry_keys_json}

Current tasks JSON:
{tasks_json}

Judge issues:
{issues_json}

Return JSON (same schema as Generate):
{{
  "ac_index": {ac_index},
  "tasks": [ ... ]
}}
"""