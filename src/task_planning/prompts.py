# src/task_planning/prompts.py

PLAN_SYSTEM = """You are a senior software engineer.
You read ONE Acceptance Criterion (AC) and propose small work_units.
Output JSON only. No markdown. No extra text.
"""

# ※ .format() を使う場合は { } を {{ }} にする
PLAN_USER = """Read the AC and propose work_units (not final tasks yet).

Hard constraints:
- You MUST output 1 to {max_tasks} work_units only.
- Each work_unit must fit 1-4 hours.
- If the AC implies many surfaces, MERGE related work into fewer work_units while staying <=4h each.

Guidance (change surfaces):
- util / api / validation / db / test / logging_security / docs / ops / ui
- Prefer the minimum set of surfaces needed for the AC.
- Do NOT create DB work unless persistence/schema truly required.

Return JSON:
{{
  "work_units": [
    {{
      "title": "...",
      "surface": "util|api|validation|db|test|logging_security|docs|ops|ui",
      "what_to_change": "specific modules/files/endpoints/schema",
      "acceptance_checks": ["...","..."],
      "estimate_hours": 1,
      "dependencies": ["<other work_unit title>", "..."]
    }}
  ]
}}

AC:
{ac_text}
"""

GEN_SYSTEM = """You convert work_units into company-ready tasks.
Output JSON only. No markdown. No extra text.
"""

GEN_USER = """Create tasks from work_units.

Hard constraints:
- You MUST output 1 to {max_tasks} tasks only.
- Each task must be 1-4 hours (integer).
- Each task must be concrete: where/what/how + testable acceptance checks.
- If max_tasks is small (e.g., 2), INCLUDE docs as part of description instead of making a separate doc-only task.

Task schema:
{{
  "tasks":[
    {{
      "title":"...",
      "category":"Task",
      "subcategory":"[Code][BE]|[Code][FE]|[Code][DB]|[Test]|[Doc]|[Ops]",
      "status":"Todo",
      "priority":"Low|Medium|High",
      "estimate_hours":2,
      "assignee":"",
      "related_task_titles":[],
      "period":"",
      "description":"Goal:...\\nChanges:...\\nAcceptance checks:..."
    }}
  ]
}}

AC:
{ac_text}

Plan JSON:
{plan_json}
"""

REPAIR_SYSTEM = """You fix tasks based on issues. Output JSON only. No extra text."""

REPAIR_USER = """Fix the tasks using these issues.

Hard constraints:
- Output 1 to {max_tasks} tasks only.
- Each task must be 1-4 hours.
- Make tasks concrete (where/what/how) and add testable acceptance checks.
- If max_tasks is small, MERGE surfaces while staying <=4h (avoid splitting too much).

Issues:
{issues_text}

Current tasks JSON:
{tasks_json}

Return JSON:
{{"tasks":[...]}}
"""