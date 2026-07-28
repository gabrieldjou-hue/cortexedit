"""
base_agent.py
-------------
Classe abstrata que define o contrato de todos os agentes do SIPA.
Nenhum agente pode desviar desta interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time


@dataclass
class AgentResult:
    """
    Padrão de entrega obrigatório (Artigo 8 do Contrato).
    """
    agent_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    files: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    confidence: float = 1.0
    limitations: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Interface oficial de todo agente do sistema.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._start_time: Optional[float] = None

    @abstractmethod
    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        """
        Executa a tarefa designada pelo Master.
        - task: dicionário com instruções e dados de entrada
        - context: SharedContext (somente leitura para agentes especializados)
        Retorna AgentResult obrigatoriamente.
        """
        ...

    def _start_timer(self):
        self._start_time = time.time()

    def _elapsed(self) -> float:
        return round(time.time() - self._start_time, 3) if self._start_time else 0.0

    def _make_result(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[List[str]] = None,
        extra_logs: Optional[List[str]] = None,
        confidence: float = 1.0,
        limitations: Optional[List[str]] = None,
        suggestions: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            success=success,
            data=data,
            files=files or [],
            logs=extra_logs or [],
            execution_time=self._elapsed(),
            confidence=confidence,
            limitations=limitations or [],
            suggestions=suggestions or [],
            error=error,
        )
