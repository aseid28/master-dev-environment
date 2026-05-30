"""
Pydantic models for project and milestone definitions.
Loaded from project.yaml by the orchestrator and all agent-loop components.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, Field, field_validator


class CredentialPermission(str, Enum):
    read = "read"
    write = "write"


class Credential(BaseModel):
    key: str
    permission: CredentialPermission = CredentialPermission.read
    description: str = ""


class Milestone(BaseModel):
    id: str
    name: str
    description: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)


class ProjectConfig(BaseModel):
    id: str
    name: str
    repo: str
    cost_cap_usd: Annotated[float, Field(gt=0, le=1000)]
    model: str = "claude-opus-4-8"
    write_enabled: bool = False


class Project(BaseModel):
    project: ProjectConfig
    milestones: list[Milestone]
    credentials: list[Credential] = Field(default_factory=list)

    @field_validator("milestones")
    @classmethod
    def milestones_not_empty(cls, v: list[Milestone]) -> list[Milestone]:
        if not v:
            raise ValueError("Project must define at least one milestone")
        return v

    def get_milestone(self, milestone_id: str) -> Milestone:
        for m in self.milestones:
            if m.id == milestone_id:
                return m
        raise KeyError(f"Milestone '{milestone_id}' not found in project '{self.project.id}'")

    def next_milestone(self, after_id: str) -> Milestone | None:
        ids = [m.id for m in self.milestones]
        try:
            idx = ids.index(after_id)
        except ValueError:
            return None
        return self.milestones[idx + 1] if idx + 1 < len(self.milestones) else None

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)
