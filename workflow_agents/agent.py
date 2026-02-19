import os
import logging
import google.cloud.logging

from callback_logging import log_query_to_model, log_model_response
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.agents import SequentialAgent, LoopAgent, ParallelAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.langchain_tool import LangchainTool
from google.adk.models import Gemini
from google.genai import types

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv()

model_name = os.getenv("MODEL")
print(f"Using model: {model_name}")

RETRY_OPTIONS = types.HttpRetryOptions(initial_delay=1, attempts=6)

# ==========================================
# 0. Define Tools (เครื่องมือสำหรับ Agent)
# ==========================================

def append_to_state(
    tool_context: ToolContext, field: str, response: str
) -> dict[str, str]:
    """Append new output to an existing state key."""
    existing_state = tool_context.state.get(field, [])
    tool_context.state[field] = existing_state + [response]
    logging.info(f"[Added to {field}] {response}")
    return {"status": "success"}

def write_file(
    tool_context: ToolContext,
    directory: str,
    filename: str,
    content: str
) -> dict[str, str]:
    """Write text content to a file."""
    target_path = os.path.join(directory, filename)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info(f"[File Saved] {target_path}")
    return {"status": "success"}

def exit_loop(tool_context: ToolContext) -> dict[str, str]:
    """
    Call this tool ONLY when both sides have presented sufficient
    and balanced arguments to exit the loop.
    """
    logging.info("[Loop Exited] The Judge has determined the debate is balanced.")
    return {"status": "Loop exited successfully. Proceed to the verdict."}

wiki_tool = LangchainTool(tool=WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()))

# ==========================================
# Step 2: The Investigation (Parallel)
# ==========================================

admirer_agent = Agent(
    name="admirer_agent",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Researches positive achievements of the historical figure.",
    instruction="""
    You are 'The Admirer'. Research the historical figure or event in the PROMPT: { PROMPT? }
    
    INSTRUCTIONS:
    1. You MUST use your wikipedia tool.
    2. To find specific positive data, append keywords like ' achievements', ' successes', or ' legacy' to your search query.
    3. Gather factual, positive information.
    4. Use the 'append_to_state' tool to save your findings to the exact field 'pos_data'.
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[wiki_tool, append_to_state]
)

critic_agent = Agent(
    name="critic_agent",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Researches mistakes and controversies of the historical figure.",
    instruction="""
    You are 'The Critic'. Research the historical figure or event in the PROMPT: { PROMPT? }
    
    INSTRUCTIONS:
    1. You MUST use your wikipedia tool.
    2. To find specific negative data, append keywords like ' controversy', ' criticisms', or ' mistakes' to your search query.
    3. Gather factual, negative information.
    4. Use the 'append_to_state' tool to save your findings to the exact field 'neg_data'.
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[wiki_tool, append_to_state]
)

investigation_team = ParallelAgent(
    name="investigation_team",
    description="Searches for both positive and negative facts in parallel.",
    sub_agents=[admirer_agent, critic_agent]
)

# ==========================================
# Step 3: The Trial & Review (Loop)
# ==========================================

judge_logic_agent = Agent(
    name="judge_logic_agent",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Evaluates if the collected arguments are balanced and sufficient.",
    instruction="""
    You are 'The Judge'. Check the Session State to decide whether the debate is balanced.
    
    Subject: { PROMPT? }
    Positive Data (Admirer): { pos_data? }
    Negative Data (Critic): { neg_data? }
    
    INSTRUCTIONS:
    1. Check if BOTH 'pos_data' and 'neg_data' contain substantial, factual arguments.
    2. If the data is balanced and complete, you MUST call the tool 'exit_loop'.
    3. If one side is empty or insufficient (e.g., 'neg_data' has nothing), DO NOT call 'exit_loop'. Instead, provide a short text response asking the investigation_team to search again with better keywords.
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0),
    tools=[exit_loop]
)

trial_loop = LoopAgent(
    name="trial_loop",
    description="Loops between researchers and the judge until data is balanced.",
    sub_agents=[investigation_team, judge_logic_agent],
    max_iterations=3
)

# ==========================================
# Step 4: The Verdict (Output)
# ==========================================

verdict_agent = Agent(
    name="verdict_agent",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Creates a neutral report comparing the facts and saves it.",
    instruction="""
    You are the 'Final Reporter'. Review the complete and balanced data approved by The Judge.
    
    Subject: { PROMPT? }
    Positive Data: { pos_data? }
    Negative Data: { neg_data? }
    
    INSTRUCTIONS:
    1. Create a highly neutral, objective summary report comparing the factual achievements and controversies of the subject.
    2. Use the 'write_file' tool to save your report.
       - directory: "."
       - filename: "verdict_report.txt"
       - content: [Your detailed summary report]
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0),
    tools=[write_file]
)

historical_court_workflow = SequentialAgent(
    name="historical_court_workflow",
    description="Executes the trial loop and then generates the verdict.",
    sub_agents=[trial_loop, verdict_agent]
)

# ==========================================
# Step 1: The Inquiry (Sequential) - Root Agent
# ==========================================

root_agent = Agent(
    name="greeter",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Guides the user in starting the Mock Court.",
    instruction="""
    - You are the host of "The Historical Court".
    - Ask the user for a historical figure or event they want to put on trial (e.g., Genghis Khan, Cold War).
    - When they respond, use the 'append_to_state' tool to store their response exactly in the 'PROMPT' state key.
    - After saving to state, transfer to the 'historical_court_workflow' agent to begin the investigation.
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0),
    tools=[append_to_state],
    sub_agents=[historical_court_workflow]
)