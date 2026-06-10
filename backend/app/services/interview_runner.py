"""
Backend-agnostic interview runner (Phase 6 of the Zep -> Postgres migration).

The interview flow does not depend on Zep at all — it only needs an
LLMClient, the OASIS simulation runner, and the agent profile files
under uploads/simulations/<sim_id>/. We extract the legacy logic out of
ZepToolsService into a pure module so PostgresToolsService can call it
without instantiating a Zep client.

ZepToolsService.interview_agents is left untouched to avoid touching the
legacy path; once both backends are in production for a few weeks,
ZepToolsService.interview_agents can be slimmed down to call this module
too. Tracked as a follow-up cleanup, not in the scope of this PR.
"""

from __future__ import annotations

import csv
import json
import os
import re
import traceback
from typing import Any, Dict, List, Optional

from ..utils.llm_client import LLMClient
from ..utils.locale import get_locale, t
from ..utils.logger import get_logger
from .graph_domain import AgentInterview, InterviewResult


logger = get_logger("mirofish.interview_runner")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_interview_agents(
    llm: LLMClient,
    simulation_id: str,
    interview_requirement: str,
    simulation_requirement: str = "",
    max_agents: int = 5,
    custom_questions: Optional[List[str]] = None,
) -> InterviewResult:
    """Run the OASIS interview flow against a live simulation.

    Mirrors ZepToolsService.interview_agents step-for-step so the Report
    Agent prompt and downstream summarisation get byte-identical results
    on either backend.
    """
    # Local import: simulation_runner pulls in heavy modules (camel-oasis)
    # that we want to avoid loading on every backend boot.
    from .simulation_runner import SimulationRunner

    logger.info(t("console.interviewAgentsStart", requirement=interview_requirement[:50]))

    result = InterviewResult(
        interview_topic=interview_requirement,
        interview_questions=custom_questions or [],
    )

    # Step 1: load profiles persisted by the simulation prepare phase.
    profiles = _load_agent_profiles(simulation_id)
    if not profiles:
        logger.warning(t("console.profilesNotFound", simId=simulation_id))
        result.summary = "No agent profiles available for interview"
        return result

    result.total_agents = len(profiles)
    logger.info(t("console.loadedProfiles", count=len(profiles)))

    # Step 2: LLM picks which agents to interview.
    selected_agents, selected_indices, selection_reasoning = _select_agents_for_interview(
        llm,
        profiles=profiles,
        interview_requirement=interview_requirement,
        simulation_requirement=simulation_requirement,
        max_agents=max_agents,
    )
    result.selected_agents = selected_agents
    result.selection_reasoning = selection_reasoning
    logger.info(
        t(
            "console.selectedAgentsForInterview",
            count=len(selected_agents),
            indices=selected_indices,
        )
    )

    # Step 3: generate interview questions if not provided.
    if not result.interview_questions:
        result.interview_questions = _generate_interview_questions(
            llm,
            interview_requirement=interview_requirement,
            simulation_requirement=simulation_requirement,
            selected_agents=selected_agents,
        )
        logger.info(
            t(
                "console.generatedInterviewQuestions",
                count=len(result.interview_questions),
            )
        )

    combined_prompt = "\n".join(
        [f"{i+1}. {q}" for i, q in enumerate(result.interview_questions)]
    )

    INTERVIEW_PROMPT_PREFIX = (
        "You are being interviewed. Use your persona, all your past memory "
        "and prior actions, and answer the following questions in plain text.\n"
        "Rules:\n"
        "1. Answer in natural language, do not invoke any tool.\n"
        "2. Do not return JSON or tool-call format.\n"
        "3. Do not use Markdown headings (#, ##, ###).\n"
        "4. Number your answers as 'Question X:' (X is the question number).\n"
        "5. Separate answers with a blank line.\n"
        "6. Each answer must be at least 2-3 sentences.\n\n"
    )
    optimized_prompt = f"{INTERVIEW_PROMPT_PREFIX}{combined_prompt}"

    # Step 4: invoke the real OASIS interview API for the selected agents.
    try:
        interviews_request = []
        for agent_idx in selected_indices:
            interviews_request.append(
                {
                    "agent_id": agent_idx,
                    "prompt": optimized_prompt,
                }
            )

        logger.info(
            t("console.callingBatchInterviewApi", count=len(interviews_request))
        )

        api_result = SimulationRunner.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=interviews_request,
            platform=None,
            timeout=180.0,
        )

        logger.info(
            t(
                "console.interviewApiReturned",
                count=api_result.get("interviews_count", 0),
                success=api_result.get("success"),
            )
        )

        if not api_result.get("success", False):
            error_msg = api_result.get("error", "unknown error")
            logger.warning(t("console.interviewApiReturnedFailure", error=error_msg))
            result.summary = (
                f"Interview API call failed: {error_msg}. "
                "Check that the OASIS simulation environment is running."
            )
            return result

        # Step 5: parse results into AgentInterview objects.
        api_data = api_result.get("result", {})
        results_dict = (
            api_data.get("results", {}) if isinstance(api_data, dict) else {}
        )

        for i, agent_idx in enumerate(selected_indices):
            agent = selected_agents[i]
            agent_name = agent.get(
                "realname", agent.get("username", f"Agent_{agent_idx}")
            )
            agent_role = agent.get("profession", "unknown")
            agent_bio = agent.get("bio", "")

            twitter_result = results_dict.get(f"twitter_{agent_idx}", {})
            reddit_result = results_dict.get(f"reddit_{agent_idx}", {})

            twitter_response = _clean_tool_call_response(
                twitter_result.get("response", "")
            )
            reddit_response = _clean_tool_call_response(
                reddit_result.get("response", "")
            )

            twitter_text = twitter_response or "(no response on this platform)"
            reddit_text = reddit_response or "(no response on this platform)"
            response_text = (
                f"[Twitter response]\n{twitter_text}\n\n"
                f"[Reddit response]\n{reddit_text}"
            )

            combined_responses = f"{twitter_response} {reddit_response}"
            clean_text = re.sub(r"#{1,6}\s+", "", combined_responses)
            clean_text = re.sub(r"\{[^}]*tool_name[^}]*\}", "", clean_text)
            clean_text = re.sub(r"[*_`|>~\-]{2,}", "", clean_text)
            clean_text = re.sub(r"(Question|Pregunta)\s*\d+[:：]\s*", "", clean_text)
            clean_text = re.sub(r"【[^】]+】", "", clean_text)
            clean_text = re.sub(r"\[[^\]]+\]", "", clean_text)

            sentences = re.split(r"[.!?。！？]", clean_text)
            meaningful = [
                s.strip()
                for s in sentences
                if 20 <= len(s.strip()) <= 200
                and not re.match(r"^[\s\W,;:、]+", s.strip())
                and not s.strip().startswith(("{", "Question", "Pregunta"))
            ]
            meaningful.sort(key=len, reverse=True)
            key_quotes = [s + "." for s in meaningful[:3]]

            if not key_quotes:
                paired = re.findall(r'"([^"]{15,150})"', clean_text)
                paired += re.findall(
                    r"“([^“”]{15,150})”", clean_text
                )
                paired += re.findall(
                    r"「([^「」]{15,150})」", clean_text
                )
                key_quotes = [q for q in paired if not re.match(r"^[,;:]", q)][:3]

            interview = AgentInterview(
                agent_name=agent_name,
                agent_role=agent_role,
                agent_bio=agent_bio[:1000],
                question=combined_prompt,
                response=response_text,
                key_quotes=key_quotes[:5],
            )
            result.interviews.append(interview)

        result.interviewed_count = len(result.interviews)

    except ValueError as e:
        logger.warning(t("console.interviewApiCallFailed", error=e))
        result.summary = (
            f"Interview failed: {str(e)}. "
            "The OASIS simulation environment is not reachable."
        )
        return result
    except Exception as e:
        logger.error(t("console.interviewApiCallException", error=e))
        logger.error(traceback.format_exc())
        result.summary = f"Interview pipeline raised an error: {str(e)}"
        return result

    # Step 6: summarise.
    if result.interviews:
        result.summary = _generate_interview_summary(
            llm,
            interviews=result.interviews,
            interview_requirement=interview_requirement,
        )

    logger.info(t("console.interviewAgentsComplete", count=result.interviewed_count))
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_agent_profiles(simulation_id: str) -> List[Dict[str, Any]]:
    sim_dir = os.path.join(
        os.path.dirname(__file__),
        f"../../uploads/simulations/{simulation_id}",
    )

    profiles: List[Dict[str, Any]] = []

    reddit_profile_path = os.path.join(sim_dir, "reddit_profiles.json")
    if os.path.exists(reddit_profile_path):
        try:
            with open(reddit_profile_path, "r", encoding="utf-8") as f:
                profiles = json.load(f)
            logger.info(t("console.loadedRedditProfiles", count=len(profiles)))
            return profiles
        except Exception as e:
            logger.warning(t("console.readRedditProfilesFailed", error=e))

    twitter_profile_path = os.path.join(sim_dir, "twitter_profiles.csv")
    if os.path.exists(twitter_profile_path):
        try:
            with open(twitter_profile_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    profiles.append(
                        {
                            "realname": row.get("name", ""),
                            "username": row.get("username", ""),
                            "bio": row.get("description", ""),
                            "persona": row.get("user_char", ""),
                            "profession": "unknown",
                        }
                    )
            logger.info(t("console.loadedTwitterProfiles", count=len(profiles)))
            return profiles
        except Exception as e:
            logger.warning(t("console.readTwitterProfilesFailed", error=e))

    return profiles


def _select_agents_for_interview(
    llm: LLMClient,
    profiles: List[Dict[str, Any]],
    interview_requirement: str,
    simulation_requirement: str,
    max_agents: int,
):
    agent_summaries: List[Dict[str, Any]] = []
    for i, profile in enumerate(profiles):
        agent_summaries.append(
            {
                "index": i,
                "name": profile.get("realname", profile.get("username", f"Agent_{i}")),
                "profession": profile.get("profession", "unknown"),
                "bio": (profile.get("bio") or "")[:200],
                "interested_topics": profile.get("interested_topics", []),
            }
        )

    system_prompt = (
        "You are a senior interview planner. Pick the agents from the simulation "
        "list that best match the interview goal.\n\n"
        "Selection criteria:\n"
        "1. Identity / role aligned with the interview topic.\n"
        "2. Likely to hold a unique or valuable viewpoint.\n"
        "3. Diverse perspectives (supporters, opposers, neutral, experts).\n"
        "4. Prefer roles directly involved in the scenario.\n\n"
        'Return JSON: {"selected_indices": [...], "reasoning": "..."}.'
    )
    user_prompt = (
        f"Interview requirement:\n{interview_requirement}\n\n"
        f"Simulation context:\n{simulation_requirement or 'not provided'}\n\n"
        f"Candidate agents ({len(agent_summaries)}):\n"
        f"{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}\n\n"
        f"Select up to {max_agents} agents and explain why."
    )

    try:
        response = llm.chat_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        selected_indices = response.get("selected_indices", [])[:max_agents]
        reasoning = response.get("reasoning", "default selection by relevance")

        selected_agents = []
        valid_indices = []
        for idx in selected_indices:
            if 0 <= idx < len(profiles):
                selected_agents.append(profiles[idx])
                valid_indices.append(idx)
        return selected_agents, valid_indices, reasoning

    except Exception as e:
        logger.warning(t("console.llmSelectAgentFailed", error=e))
        selected = profiles[:max_agents]
        indices = list(range(min(max_agents, len(profiles))))
        return selected, indices, "default selection (LLM picker failed)"


def _generate_interview_questions(
    llm: LLMClient,
    interview_requirement: str,
    simulation_requirement: str,
    selected_agents: List[Dict[str, Any]],
) -> List[str]:
    agent_roles = [a.get("profession", "unknown") for a in selected_agents]

    system_prompt = (
        "You are a professional reporter. Produce 3-5 deep interview questions.\n\n"
        "Rules:\n"
        "1. Open-ended, encouraging detailed answers.\n"
        "2. Different roles should plausibly answer differently.\n"
        "3. Cover facts, opinions and feelings.\n"
        "4. Natural tone, like a real interview.\n"
        "5. Each question under ~25 words.\n"
        "6. Direct questions only — no preamble.\n\n"
        'Return JSON: {"questions": ["q1", "q2", ...]}.'
    )
    user_prompt = (
        f"Interview requirement: {interview_requirement}\n\n"
        f"Simulation context: {simulation_requirement or 'not provided'}\n\n"
        f"Interviewee roles: {', '.join(agent_roles)}\n\n"
        "Generate 3-5 questions."
    )

    try:
        response = llm.chat_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
        )
        return response.get(
            "questions",
            [f"What is your view on '{interview_requirement}'?"],
        )
    except Exception as e:
        logger.warning(t("console.generateInterviewQuestionsFailed", error=e))
        return [
            f"What is your view on '{interview_requirement}'?",
            "How does this affect you or the group you represent?",
            "What do you think should be done to address it?",
        ]


def _generate_interview_summary(
    llm: LLMClient,
    interviews: List[AgentInterview],
    interview_requirement: str,
) -> str:
    if not interviews:
        return "No interviews completed"

    interview_texts: List[str] = []
    for interview in interviews:
        interview_texts.append(
            f"[{interview.agent_name} ({interview.agent_role})]\n"
            f"{interview.response[:500]}"
        )

    quote_instruction = (
        "Use \" \" when quoting interviewees."
        if get_locale() != "zh"
        else "引用受访者原话时使用中文引号「」"
    )

    system_prompt = (
        "You are a professional editor. Produce a single interview summary "
        "based on multiple interviewees' answers.\n\n"
        "Requirements:\n"
        "1. Distil each side's main points.\n"
        "2. Note shared views and disagreements.\n"
        "3. Highlight valuable quotes.\n"
        "4. Stay objective and neutral.\n"
        "5. Keep it under ~1000 words.\n\n"
        "Format constraints (mandatory):\n"
        "- Plain-text paragraphs separated by blank lines.\n"
        "- No Markdown headings (#, ##, ###).\n"
        "- No horizontal rules (--- or ***).\n"
        f"- {quote_instruction}\n"
        "- You may bold key terms with **bold**, but no other Markdown."
    )
    user_prompt = (
        f"Interview topic: {interview_requirement}\n\n"
        "Interview transcripts:\n"
        f"{''.join(interview_texts)}\n\n"
        "Produce the summary."
    )

    try:
        return llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=800,
        )
    except Exception as e:
        logger.warning(t("console.generateInterviewSummaryFailed", error=e))
        return (
            f"Interviewed {len(interviews)} subjects: "
            + ", ".join([i.agent_name for i in interviews])
        )


def _clean_tool_call_response(response: str) -> str:
    """Strip JSON tool-call wrappers that the model sometimes returns."""
    if not response or not response.strip().startswith("{"):
        return response
    text = response.strip()
    if "tool_name" not in text[:80]:
        return response
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "arguments" in data:
            for key in ("content", "text", "body", "message", "reply"):
                if key in data["arguments"]:
                    return str(data["arguments"][key])
    except (json.JSONDecodeError, KeyError, TypeError):
        match = re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if match:
            return match.group(1).replace("\\n", "\n").replace('\\"', '"')
    return response
