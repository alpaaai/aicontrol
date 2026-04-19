# Framework Integrations

Copy-paste wrappers for every major agent framework. Each pattern adds a single intercept call to the tool execution path — no changes to your agent logic, LLM provider, or infrastructure.

All patterns require the [Python universal wrapper](/docs/integration#python-universal-wrapper) or the TypeScript equivalent set up first, and the following environment variables:

```bash
AICONTROL_URL=http://your-aicontrol-host:8000
AICONTROL_TOKEN=your-agent-token
AGENT_NAME=your-agent-name          # optional but recommended
AGENT_ID=your-stable-agent-uuid     # optional but recommended
```

---

## LangChain (Python)

Subclass `GovernedTool` instead of `BaseTool`. Every `run()` call is intercepted automatically.

```python
# langchain_integration.py
import os, uuid, httpx
from langchain.tools import BaseTool
from typing import Any

AICONTROL_URL   = os.environ["AICONTROL_URL"]
AICONTROL_TOKEN = os.environ["AICONTROL_TOKEN"]
AGENT_NAME      = os.environ.get("AGENT_NAME", "langchain-agent")
AGENT_ID        = os.environ.get("AGENT_ID", str(uuid.uuid4()))


class GovernedTool(BaseTool):
    """Drop-in replacement for BaseTool. Subclass this for any governed tool."""
    session_id: str = ""
    _sequence: int = 0

    def _intercept(self, tool_input: dict) -> None:
        self._sequence += 1
        response = httpx.post(
            f"{AICONTROL_URL}/intercept",
            headers={"Authorization": f"Bearer {AICONTROL_TOKEN}"},
            json={
                "session_id": self.session_id,
                "agent_id": AGENT_ID,
                "agent_name": AGENT_NAME,
                "tool_name": self.name,
                "tool_parameters": tool_input,
                "sequence_number": self._sequence,
            },
            timeout=5.0,
        )
        response.raise_for_status()
        result = response.json()
        if result["decision"] == "deny":
            raise ValueError(f"[AIControl] Tool '{self.name}' denied: {result['reason']}")
        if result["decision"] == "review":
            raise ValueError(f"[AIControl] Human review required. Review ID: {result['review_id']}")

    def _run(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    def run(self, tool_input: str | dict, **kwargs) -> Any:
        params = {"input": tool_input} if isinstance(tool_input, str) else tool_input
        self._intercept(params)
        return super().run(tool_input, **kwargs)


# ── Define your tool ──────────────────────────────────────────────────────────
class QueryDatabaseTool(GovernedTool):
    name = "query_database"
    description = "Query the customer database"

    def _run(self, table: str, limit: int = 100) -> str:
        return f"Results from {table}"   # your actual implementation


# ── Wire into a LangChain agent ───────────────────────────────────────────────
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain import hub

session_id = str(uuid.uuid4())
tool = QueryDatabaseTool(session_id=session_id)

llm = ChatOpenAI(model="gpt-4o")
prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm, [tool], prompt)
agent_executor = AgentExecutor(agent=agent, tools=[tool], verbose=True)
agent_executor.invoke({"input": "Query the customers table"})
```

**Alternative — wrap existing tools without subclassing:**

```python
from langchain.tools import Tool
from aicontrol import intercept

def make_governed(tool_fn, tool_name: str, session_id: str):
    call_count = {"n": 0}
    def governed_fn(*args, **kwargs):
        call_count["n"] += 1
        intercept(
            tool_name=tool_name,
            tool_parameters={"args": args, **kwargs},
            session_id=session_id,
            sequence_number=call_count["n"],
        )
        return tool_fn(*args, **kwargs)
    return Tool(name=tool_name, func=governed_fn, description="")

session_id = str(uuid.uuid4())
governed_query = make_governed(query_database, "query_database", session_id)
```

---

## CrewAI (Python)

Subclass `GovernedCrewTool` instead of `BaseTool`.

```python
# crewai_integration.py
import os, uuid, httpx
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from pydantic import Field
from typing import Any

AICONTROL_URL   = os.environ["AICONTROL_URL"]
AICONTROL_TOKEN = os.environ["AICONTROL_TOKEN"]
AGENT_NAME      = os.environ.get("AGENT_NAME", "crewai-agent")
AGENT_ID        = os.environ.get("AGENT_ID", str(uuid.uuid4()))


class GovernedCrewTool(BaseTool):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    _call_count: int = 0

    def _intercept(self, params: dict):
        self._call_count += 1
        response = httpx.post(
            f"{AICONTROL_URL}/intercept",
            headers={"Authorization": f"Bearer {AICONTROL_TOKEN}"},
            json={
                "session_id": self.session_id,
                "agent_id": AGENT_ID,
                "agent_name": AGENT_NAME,
                "tool_name": self.name,
                "tool_parameters": params,
                "sequence_number": self._call_count,
            },
            timeout=5.0,
        )
        response.raise_for_status()
        result = response.json()
        if result["decision"] == "deny":
            return f"[BLOCKED] Tool '{self.name}' denied: {result['reason']}"
        if result["decision"] == "review":
            return f"[PENDING] Human review required. Review ID: {result['review_id']}"
        return None

    def _run(self, **kwargs) -> Any:
        raise NotImplementedError

    def run(self, **kwargs) -> Any:
        block_message = self._intercept(kwargs)
        if block_message:
            return block_message
        return self._run(**kwargs)


# ── Define your tool ──────────────────────────────────────────────────────────
class QueryDatabaseTool(GovernedCrewTool):
    name: str = "query_database"
    description: str = "Query the customer database by table name"

    def _run(self, table: str, limit: int = 100) -> str:
        return f"Results from {table}"   # your actual implementation


# ── Wire into a Crew ──────────────────────────────────────────────────────────
session_id = str(uuid.uuid4())
tool = QueryDatabaseTool(session_id=session_id)

analyst = Agent(
    role="Data Analyst",
    goal="Analyze customer data",
    backstory="You analyze customer records.",
    tools=[tool],
)

task = Task(
    description="Query the customers table and summarize results",
    agent=analyst,
    expected_output="A summary of customer records",
)

Crew(agents=[analyst], tasks=[task]).kickoff()
```

---

## AutoGen / Microsoft AutoGen (Python)

Wrap the function before registering it with the agent.

```python
# autogen_integration.py
import os, uuid, httpx, autogen
from functools import wraps

AICONTROL_URL   = os.environ["AICONTROL_URL"]
AICONTROL_TOKEN = os.environ["AICONTROL_TOKEN"]
AGENT_NAME      = os.environ.get("AGENT_NAME", "autogen-agent")
AGENT_ID        = os.environ.get("AGENT_ID", str(uuid.uuid4()))


def governed(tool_name: str, session_id: str):
    """Decorator for AutoGen tool functions."""
    call_count = {"n": 0}
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            call_count["n"] += 1
            response = httpx.post(
                f"{AICONTROL_URL}/intercept",
                headers={"Authorization": f"Bearer {AICONTROL_TOKEN}"},
                json={
                    "session_id": session_id,
                    "agent_id": AGENT_ID,
                    "agent_name": AGENT_NAME,
                    "tool_name": tool_name,
                    "tool_parameters": {**kwargs},
                    "sequence_number": call_count["n"],
                },
                timeout=5.0,
            )
            response.raise_for_status()
            result = response.json()
            if result["decision"] == "deny":
                return f"[BLOCKED] {result['reason']}"
            if result["decision"] == "review":
                return f"[PENDING REVIEW] Review ID: {result['review_id']}"
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ── Wire into AutoGen ─────────────────────────────────────────────────────────
session_id = str(uuid.uuid4())

assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]},
)
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

@governed("query_database", session_id)
def query_database(table: str, limit: int = 100) -> str:
    return f"Results from {table}"   # your actual implementation

autogen.register_function(
    query_database,
    caller=assistant,
    executor=user_proxy,
    name="query_database",
    description="Query the customer database",
)

user_proxy.initiate_chat(assistant, message="Query the customers table.")
```

---

## OpenAI Agents SDK (Python)

Intercept inside the `@function_tool` body before executing.

```python
# openai_agents_integration.py
import os, uuid, httpx
from agents import Agent, Runner, function_tool

AICONTROL_URL   = os.environ["AICONTROL_URL"]
AICONTROL_TOKEN = os.environ["AICONTROL_TOKEN"]
AGENT_NAME      = os.environ.get("AGENT_NAME", "openai-agent")
AGENT_ID        = os.environ.get("AGENT_ID", str(uuid.uuid4()))

session_id  = str(uuid.uuid4())
_call_count = 0


def _intercept(tool_name: str, params: dict) -> str | None:
    global _call_count
    _call_count += 1
    response = httpx.post(
        f"{AICONTROL_URL}/intercept",
        headers={"Authorization": f"Bearer {AICONTROL_TOKEN}"},
        json={
            "session_id": session_id,
            "agent_id": AGENT_ID,
            "agent_name": AGENT_NAME,
            "tool_name": tool_name,
            "tool_parameters": params,
            "sequence_number": _call_count,
        },
        timeout=5.0,
    )
    response.raise_for_status()
    result = response.json()
    if result["decision"] == "deny":
        return f"[BLOCKED] {result['reason']}"
    if result["decision"] == "review":
        return f"[PENDING] Human review required. Review ID: {result['review_id']}"
    return None


@function_tool
def query_database(table: str, limit: int = 100) -> str:
    """Query the customer database."""
    blocked = _intercept("query_database", {"table": table, "limit": limit})
    if blocked:
        return blocked
    return f"Results from {table}"   # your actual implementation


agent = Agent(
    name=AGENT_NAME,
    instructions="You are a data analyst.",
    tools=[query_database],
)

result = Runner.run_sync(agent, "Query the customers table")
print(result.final_output)
```

---

## LangGraph (Python)

Call `governed_tool_call()` inside each node before executing the tool.

```python
# langgraph_integration.py
import os, uuid, httpx
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from typing import TypedDict, Annotated
import operator

AICONTROL_URL   = os.environ["AICONTROL_URL"]
AICONTROL_TOKEN = os.environ["AICONTROL_TOKEN"]
AGENT_NAME      = os.environ.get("AGENT_NAME", "langgraph-agent")
AGENT_ID        = os.environ.get("AGENT_ID", str(uuid.uuid4()))


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    session_id: str
    sequence_number: int


def governed_tool_call(tool_name: str, tool_parameters: dict, state: AgentState):
    """Call before executing any tool in a LangGraph node."""
    response = httpx.post(
        f"{AICONTROL_URL}/intercept",
        headers={"Authorization": f"Bearer {AICONTROL_TOKEN}"},
        json={
            "session_id": state["session_id"],
            "agent_id": AGENT_ID,
            "agent_name": AGENT_NAME,
            "tool_name": tool_name,
            "tool_parameters": tool_parameters,
            "sequence_number": state["sequence_number"],
        },
        timeout=5.0,
    )
    response.raise_for_status()
    result = response.json()
    if result["decision"] == "deny":
        return f"[BLOCKED] {result['reason']}"
    if result["decision"] == "review":
        return f"[PENDING] Review ID: {result['review_id']}"
    return result   # allow


# ── Example node ──────────────────────────────────────────────────────────────
def query_node(state: AgentState) -> AgentState:
    result = governed_tool_call(
        tool_name="query_database",
        tool_parameters={"table": "customers", "limit": 100},
        state=state,
    )
    if isinstance(result, str):
        message = AIMessage(content=result)   # blocked or pending
    else:
        data = run_query("customers", 100)    # your actual implementation
        message = AIMessage(content=str(data))

    return {
        "messages": [message],
        "session_id": state["session_id"],
        "sequence_number": state["sequence_number"] + 1,
    }


builder = StateGraph(AgentState)
builder.add_node("query", query_node)
builder.set_entry_point("query")
builder.add_edge("query", END)
graph = builder.compile()

graph.invoke({
    "messages": [HumanMessage(content="Query the customers table")],
    "session_id": str(uuid.uuid4()),
    "sequence_number": 1,
})
```

---

## Vercel AI SDK (TypeScript)

Wrap any `tool()` call with `governedTool()`.

```typescript
// vercel_ai_integration.ts
import { tool } from 'ai';
import { z } from 'zod';
import { intercept, PolicyViolationError } from './aicontrol';
import { v4 as uuidv4 } from 'uuid';

const sessionId = uuidv4();
let sequenceNumber = 0;

function governedTool<T extends z.ZodType>(config: {
  description: string;
  parameters: T;
  toolName: string;
  execute: (params: z.infer<T>) => Promise<string>;
}) {
  return tool({
    description: config.description,
    parameters: config.parameters,
    execute: async (params) => {
      sequenceNumber++;
      try {
        await intercept({
          toolName: config.toolName,
          toolParameters: params as Record<string, unknown>,
          sessionId,
          sequenceNumber,
        });
      } catch (e) {
        if (e instanceof PolicyViolationError) {
          return `[BLOCKED] ${e.reason}`;
        }
        throw e;
      }
      return config.execute(params);
    },
  });
}

export const queryDatabaseTool = governedTool({
  toolName: 'query_database',
  description: 'Query the customer database',
  parameters: z.object({
    table: z.string(),
    limit: z.number().default(100),
  }),
  execute: async ({ table, limit }) => {
    return `Results from ${table}`;   // your actual implementation
  },
});
```

---

## MCP (Model Context Protocol) — Python Server

Add governance at the MCP server level. Every tool registered with the server is automatically governed — no per-tool changes needed.

```python
# mcp_governed_server.py
import os, uuid, httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

AICONTROL_URL   = os.environ["AICONTROL_URL"]
AICONTROL_TOKEN = os.environ["AICONTROL_TOKEN"]
AGENT_NAME      = os.environ.get("AGENT_NAME", "mcp-agent")
AGENT_ID        = os.environ.get("AGENT_ID", str(uuid.uuid4()))

app = Server("governed-mcp-server")
_session_id = str(uuid.uuid4())
_call_count = 0


def _intercept(tool_name: str, params: dict) -> types.TextContent | None:
    global _call_count
    _call_count += 1
    response = httpx.post(
        f"{AICONTROL_URL}/intercept",
        headers={"Authorization": f"Bearer {AICONTROL_TOKEN}"},
        json={
            "session_id": _session_id,
            "agent_id": AGENT_ID,
            "agent_name": AGENT_NAME,
            "tool_name": tool_name,
            "tool_parameters": params,
            "sequence_number": _call_count,
        },
        timeout=5.0,
    )
    response.raise_for_status()
    result = response.json()
    if result["decision"] == "deny":
        return types.TextContent(type="text", text=f"[BLOCKED] Tool '{tool_name}' denied: {result['reason']}")
    if result["decision"] == "review":
        return types.TextContent(type="text", text=f"[PENDING REVIEW] Review ID: {result['review_id']}")
    return None


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="query_database",
            description="Query the customer database",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {"type": "string"},
                    "limit": {"type": "integer", "default": 100},
                },
                "required": ["table"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    blocked = _intercept(name, arguments)
    if blocked:
        return [blocked]
    # execute the actual tool
    if name == "query_database":
        return [types.TextContent(type="text", text=f"Results from {arguments['table']}")]
    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## TypeScript / Node.js — Universal

Drop `aicontrol.ts` into your project. Works with any Node.js agent framework.

```typescript
// aicontrol.ts
import { v4 as uuidv4 } from 'uuid';

const AICONTROL_URL   = process.env.AICONTROL_URL!;
const AICONTROL_TOKEN = process.env.AICONTROL_TOKEN!;
const AGENT_NAME      = process.env.AGENT_NAME ?? 'node-agent';
const AGENT_ID        = process.env.AGENT_ID   ?? uuidv4();


export class PolicyViolationError extends Error {
  constructor(public reason: string) {
    super(`Tool denied by policy: ${reason}`);
  }
}

export class HumanReviewRequiredError extends Error {
  constructor(public reviewId: string) {
    super(`Human review required. Review ID: ${reviewId}`);
  }
}

export async function intercept(params: {
  toolName: string;
  toolParameters: Record<string, unknown>;
  sessionId: string;
  sequenceNumber: number;
}): Promise<{ auditEventId: string; durationMs: number }> {
  const response = await fetch(`${AICONTROL_URL}/intercept`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${AICONTROL_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id:      params.sessionId,
      agent_id:        AGENT_ID,
      agent_name:      AGENT_NAME,
      tool_name:       params.toolName,
      tool_parameters: params.toolParameters,
      sequence_number: params.sequenceNumber,
    }),
  });

  if (!response.ok) throw new Error(`AIControl error: ${response.status}`);

  const result = await response.json();

  if (result.decision === 'deny')   throw new PolicyViolationError(result.reason);
  if (result.decision === 'review') throw new HumanReviewRequiredError(result.review_id);

  return { auditEventId: result.audit_event_id, durationMs: result.duration_ms };
}


export function governed<T extends unknown[], R>(
  toolName: string,
  fn: (...args: T) => Promise<R>,
) {
  let callCount = 0;
  return async (sessionId: string, ...args: T): Promise<R> => {
    callCount++;
    await intercept({ toolName, toolParameters: { args }, sessionId, sequenceNumber: callCount });
    return fn(...args);
  };
}


// ── Usage ─────────────────────────────────────────────────────────────────────
async function queryDatabase(table: string, limit: number): Promise<string> {
  return `Results from ${table}`;   // your actual implementation
}

const governedQuery = governed('query_database', queryDatabase);

try {
  const result = await governedQuery(uuidv4(), 'customers', 100);
} catch (e) {
  if (e instanceof PolicyViolationError) console.error('Blocked:', e.reason);
}
```
