from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import asdict
from typing import Any

from agent_router import AgentRouter
from agents.agent_factory import AgentFactory
from agents.agent_manager import AgentManager
from agents.coding_agent import CodingAgent
from agents.critic_agent import CriticAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.memory_agent import MemoryAgent
from agents.planner_agent import PlannerAgent
from agents.research_agent import ResearchAgent
from agents.task_agent import TaskAgent
from agents.vision_agent import VisionAgent
from agents.contracts import AgentOutcome, OrchestrationResult
from agents.base_agent import BaseAgent
from context_bus import ContextBus
from agent_registry import AgentRegistry
from conversation import Conversation
from critic import Critic
from execution_loop import ExecutionLoop
from memory import Memory
from memory_extractor import MemoryExtractor
from memory_validator import MemoryValidator
from normalizer import Normalizer
from planner import Planner
from conversation_summarizer import ConversationSummarizer
from research.pipeline import ResearchPipeline
from tool_executor import ToolExecutor
from tools import tool_manager


class Orchestrator:
    def __init__(
        self,
        *,
        model: str = "qwen2.5:7b",
        registry: AgentRegistry | None = None,
        router: AgentRouter | None = None,
        context_bus: ContextBus | None = None,
        planner_cls=Planner,
        critic_cls=Critic,
        execution_loop_cls=ExecutionLoop,
        research_pipeline_cls=ResearchPipeline,
        memory_cls=Memory,
        extractor_cls=MemoryExtractor,
        validator_cls=MemoryValidator,
        summarizer_cls=ConversationSummarizer,
        normalizer_cls=Normalizer,
        tool_executor_cls=ToolExecutor,
        tool_manager_obj=tool_manager,
        knowledge_store: Any | None = None,
    ):
        self.model = model
        self.registry = registry if registry is not None else AgentRegistry()
        self.context_bus = context_bus if context_bus is not None else ContextBus()
        self.router = router if router is not None else AgentRouter(self.registry)
        self.manager = AgentManager(self.registry)
        self.factory = AgentFactory(self.registry)
        self.memory = memory_cls()
        self.extractor = extractor_cls()
        self.validator = validator_cls()
        self.summarizer = summarizer_cls()
        self.normalizer = normalizer_cls()
        self.planner = planner_cls(model=model)
        self.critic = critic_cls(model=model)
        self.research_pipeline = research_pipeline_cls(model=model, memory=self.memory)
        self.execution_loop = execution_loop_cls(
            model=model,
            tool_executor=tool_executor_cls(),
            tool_manager=tool_manager_obj,
            critic=self.critic,
            research_pipeline=self.research_pipeline,
        )
        self.conversation = Conversation(self._system_prompt(tool_manager_obj))
        self.tool_manager = tool_manager_obj
        self.knowledge_store = knowledge_store
        self.last_plan = None
        self.last_execution = None
        self.last_reflection = None
        self.last_research_result = None
        self.last_answer = None
        self.last_route = None
        self._register_default_agents(
            model=model,
            planner_cls=planner_cls,
            critic_cls=critic_cls,
            research_pipeline_cls=research_pipeline_cls,
            knowledge_store=knowledge_store,
        )


    def _system_prompt(self, tool_manager_obj):
        try:
            from prompts import create_system_prompt

            return create_system_prompt(tool_manager_obj)
        except Exception:
            return ""


    def _register_default_agents(self, *, model: str, planner_cls, critic_cls, research_pipeline_cls, knowledge_store):
        self.factory.create(
            PlannerAgent,
            model=model,
            planner_cls=planner_cls,
            router=self.router,
        )
        self.factory.create(
            MemoryAgent,
            memory=self.memory,
            extractor_cls=type(self.extractor),
            validator_cls=type(self.validator),
            summarizer_cls=type(self.summarizer),
            normalizer_cls=type(self.normalizer),
        )
        self.factory.create(
            ResearchAgent,
            model=model,
            memory=self.memory,
            research_pipeline_cls=research_pipeline_cls,
        )
        self.factory.create(
            KnowledgeAgent,
            knowledge_store=knowledge_store,
        )
        self.factory.create(
            CodingAgent,
            model=model,
        )
        self.factory.create(
            CriticAgent,
            model=model,
            critic_cls=critic_cls,
        )
        self.factory.create(
            VisionAgent,
        )
        self.factory.create(
            TaskAgent,
        )


    def _available_tools(self):
        try:
            return [tool.name for tool in self.tool_manager.list_tools()]
        except Exception:
            return []


    def _memory_context(self, user_input: str):
        try:
            return self.memory.get_semantic_context(user_input)
        except Exception:
            return ""


    def _route(self, user_input: str, plan=None):
        decision = self.router.route(user_input, context_bus=self.context_bus, plan=plan)
        self.context_bus.set("route_decision", asdict(decision))
        self.context_bus.publish("route", asdict(decision), source="orchestrator")
        return decision


    def _execute_agent(self, agent_name: str, task: Any | None = None, **kwargs):
        return self.manager.execute(agent_name, self.context_bus, task=task, **kwargs)


    def _execute_parallel_group(self, agent_names: list[str], task: Any | None = None, timeout: float | None = None, **kwargs):
        outcomes = []
        if not agent_names:
            return outcomes
        with ThreadPoolExecutor(max_workers=len(agent_names)) as executor:
            futures = {
                executor.submit(self._execute_agent, name, task, **kwargs): name
                for name in agent_names
                if name in self.registry
            }
            try:
                for future in futures:
                    name = futures[future]
                    try:
                        outcomes.append(future.result(timeout=timeout))
                    except FuturesTimeoutError:
                        outcomes.append(AgentOutcome(agent_name=name, status="timeout", output=None, errors=["Timeout"]))
                    except Exception as exc:
                        outcomes.append(AgentOutcome(agent_name=name, status="error", output=None, errors=[str(exc)]))
            finally:
                pass
        return outcomes


    def think(self, user_input: str, *, stream: bool = True):
        self.context_bus.reset()
        self.context_bus.set("user_input", user_input)
        self.conversation.add_user(user_input)

        memory_context = self._memory_context(user_input)
        self.context_bus.set_memory_context({"query": user_input, "relevant": memory_context})
        self.conversation.add_system(memory_context)

        plan_outcome = self._execute_agent(
            "planner_agent",
            task=user_input,
            memory_context=memory_context,
            tool_descriptions=self.tool_manager.get_descriptions(),
            available_tools=self._available_tools(),
        )
        plan = plan_outcome.output
        self.last_plan = plan
        structured_plan = self.context_bus.get("plan")
        self.context_bus.set("plan_object", plan)
        if structured_plan is not None:
            self.context_bus.set("structured_plan", structured_plan)

        route_decision = self._route(user_input, plan=structured_plan or plan)
        self.last_route = route_decision
        selected_agents = [name for name in route_decision.agents if name != "planner_agent"]
        if "critic_agent" in selected_agents:
            selected_agents = [name for name in selected_agents if name != "critic_agent"] + ["critic_agent"]

        side_outcomes = []
        parallel_groups = [group for group in route_decision.parallel_groups if group]
        executed = set()
        parallel_timeout = float(self.context_bus.get("parallel_timeout", 30.0) or 30.0)
        for group in parallel_groups:
            group_agents = [name for name in group if name in selected_agents and name not in executed and name != "critic_agent"]
            if not group_agents:
                continue
            side_outcomes.extend(
                self._execute_parallel_group(
                    group_agents,
                    task=user_input,
                    timeout=parallel_timeout,
                    memory_context=memory_context,
                    available_tools=self._available_tools(),
                )
            )
            executed.update(group_agents)
        for agent_name in selected_agents:
            if agent_name in executed or agent_name == "critic_agent":
                continue
            outcome = self._execute_agent(
                agent_name,
                task=user_input,
                memory_context=memory_context,
                available_tools=self._available_tools(),
            )
            side_outcomes.append(outcome)
            executed.add(agent_name)

        combined_context = self.context_bus.compose_context()
        execution = self.execution_loop.run(
            user_input=user_input,
            memory_context=combined_context or memory_context,
            plan=plan,
        )
        final_answer = execution.get("answer", "")
        self.last_execution = execution
        self.last_answer = final_answer
        step_results = execution.get("step_results", [])
        self.last_research_result = self._extract_research_result(step_results)
        reflection = execution.get("reflection")
        self.last_reflection = reflection

        if "critic_agent" in route_decision.agents:
            critic_outcome = self._execute_agent(
                "critic_agent",
                task={"final_answer": final_answer, "goal": user_input},
                user_input=user_input,
                memory_context=combined_context or memory_context,
                plan=plan,
                step_results=step_results,
                final_answer=final_answer,
            )
            if critic_outcome.status == "ok" and critic_outcome.output is not None:
                self.context_bus.set("critique", critic_outcome.output)
                self.last_reflection = critic_outcome.output

        self.context_bus.set("final_answer", final_answer)
        self.context_bus.set("step_results", step_results)
        self.context_bus.set("execution", execution)
        self.context_bus.set("reflection", self.last_reflection)
        self.context_bus.add_agent_report("execution_engine", execution)
        self.context_bus.publish("final_answer", final_answer, source="orchestrator")

        self.conversation.add_assistant(final_answer)
        return OrchestrationResult(
            task=user_input,
            plan=plan,
            outcomes=[plan_outcome, *side_outcomes],
            final_response=final_answer,
            status="ok" if execution else "error",
            context=self.context_bus.snapshot(),
        )


    def _extract_research_result(self, step_results):
        for item in step_results:
            if item.get("action") in {"research", "research_pipeline"}:
                result = item.get("result")
                if isinstance(result, dict):
                    return result
        research = self.context_bus.get("research")
        if isinstance(research, dict):
            return research
        return None


    def snapshot(self):
        return {
            "plan": self.last_plan,
            "execution": self.last_execution,
            "reflection": self.last_reflection,
            "research_result": self.last_research_result,
            "answer": self.last_answer,
            "route": self.last_route,
            "context": self.context_bus.snapshot(),
        }
