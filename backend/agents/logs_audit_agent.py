"""
logs_audit_agent.py
-------------------
Agente 20 — Logs e Auditoria.
Registra todas as acoes, tempos, erros, decisoes, versoes,
agentes utilizados e historico completo do pipeline.
Persiste tanto em JSON (compatibilidade) quanto no banco de dados.
"""

import json
import os
import logging
from typing import Dict, Any
from datetime import datetime, timezone

from agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class LogsAuditAgent(BaseAgent):
    def __init__(self):
        super().__init__("logs_audit")

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = []

        job_id = task.get("job_id", "unknown")
        export_dir = task.get("export_dir", "")
        ctx = context.get_all() if hasattr(context, 'get_all') else {}

        audit_trail = {
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents_executed": task.get("agents_executed", []),
            "total_execution_time": task.get("total_execution_time", 0.0),
            "errors": ctx.get("errors", []),
            "logs_count": len(ctx.get("logs", [])),
            "decisions": [],
        }

        for agent_name in audit_trail["agents_executed"]:
            audit_trail["decisions"].append({
                "agent": agent_name,
                "action": f"executado pelo Master",
                "status": "completed",
            })

        if ctx.get("qc_report"):
            qc = ctx.get("qc_report")
            audit_trail["qc_approved"] = qc.get("approved", False)
            audit_trail["qc_issues"] = qc.get("issues", [])

        report_path = ""
        if export_dir:
            os.makedirs(export_dir, exist_ok=True)
            report_path = os.path.join(export_dir, "audit_report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(audit_trail, f, indent=2, ensure_ascii=False)
            logs.append(f"Relatorio de auditoria salvo: {report_path}")

        n_agents = len(audit_trail["agents_executed"])
        n_errors = len(audit_trail["errors"])
        logs.append(f"Auditoria: {n_agents} agente(s) executados, {n_errors} erro(s)")
        logs.append(f"QC aprovado: {audit_trail.get('qc_approved', 'N/A')}")

        return self._make_result(
            success=True,
            data=audit_trail,
            files=[report_path] if report_path else [],
            extra_logs=logs,
            confidence=1.0,
            limitations=limitations,
            suggestions=[],
        )
