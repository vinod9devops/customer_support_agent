"""
Crew orchestrator - coordinates multiple agents to handle a customer support inquiry.
Equivalent to CrewAI's Crew class but using Claude API directly.
"""

import os
import time
import anthropic
from agents import Agent
from tools import TOOLS, execute_tool


class Crew:
    """Orchestrates a sequence of agents working on tasks."""

    def __init__(self, agents: list[Agent], tasks: list[dict], memory: bool = True, verbose: bool = False):
        self.agents = agents
        self.tasks = tasks
        self.memory = memory
        self.verbose = verbose
        self.client = anthropic.Anthropic(
            base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.ai.tech.gov.sg/platform/models"),
        )
        self.conversation_history: list[dict] = []  # shared memory across tasks

    def _call_with_retry(self, max_retries: int = 3, **kwargs):
        """Call Claude API with retry on rate limit errors."""
        for attempt in range(max_retries):
            try:
                return self.client.messages.create(**kwargs)
            except anthropic.RateLimitError as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 30 * (attempt + 1)  # 30s, 60s, 90s
                print(f"  ⏳ Rate limited. Waiting {wait_time}s before retry ({attempt + 1}/{max_retries})...")
                time.sleep(wait_time)

    def _run_agent(self, agent: Agent, task: dict, context: str = "") -> str:
        """Run a single agent on a task, handling tool use loops."""
        user_message = task["description"]
        if context:
            user_message = (
                f"## Previous Agent Output (for context)\n{context}\n\n"
                f"## Your Task\n{user_message}"
            )

        # Build message content (supports multimodal with images)
        attachments = task.get("attachments", [])
        if attachments:
            content_blocks = [{"type": "text", "text": user_message}]
            for att in attachments:
                if att["type"] == "image":
                    content_blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": att["media_type"],
                            "data": att["data"],
                        },
                    })
                    content_blocks.append({
                        "type": "text",
                        "text": f"[Above image is attachment: {att.get('filename', 'image')}]",
                    })
                elif att["type"] == "text":
                    content_blocks.append({"type": "text", "text": att["content"]})
            messages = [{"role": "user", "content": content_blocks}]
        else:
            messages = [{"role": "user", "content": user_message}]

        # Include tools only if the task specifies them
        task_tools = task.get("tools", agent.tools) or None

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🤖 Agent: {agent.role}")
            print(f"📋 Task: {task['description'][:100]}...")
            print(f"{'='*60}\n")

        # Agentic loop: keep calling Claude until we get a final text response
        while True:
            kwargs = {
                "model": "bedrock.claude-opus-4-6",
                "max_tokens": 4096,
                "system": agent.system_prompt,
                "messages": messages,
            }
            if task_tools:
                kwargs["tools"] = task_tools

            response = self._call_with_retry(**kwargs)

            # Check if the model wants to use a tool
            if response.stop_reason == "tool_use":
                # Process all tool calls in the response
                assistant_content = response.content
                messages.append({"role": "assistant", "content": assistant_content})

                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        if self.verbose:
                            print(f"  🔧 Using tool: {block.name}({block.input})")

                        result = execute_tool(block.name, block.input)

                        if self.verbose:
                            print(f"  ✅ Tool result: {result[:200]}...\n")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "user", "content": tool_results})
            else:
                # Final response - extract text
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text

                if self.verbose:
                    print(f"\n📝 Response from {agent.role}:")
                    print(f"{final_text[:500]}...\n" if len(final_text) > 500 else f"{final_text}\n")

                # Store in memory
                if self.memory:
                    self.conversation_history.append({
                        "agent": agent.role,
                        "task": task["description"][:200],
                        "response": final_text,
                    })

                return final_text

    def kickoff(self, inputs: dict) -> str:
        """
        Execute all tasks sequentially, passing context between agents.
        Variable substitution is done on task descriptions using `inputs`.
        """
        context = ""

        for i, task in enumerate(self.tasks):
            agent = task["agent"]

            # Substitute variables in task description and expected_output
            description = task["description"]
            for key, value in inputs.items():
                description = description.replace(f"{{{key}}}", value)

            resolved_task = {**task, "description": description}

            if self.verbose:
                print(f"\n{'#'*60}")
                print(f"  TASK {i+1}/{len(self.tasks)}")
                print(f"{'#'*60}")

            context = self._run_agent(agent, resolved_task, context=context if i > 0 else "")

        return context
