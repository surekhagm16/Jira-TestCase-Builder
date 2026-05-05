# CAB Booking - AI Test Case Generator

AI-powered test case generation with Human-in-the-Loop (HITL) review.
Built with LangChain, LangGraph, RAG, and Streamlit.

## Setup

```bash
# 1. Clone / create the project folder
cd cab-test-gen

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your Jira URL, email, API token, and OpenAI key

# 5. Run the app
streamlit run app.py
```

## Getting your Jira API token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy and paste into .env or the UI

## How it works
1. Enter your Jira + OpenAI credentials in the UI
2. Type the epic key (e.g. SP-1) to process
3. The app fetches all child stories from Jira via API
4. For each story, GPT-4o generates test cases in Given/When/Then format
5. You review each test case — check/uncheck to approve or reject
6. You can regenerate for any story if the results aren't good
7. Approved test cases are written back to Jira as child Tasks
   labelled "ai-generated" and "test-case"

## Flow
Config → Fetch stories → Generate (per story) → HITL Review → Write to Jira → Done
