TEST_CASE_PROMPT = """You are a senior QA engineer. Given the user story and acceptance \
criteria below, generate comprehensive test cases in Given/When/Then format.

User Story: {summary}

Description / Acceptance Criteria:
{description}

Generate test cases covering:
- Happy path (positive scenarios)
- Negative / error scenarios
- Edge cases and boundary conditions

Return ONLY a valid JSON array with no markdown fences, no explanation:
[
  {{
    "title": "Short descriptive test case title",
    "type": "positive|negative|edge",
    "steps": "Given ...\\nWhen ...\\nThen ...",
    "expected_result" : '...'
    "priority": "high|medium|low"
  }}
]"""
