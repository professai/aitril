"""
Artifact - Agent-to-agent artifact exchange system.

Enables proper handoff of work products between agents without truncation or loss.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime


@dataclass
class AgentArtifact:
    """
    Structured artifact for agent-to-agent communication.

    Ensures complete content transfer without truncation or loss.
    """
    type: str  # "plan", "code", "file", "deployment", "data"
    content: Any  # Full content, never truncated
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize metadata with defaults."""
        if "created_at" not in self.metadata:
            self.metadata["created_at"] = datetime.now().isoformat()
        if "size" not in self.metadata:
            self.metadata["size"] = len(str(self.content))

    @property
    def source_agent(self) -> Optional[str]:
        """Get the agent that created this artifact."""
        return self.metadata.get("source_agent")

    @property
    def target_agent(self) -> Optional[str]:
        """Get the intended recipient agent."""
        return self.metadata.get("target_agent")

    @property
    def requires_action(self) -> bool:
        """Check if this artifact requires action from target agent."""
        return self.metadata.get("requires_action", False)

    def verify(self) -> bool:
        """Verify artifact has valid content."""
        if not self.content:
            return False
        if self.type == "file" and self.metadata.get("size", 0) == 0:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert artifact to dictionary for storage."""
        return {
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentArtifact":
        """Create artifact from dictionary."""
        return cls(
            type=data["type"],
            content=data["content"],
            metadata=data.get("metadata", {})
        )


class ArtifactRegistry:
    """
    Registry to track artifacts during multi-agent workflows.

    Ensures no artifact is lost or truncated during handoffs.
    """

    def __init__(self):
        self.artifacts: Dict[str, AgentArtifact] = {}
        self._artifact_counter = 0

    def register(self, artifact: AgentArtifact) -> str:
        """
        Register an artifact and return its ID.

        Args:
            artifact: The artifact to register

        Returns:
            str: Unique artifact ID
        """
        self._artifact_counter += 1
        artifact_id = f"artifact_{self._artifact_counter}"
        self.artifacts[artifact_id] = artifact
        return artifact_id

    def get(self, artifact_id: str) -> Optional[AgentArtifact]:
        """Get an artifact by ID."""
        return self.artifacts.get(artifact_id)

    def get_by_type(self, artifact_type: str) -> list[AgentArtifact]:
        """Get all artifacts of a specific type."""
        return [a for a in self.artifacts.values() if a.type == artifact_type]

    def get_for_agent(self, agent_name: str) -> list[AgentArtifact]:
        """Get all artifacts intended for a specific agent."""
        return [
            a for a in self.artifacts.values()
            if a.target_agent == agent_name
        ]

    def verify_all(self) -> Dict[str, bool]:
        """Verify all artifacts have valid content."""
        return {
            artifact_id: artifact.verify()
            for artifact_id, artifact in self.artifacts.items()
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all artifacts."""
        return {
            "total": len(self.artifacts),
            "by_type": self._count_by_type(),
            "verification": self.verify_all()
        }

    def _count_by_type(self) -> Dict[str, int]:
        """Count artifacts by type."""
        counts = {}
        for artifact in self.artifacts.values():
            counts[artifact.type] = counts.get(artifact.type, 0) + 1
        return counts
