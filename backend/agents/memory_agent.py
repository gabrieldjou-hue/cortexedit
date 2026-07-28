"""
memory_agent.py
---------------
Agente 21 — Memoria.
Armazena preferencias, presets, estilos, historico e modelos.
Persiste preferencias no banco de dados SQLite.
"""

import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent, AgentResult
from database import SessionLocal
import crud

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    """
    Banco de memoria do sistema.
    Persiste preferencias de usuario, estilos recorrentes e historico
    de producoes para acelerar decisoes futuras.
    """

    def __init__(self):
        super().__init__("memory")

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = []

        action = task.get("action", "read")
        profile = task.get("profile", {})
        profile_name = profile.get("name", "default")

        db = SessionLocal()
        try:
            if action == "save":
                key = task.get("key", f"profile_{profile_name}")
                value = task.get("value", profile)
                crud.save_preference(db, key, value)
                logs.append(f"Memoria: preferencia salva '{key}' no banco de dados")
                return self._make_result(
                    success=True,
                    data={"action": "saved", "key": key, "stored": True},
                    extra_logs=logs,
                    confidence=1.0,
                    limitations=limitations,
                )

            if action == "delete":
                key = task.get("key", "")
                deleted = crud.delete_preference(db, key)
                if deleted:
                    logs.append(f"Memoria: preferencia removida '{key}' do banco de dados")
                else:
                    logs.append(f"Memoria: preferencia '{key}' nao encontrada")
                return self._make_result(
                    success=True,
                    data={"action": "deleted", "key": key, "found": deleted},
                    extra_logs=logs,
                    confidence=1.0,
                    limitations=limitations,
                )

            preset_key = f"profile_{profile_name}"
            stored = crud.get_preference(db, preset_key)

            all_prefs = crud.list_preferences(db)
            profiles_found = [p.profile_name for p in all_prefs]

            logs.append(f"Memoria: {len(profiles_found)} perfil(is) armazenado(s) no banco de dados")
            if stored:
                logs.append(f"Memoria: profile '{profile_name}' possui preferencias salvas.")
            else:
                logs.append(f"Memoria: nenhuma preferencia encontrada para '{profile_name}'.")

            return self._make_result(
                success=True,
                data={
                    "stored_preferences": stored.preferences if stored else {},
                    "profiles_available": profiles_found,
                    "total_entries": len(all_prefs),
                },
                extra_logs=logs,
                confidence=1.0,
                limitations=limitations,
                suggestions=[],
            )
        finally:
            db.close()
