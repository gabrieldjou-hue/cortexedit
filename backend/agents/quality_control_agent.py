"""
quality_control_agent.py
------------------------
Agente de Controle de Qualidade (Artigo 5).
Responsavel por verificar integridade, conferir especificacoes,
detectar erros e aprovar ou reprovar entregas.
"""

import os
import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class QualityControlAgent(BaseAgent):
    def __init__(self):
        super().__init__("quality_control")

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        issues = []

        exports = task.get("exports", {})
        edl = task.get("edl", {})
        profile = task.get("profile", {})
        export_formats = task.get("export_formats", [])

        output_files = exports.get("output_files", []) if exports else []

        logs.append(f"Iniciando controle de qualidade para {len(output_files)} arquivo(s)...")

        if not output_files:
            issues.append("Nenhum arquivo de saida gerado.")

        for f in output_files:
            filename = f.get("filename", "")
            fmt = f.get("format", "")
            size = f.get("size_mb", 0)

            if size == 0:
                issues.append(f"{filename} ({fmt}): tamanho zero.")
            elif fmt != "subtitle" and size < 0.1:
                issues.append(f"{filename} ({fmt}): tamanho suspeito ({size} MB).")

            logs.append(f"  {filename}: {size} MB [{fmt}]")

        n_clips = len(edl.get("clips", []))
        total_dur = edl.get("total_duration", 0.0)

        if n_clips == 0:
            issues.append("EDL vazia: nenhum clip na timeline.")

        logs.append(f"EDL: {n_clips} clip(s), {total_dur:.1f}s")

        expected_count = len(export_formats)
        actual_count = len([f for f in output_files if f.get("format") in export_formats])
        if expected_count > 0 and actual_count < expected_count:
            issues.append(f"Exportacoes incompletas: {actual_count}/{expected_count} formatos gerados.")

        approved = len(issues) == 0
        qc_report = {
            "approved": approved,
            "issues": issues,
            "files_checked": len(output_files),
            "total_duration": total_dur,
            "profile": profile.get("name", "default"),
        }

        if approved:
            logs.append("QC: Todos os itens aprovados.")
        else:
            logs.append(f"QC: {len(issues)} issue(s) encontrada(s).")

        return self._make_result(
            success=True,
            data=qc_report,
            extra_logs=logs,
            confidence=0.9 if approved else 0.6,
            limitations=[],
            suggestions=issues if not approved else [],
        )
