from __future__ import annotations
"""
CyberDrishti × ArmorIQ — Fully Autonomous ReAct Investigation Agent

Architecture:
  Security Incident / Case
        ↓
  [Plan Declaration] — capture_plan() declares the agent's authorized scope
        ↓
  [Cryptographic Token] — get_intent_token() issues Ed25519-signed Merkle token
        ↓
  ┌────────────────── Autonomous ReAct Loop (Multi-Turn) ──────────────────┐
  │                                                                         │
  │  1. LLM Reasoning (Thought): Evaluates evidence and past observations   │
  │  2. Action Selection: Dynamically chooses next tool & parameters        │
  │  3. ArmorIQ Live Gate: client.invoke(mcp, action, intent_token)        │
  │     ├── [Authorized] → Tool executes → returns Observation → Loop      │
  │     └── [Out-of-Scope] → IntentMismatchException                        │
  │                                 ↓                                       │
  │                     [HOLD STATE / Interception]                         │
  │                     Agent pauses in awaiting_approval                   │
  │                     Human reviews AI reasoning & risk in UI             │
  │                                 ↓                                       │
  │                     [Human Action: Approve / Reject]                    │
  │                     Observation injected → Loop RESUMES                 │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘
        ↓
  [Dual Audit Trail] — Recorded in ArmorIQ log + CyberDrishti SHA-256 chain
"""
import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from armoriq.client import armoriq, get_intent_mismatch_exception
from armoriq.tools import (
    tool_collect_security_logs,
    tool_analyze_suspicious_entities,
    tool_correlate_events,
    tool_quarantine_account,
    tool_generate_incident_assessment,
    tool_modify_network_control_config,
)

logger = logging.getLogger(__name__)

# ── MCP identifier registered in ArmorIQ platform ───────────────────────────

CYBERDRISHTI_MCP = "cyberdrishti-investigation-mcp"

# ── Authorization Scope Declaration (CSRG-IAP Plan) ─────────────────────────

AUTHORIZED_PLAN = {
    "goal": (
        "Autonomously investigate a cybersecurity incident: collect evidence logs, "
        "analyze suspicious entities, correlate events via hidden-link engine, "
        "quarantine confirmed threat actors, and generate an incident assessment report."
    ),
    "steps": [
        {
            "action": "collect_security_logs",
            "mcp": CYBERDRISHTI_MCP,
            "description": "Retrieve all evidence events and security logs for the case",
        },
        {
            "action": "analyze_suspicious_entities",
            "mcp": CYBERDRISHTI_MCP,
            "description": "Run NER extraction and entity graph centrality analysis",
        },
        {
            "action": "correlate_events",
            "mcp": CYBERDRISHTI_MCP,
            "description": "Run hidden-link engine to find covert relationships",
        },
        {
            "action": "quarantine_account",
            "mcp": CYBERDRISHTI_MCP,
            "description": "Mark confirmed threat actor entities as quarantined",
        },
        {
            "action": "generate_incident_assessment",
            "mcp": CYBERDRISHTI_MCP,
            "description": "Generate structured incident assessment using RAG copilot",
        },
        # NOTE: "modify_network_control_config" is intentionally NOT in this plan.
        # The agent's AI reasoning will conclude that perimeter blocking is needed,
        # but ArmorIQ's Live Intent Assurance will intercept it cryptographically.
    ],
    "metadata": {
        "agent": "CyberDrishti Autonomous ReAct Agent",
        "version": "3.0.0",
        "scope": "incident_investigation",
        "authorized_remediation": "account_quarantine_only",
        "out_of_scope": "network_control_modification",
    },
}

# ── Tool Definitions for Agentic Dispatch ────────────────────────────────────

TOOL_DESCRIPTIONS = {
    "collect_security_logs": {
        "name": "collect_security_logs",
        "description": "Retrieve evidence events, call records, and security logs for the case.",
        "params": {},
        "fn": tool_collect_security_logs,
    },
    "analyze_suspicious_entities": {
        "name": "analyze_suspicious_entities",
        "description": "Run NER extraction and graph centrality analysis to identify suspect entities and primary threat actors.",
        "params": {},
        "fn": tool_analyze_suspicious_entities,
    },
    "correlate_events": {
        "name": "correlate_events",
        "description": "Run the hidden-link engine to discover covert relationships and high-risk clusters.",
        "params": {},
        "fn": tool_correlate_events,
    },
    "quarantine_account": {
        "name": "quarantine_account",
        "description": "Quarantine a confirmed threat actor entity in the investigation database.",
        "params": {"entity_id": "ID of the suspect entity to quarantine"},
        "fn": tool_quarantine_account,
    },
    "modify_network_control_config": {
        "name": "modify_network_control_config",
        "description": "Apply a network-level perimeter block rule for a persistent attacker IP.",
        "params": {
            "rule_id": "Target firewall rule ID (e.g. 'fwr-002')",
            "suspect_ip": "Attacker IP address to block",
            "modification_type": "Modification type (e.g. 'add_block')",
        },
        "fn": tool_modify_network_control_config,
    },
    "generate_incident_assessment": {
        "name": "generate_incident_assessment",
        "description": "Generate the final incident assessment report and conclude investigation.",
        "params": {},
        "fn": tool_generate_incident_assessment,
    },
}


class AutonomousInvestigationAgent:
    """
    CyberDrishti's Fully Autonomous ReAct Investigation Agent.

    Features:
      - Dynamic ReAct Loop: Reason -> Act -> ArmorIQ Gate -> Observe -> Repeat
      - ArmorIQ Live Intent Assurance: Cryptographic Merkle-tree validation per turn
      - Stateful Hold Interception: Out-of-scope actions pause into reviewable HOLDs
      - Seamless Resume: Resumes autonomous loop upon human approval or rejection
      - Dual Audit Trail: Synchronized with SHA-256 blockchain-style hash chain
    """

    def __init__(self, case_id: str, triggered_by: str, db):
        self.case_id = case_id
        self.triggered_by = triggered_by
        self.db = db
        self.session_id = str(uuid.uuid4())
        self.status = "idle"
        self.actions: list[dict] = []
        self.history: list[dict] = []  # ReAct memory: list of turn dicts
        self.pending_hold: dict | None = None
        self.intent_token = None
        self.plan_capture = None
        self._client = armoriq()
        self._IntentMismatch = get_intent_mismatch_exception()
        self._discovered_entities: dict = {}
        self._discovered_correlations: dict = {}

    # ── Public Lifecycle Methods ─────────────────────────────────────────────

    async def run(self) -> dict:
        """
        Start the autonomous ReAct investigation from scratch.
        """
        await self._set_status("investigating")
        await self._persist_session()

        try:
            # 1. Declare Authorization Plan to ArmorIQ
            await self._declare_intent_plan()

            # 2. Launch Autonomous ReAct Loop
            await self._run_react_loop(max_turns=8)

        except Exception as exc:
            logger.error(f"[Agent] Error in agent lifecycle: {exc}", exc_info=True)
            await self._log_action(
                "AGENT_ERROR",
                f"Agent execution encountered an error: {exc}",
                {"error": str(exc)},
                status="failed",
            )
            await self._set_status("failed")

        return self._build_summary()

    async def approve_hold(self, approved_by: str) -> dict:
        """
        Human supervisor approves the blocked action.
        The action is executed, the result is added to the agent's memory as an observation,
        and the ReAct loop resumes autonomously to finalize the investigation.
        """
        if not self.pending_hold:
            return {"error": "No pending hold to approve"}

        hold = self.pending_hold
        hold["approved_by"] = approved_by
        hold["approved_at"] = datetime.now(timezone.utc).isoformat()
        hold["status"] = "approved"

        await self._log_action(
            "HOLD_APPROVED",
            f"Human supervisor authorized blocked action: {hold['action']}",
            {
                "hold_id": hold["hold_id"],
                "approved_by": approved_by,
                "action": hold["action"],
                "authorization": "human_in_the_loop_elevation",
            },
            status="approved",
        )

        # Execute the authorized tool
        execution_result = {}
        try:
            tool_fn = TOOL_DESCRIPTIONS[hold["action"]]["fn"]
            execution_result = await tool_fn(**hold["tool_params"])

            await self._log_action(
                "HOLD_EXECUTED",
                f"Action executed following human approval: {hold['action']}",
                {
                    "hold_id": hold["hold_id"],
                    "action": hold["action"],
                    "result": execution_result,
                    "executed_by": f"agent (supervised by {approved_by})",
                },
                status="executed",
            )
        except Exception as exc:
            logger.error(f"[Agent] Execution of approved hold failed: {exc}")
            await self._log_action(
                "HOLD_EXECUTION_FAILED",
                f"Execution failed: {exc}",
                {"error": str(exc)},
                status="failed",
            )

        # Record observation in ReAct memory
        self.history.append({
            "turn": len(self.history) + 1,
            "thought": "Supervisor reviewed my request and APPROVED perimeter network defense. Proceeding to finalize report.",
            "action": hold["action"],
            "params": {k: v for k, v in hold["tool_params"].items() if k != "db"},
            "observation": {
                "status": "approved_and_executed",
                "supervisor": approved_by,
                "result": execution_result,
            },
        })

        self.pending_hold = None

        # Resume the autonomous loop to complete the investigation
        await self._set_status("executing")
        await self._run_react_loop(max_turns=4)

        return self._build_summary()

    async def reject_hold(self, rejected_by: str, reason: str) -> dict:
        """
        Human supervisor rejects the blocked action.
        The rejection is provided to the agent as an observation so it can adapt
        and autonomously conclude the investigation without the blocked action.
        """
        if not self.pending_hold:
            return {"error": "No pending hold to reject"}

        hold = self.pending_hold
        hold["rejected_by"] = rejected_by
        hold["rejected_at"] = datetime.now(timezone.utc).isoformat()
        hold["rejection_reason"] = reason
        hold["status"] = "rejected"

        await self._log_action(
            "HOLD_REJECTED",
            f"Human supervisor REJECTED action: {hold['action']}",
            {
                "hold_id": hold["hold_id"],
                "rejected_by": rejected_by,
                "reason": reason,
                "action": hold["action"],
            },
            status="rejected",
        )

        # Record rejection observation in ReAct memory
        self.history.append({
            "turn": len(self.history) + 1,
            "thought": f"Supervisor rejected {hold['action']} (Reason: {reason}). Adapting investigation plan to conclude without perimeter modification.",
            "action": hold["action"],
            "params": {k: v for k, v in hold["tool_params"].items() if k != "db"},
            "observation": {
                "status": "rejected_by_supervisor",
                "supervisor": rejected_by,
                "reason": reason,
            },
        })

        self.pending_hold = None

        # Resume autonomous loop so the agent adapts and generates the final assessment
        await self._set_status("executing")
        await self._run_react_loop(max_turns=4)

        return self._build_summary()

    # ── Core Autonomous ReAct Engine ─────────────────────────────────────────

    async def _declare_intent_plan(self):
        """Register the agent's intent plan and mint an ArmorIQ token."""
        await self._log_action(
            "PLAN_DECLARED",
            "Authorization scope declared to ArmorIQ Live Intent Assurance",
            {
                "goal": AUTHORIZED_PLAN["goal"],
                "authorized_actions": [s["action"] for s in AUTHORIZED_PLAN["steps"]],
                "out_of_scope": ["modify_network_control_config"],
                "governance": "CSRG-IAP Merkle Intent Verification",
            },
            status="authorized",
        )

        self.plan_capture = self._client.capture_plan(
            llm="ollama/llama3.2:1b",
            prompt=(
                f"Autonomously investigate security incident for case {self.case_id}. "
                "Collect evidence, analyze threat entities, correlate links, and mitigate."
            ),
            plan=AUTHORIZED_PLAN,
            metadata={"case_id": self.case_id, "session_id": self.session_id},
        )

        token_response = self._client.get_intent_token(
            self.plan_capture,
            validity_seconds=3600,
        )
        self.intent_token = token_response

        await self._log_action(
            "INTENT_TOKEN_ISSUED",
            "Cryptographic Intent Token issued by ArmorIQ Proxy",
            {
                "plan_hash": token_response.get("plan_hash", "stub_hash"),
                "merkle_root": token_response.get("merkle_root", "stub_root"),
                "expires_at": token_response.get("expires_at"),
                "signature_type": "Ed25519",
            },
            status="authorized",
        )

    async def _run_react_loop(self, max_turns: int = 8):
        """
        Dynamic ReAct loop:
          Turn 1..N:
            - Decide next Thought + Action
            - Submit to ArmorIQ Intent Check
            - Execute or Intercept
        """
        for turn_idx in range(max_turns):
            # 1. AI Decision Step (Reasoning + Next Action)
            decision = await self._decide_next_action()
            action_name = decision.get("action")
            thought = decision.get("thought", "Analyzing incident data...")
            tool_args = decision.get("params", {})

            # Log the agent's dynamic reasoning
            await self._log_action(
                "AGENT_REASONING",
                f"Thought: {thought}",
                {
                    "turn": len(self.history) + 1,
                    "thought": thought,
                    "proposed_action": action_name,
                    "parameters": tool_args,
                },
                status="requested",
            )

            # If agent decides it has completed everything
            if action_name == "complete" or not action_name:
                await self._set_status("completed")
                await self._update_session_completed()
                break

            # 2. Check if tool exists
            tool_info = TOOL_DESCRIPTIONS.get(action_name)
            if not tool_info:
                logger.warning(f"[Agent] Unknown tool: {action_name}")
                break

            # 3. Gated Execution through ArmorIQ
            tool_params = {**tool_args, "case_id": self.case_id, "db": self.db}

            # If this is assessment, pass discovered context
            if action_name == "generate_incident_assessment":
                tool_params["entities"] = self._discovered_entities
                tool_params["correlations"] = self._discovered_correlations
                tool_params["actions_taken"] = self.actions

            intercepted = await self._dispatch_with_armoriq(
                action=action_name,
                description=f"Action: {action_name} — {tool_info['description']}",
                tool_fn=tool_info["fn"],
                tool_params=tool_params,
                ai_thought=thought,
            )

            if intercepted:
                # Execution paused in HOLD state awaiting human supervisor
                return

            # Check if this completed the investigation
            if action_name == "generate_incident_assessment":
                await self._set_status("completed")
                await self._update_session_completed()
                break

            # Short async pause to allow UI real-time streaming
            await asyncio.sleep(0.8)

    async def _dispatch_with_armoriq(
        self,
        action: str,
        description: str,
        tool_fn,
        tool_params: dict,
        ai_thought: str,
    ) -> bool:
        """
        Executes an action gated by ArmorIQ Live Intent Assurance.
        Returns True if action was intercepted into HOLD, False if completed.
        """
        clean_params = {k: v for k, v in tool_params.items() if k not in ("db", "actions_taken")}

        await self._log_action(
            "ACTION_REQUESTED",
            description,
            {"action": action, "ai_thought": ai_thought, "params": clean_params},
            status="requested",
        )

        try:
            # ── ArmorIQ Cryptographic Verification ───────────────────────────
            # Checks Merkle proof of the action against the signed Intent Token
            invoke_res = self._client.invoke(
                mcp=CYBERDRISHTI_MCP,
                action=action,
                intent_token=self.intent_token,
                params={k: str(v) for k, v in clean_params.items()},
            )

            # ── Authorized Execution ─────────────────────────────────────────
            obs = await tool_fn(**tool_params)

            # Cache entity/correlation findings for downstream turns
            if action == "analyze_suspicious_entities" and isinstance(obs, dict):
                self._discovered_entities = obs
            elif action == "correlate_events" and isinstance(obs, dict):
                self._discovered_correlations = obs

            await self._log_action(
                "ACTION_EXECUTED",
                f"Action executed (ArmorIQ Authorized ✓): {action}",
                {
                    "action": action,
                    "armoriq_verified": invoke_res.get("success", True),
                    "observation_summary": _summarize(obs),
                },
                status="executed",
            )

            # Append to ReAct turn history
            self.history.append({
                "turn": len(self.history) + 1,
                "thought": ai_thought,
                "action": action,
                "params": clean_params,
                "observation": obs,
            })
            return False

        except self._IntentMismatch as exc:
            # ── ArmorIQ Cryptographic Interception ───────────────────────────
            # The action was NOT declared in the signed authorization plan.
            hold_id = f"hold-{self.session_id[:8]}-{action[:12]}"

            self.pending_hold = {
                "hold_id": hold_id,
                "action": action,
                "mcp": CYBERDRISHTI_MCP,
                "description": description,
                "ai_reasoning": ai_thought,
                "armoriq_reason": str(exc),
                "authorization_boundary": (
                    f"Action '{action}' is outside the agent's cryptographically signed authorization plan. "
                    "Perimeter network control modifications require human supervisor sign-off."
                ),
                "risk_level": "HIGH",
                "affected_resource": {
                    "type": "sandbox_firewall_rule",
                    "id": clean_params.get("rule_id", "fwr-002"),
                    "name": "THREAT_IP_BLOCKLIST",
                    "description": "Perimeter block policy managed by NOC/SOC team",
                },
                "tool_params": tool_params,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "status": "awaiting_approval",
            }

            await self._log_action(
                "ARMORIQ_BLOCK",
                f"ArmorIQ intercepted action outside authorization plan: {action}",
                {
                    "hold_id": hold_id,
                    "action": action,
                    "armoriq_enforcement": "IntentMismatchException",
                    "enforcement_reason": str(exc),
                    "ai_reasoning": ai_thought,
                    "authorization_boundary": self.pending_hold["authorization_boundary"],
                    "risk_level": "HIGH",
                },
                status="blocked",
            )

            await self._set_status("awaiting_approval")
            await self._persist_hold()
            return True

    # ── Dynamic ReAct Planner (AI Decision Engine) ───────────────────────────

    async def _decide_next_action(self) -> dict:
        """
        Dynamically analyzes current observation history to decide the next step.
        Uses Ollama RAG Copilot when available, with grounded state machine logic.
        """
        executed_actions = [h["action"] for h in self.history]
        has_logs = "collect_security_logs" in executed_actions
        has_entities = "analyze_suspicious_entities" in executed_actions
        has_correlations = "correlate_events" in executed_actions
        has_quarantine = "quarantine_account" in executed_actions
        has_firewall = "modify_network_control_config" in executed_actions

        # Step 1: Collect logs
        if not has_logs:
            return {
                "thought": "Investigation initiated. First, retrieve all security events and communication evidence for this case.",
                "action": "collect_security_logs",
                "params": {},
            }

        # Step 2: Analyze entities
        if not has_entities:
            return {
                "thought": "Evidence logs gathered. Next, perform NER extraction and graph centrality analysis to identify high-degree suspect nodes.",
                "action": "analyze_suspicious_entities",
                "params": {},
            }

        # Step 3: Correlate hidden links
        if not has_correlations:
            return {
                "thought": "Entities identified. Running hidden-link engine to uncover covert associations and syndicates.",
                "action": "correlate_events",
                "params": {},
            }

        # Step 4: Quarantine threat actor
        if not has_quarantine:
            suspect_id = self._discovered_entities.get("primary_suspect_id", "syn-ent-001")
            suspect_val = self._discovered_entities.get("primary_suspect", "203.0.113.42")
            return {
                "thought": f"High centrality threat actor confirmed ({suspect_val}). Applying internal account quarantine.",
                "action": "quarantine_account",
                "params": {"entity_id": suspect_id},
            }

        # Step 5: AI determines perimeter defense (Out-of-scope trigger)
        if not has_firewall:
            suspect_ip = self._discovered_entities.get("primary_suspect_ip", "203.0.113.42")
            ai_reasoning = await self._query_rag_for_remediation(suspect_ip)
            return {
                "thought": ai_reasoning,
                "action": "modify_network_control_config",
                "params": {
                    "rule_id": "fwr-002",
                    "suspect_ip": suspect_ip,
                    "modification_type": "add_block",
                },
            }

        # Step 6: Final Assessment
        return {
            "thought": "All remediation pathways evaluated. Generating comprehensive Section 65B-admissible incident assessment report.",
            "action": "generate_incident_assessment",
            "params": {},
        }

    async def _query_rag_for_remediation(self, suspect_ip: str) -> str:
        """Call the RAG copilot to reason about perimeter defense. Abstains honestly when offline."""
        try:
            from rag.copilot import copilot_query
            q = (
                f"Threat actor IP {suspect_ip} demonstrates persistent attack behavior. "
                "Account quarantine is applied. What perimeter network defense is recommended to prevent re-entry?"
            )
            # copilot_query is async with signature (db, case_id, question, top_k).
            # Previously called positionally, un-awaited, and with the wrong arg
            # order — so it always raised and the fabricated fallback below always won.
            res = await copilot_query(self.db, self.case_id, q, top_k=2)
            answer = res.get("answer", "")
            if answer and len(answer) > 30 and "No evidence" not in answer:
                return f"AI Analysis: {answer[:250]}. Recommending perimeter firewall block for {suspect_ip}."
        except Exception:
            pass

        # No fabricated assessment when the language model is unavailable.
        return (
            "AI-generated remediation assessment unavailable — the language model could "
            "not be reached. No AI assessment is being shown."
        )

    # ── Persistence & Audit Logging ──────────────────────────────────────────

    async def _log_action(self, action_type: str, description: str, details: dict, status: str):
        entry = {
            "id": str(uuid.uuid4()),
            "session_id": self.session_id,
            "case_id": self.case_id,
            "action_type": action_type,
            "description": description,
            "details": details,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.actions.append(entry)
        await self._persist_action(entry)
        await self._write_to_audit_chain(action_type, details, status)

    async def _write_to_audit_chain(self, action: str, details: dict, status: str):
        """Append to CyberDrishti's SHA-256 blockchain-style audit chain."""
        try:
            from sqlalchemy import text
            from db.models import AuditLog

            result = await self.db.execute(
                text("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1")
            )
            last_row = result.fetchone()
            prev_hash = last_row[0] if last_row else "0" * 64

            now = datetime.now(timezone.utc)
            final_details = {
                **details,
                "session_id": self.session_id,
                "armoriq_status": status,
            }
            entry_data = json.dumps({
                "action": f"ARMORIQ_{action}",
                "user_id": None,
                "resource_id": self.case_id,
                "details": final_details,
                "timestamp": now.isoformat(),
            }, sort_keys=True)

            entry_hash = hashlib.sha256((prev_hash + entry_data).encode()).hexdigest()

            audit_entry = AuditLog(
                prev_hash=prev_hash,
                entry_hash=entry_hash,
                action=f"ARMORIQ_{action}",
                resource_type="agent_session",
                resource_id=self.case_id,
                details_json=final_details,
                event_timestamp=now,
            )
            self.db.add(audit_entry)
            await self.db.flush()
        except Exception as exc:
            logger.warning(f"[Agent] Audit chain write failed: {exc}")

    async def _set_status(self, status: str):
        self.status = status
        await self._update_session_status(status)

    async def _persist_session(self):
        try:
            from sqlalchemy import text
            await self.db.execute(
                text("""
                    INSERT INTO agent_sessions
                        (id, case_id, status, triggered_by, started_at, actions_json)
                    VALUES (:id, :case_id, :status, :triggered_by, NOW(), :actions)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": self.session_id,
                    "case_id": self.case_id,
                    "status": self.status,
                    "triggered_by": self.triggered_by,
                    "actions": json.dumps([]),
                }
            )
            await self.db.commit()
        except Exception as exc:
            logger.warning(f"[Agent] Session persist failed: {exc}")

    async def _update_session_status(self, status: str):
        try:
            from sqlalchemy import text
            await self.db.execute(
                text("""
                    UPDATE agent_sessions
                    SET status = :status, actions_json = :actions
                    WHERE id = :id
                """),
                {
                    "id": self.session_id,
                    "status": status,
                    "actions": json.dumps(self.actions),
                }
            )
            await self.db.commit()
        except Exception as exc:
            logger.warning(f"[Agent] Session status update failed: {exc}")

    async def _update_session_completed(self):
        try:
            from sqlalchemy import text
            await self.db.execute(
                text("""
                    UPDATE agent_sessions
                    SET status = 'completed', completed_at = NOW(), actions_json = :actions
                    WHERE id = :id
                """),
                {"id": self.session_id, "actions": json.dumps(self.actions)}
            )
            await self.db.commit()
        except Exception as exc:
            logger.warning(f"[Agent] Session completion update failed: {exc}")

    async def _persist_action(self, entry: dict):
        try:
            from sqlalchemy import text
            await self.db.execute(
                text("""
                    INSERT INTO agent_actions
                        (id, session_id, case_id, action_type, description,
                         status, details_json, created_at)
                    VALUES
                        (:id, :session_id, :case_id, :action_type, :description,
                         :status, :details, NOW())
                """),
                {
                    "id": entry["id"],
                    "session_id": self.session_id,
                    "case_id": self.case_id,
                    "action_type": entry["action_type"],
                    "description": entry["description"],
                    "status": entry["status"],
                    "details": json.dumps(entry["details"]),
                }
            )
            await self.db.commit()
        except Exception as exc:
            logger.warning(f"[Agent] Action persist failed: {exc}")

    async def _persist_hold(self):
        if not self.pending_hold:
            return
        try:
            from sqlalchemy import text
            hold = self.pending_hold
            await self.db.execute(
                text("""
                    INSERT INTO agent_holds
                        (id, session_id, case_id, action, description,
                         ai_reasoning, authorization_boundary, risk_level,
                         affected_resource_json, tool_params_json,
                         armoriq_reason, status, created_at)
                    VALUES
                        (:id, :session_id, :case_id, :action, :description,
                         :ai_reasoning, :authorization_boundary, :risk_level,
                         :affected_resource, :tool_params,
                         :armoriq_reason, :status, NOW())
                """),
                {
                    "id": hold["hold_id"],
                    "session_id": self.session_id,
                    "case_id": self.case_id,
                    "action": hold["action"],
                    "description": hold["description"],
                    "ai_reasoning": hold["ai_reasoning"],
                    "authorization_boundary": hold["authorization_boundary"],
                    "risk_level": hold["risk_level"],
                    "affected_resource": json.dumps(hold["affected_resource"]),
                    "tool_params": json.dumps({
                        k: v for k, v in hold["tool_params"].items() if k != "db"
                    }),
                    "armoriq_reason": hold["armoriq_reason"],
                    "status": hold["status"],
                }
            )
            await self.db.commit()
        except Exception as exc:
            logger.warning(f"[Agent] Hold persist failed: {exc}")

    def _build_summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "case_id": self.case_id,
            "status": self.status,
            "total_actions": len(self.actions),
            "history_turns": len(self.history),
            "actions": self.actions,
            "pending_hold": self.pending_hold,
        }


def _summarize(result: Any) -> str:
    if result is None:
        return "None"
    if isinstance(result, dict):
        return json.dumps({k: v for k, v in result.items() if k != "db"})[:200]
    return str(result)[:200]
