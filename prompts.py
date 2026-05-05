TEST_CASE_PROMPT = """You are a senior QA engineer with 10+ years of experience in behavior-driven development (BDD) and risk-based testing. 

Task: Given the user story and acceptance criteria below, generate comprehensive test cases

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
    "steps": "Clear, numbered, and reproducible actions in separate lines",
    "expected_result" : "The specific outcome that defines success against the label 'expected result' "
    "priority": "high|medium|low"
  }}
]"""


REQUIREMENTS_ANALYSIS_PROMPT = """You are a senior business analyst and QA lead. \
Analyse the following user story for requirements quality.
 
Story Key: {key}
Summary: {summary}
 
Description / Acceptance Criteria:
{description}
 
Evaluate across these 4 dimensions and return ONLY a valid JSON object, \
no markdown fences, no explanation:
 
{{
  "clarity": {{
    "score": <1-5>,
    "verdict": "pass|warn|fail",
    "issues": ["list of specific clarity issues, empty if none"],
    "suggestion": "one concrete improvement suggestion or empty string"
  }},
  "ambiguity": {{
    "score": <1-5>,
    "verdict": "pass|warn|fail",
    "issues": ["list of ambiguous terms or conditions, empty if none"],
    "suggestion": "one concrete improvement suggestion or empty string"
  }},
  "consistency": {{
    "score": <1-5>,
    "verdict": "pass|warn|fail",
    "issues": ["list of contradictions or inconsistencies, empty if none"],
    "suggestion": "one concrete improvement suggestion or empty string"
  }},
  "readability": {{
    "score": <1-5>,
    "verdict": "pass|warn|fail",
    "issues": ["list of readability problems, empty if none"],
    "suggestion": "one concrete improvement suggestion or empty string"
  }},
  "overall": {{
    "score": <1-5>,
    "verdict": "pass|warn|fail",
    "summary": "2-3 sentence overall assessment"
  }}
}}
 
Scoring guide: 5=excellent, 4=good, 3=acceptable, 2=needs work, 1=poor
Verdict guide: pass=score>=4, warn=score==3, fail=score<3"""
