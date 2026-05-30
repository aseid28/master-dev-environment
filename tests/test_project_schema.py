import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_loop.project_schema import Project, Milestone, ProjectConfig, CredentialPermission


FIXTURE = Path(__file__).parent.parent / "projects" / "example-triage-tool" / "project.yaml"


def test_load_project_yaml():
    p = Project.load(FIXTURE)
    assert p.project.id == "triage-tool"
    assert p.project.name == "Triage Tool"
    assert p.project.cost_cap_usd == 15.0
    assert p.project.write_enabled is False
    assert len(p.milestones) == 3


def test_milestone_order_and_ids():
    p = Project.load(FIXTURE)
    ids = [m.id for m in p.milestones]
    assert ids == ["m1", "m2", "m3"]


def test_milestone_blocked_by():
    p = Project.load(FIXTURE)
    assert p.get_milestone("m1").blocked_by == []
    assert p.get_milestone("m2").blocked_by == ["m1"]
    assert p.get_milestone("m3").blocked_by == ["m2"]


def test_get_milestone_found():
    p = Project.load(FIXTURE)
    m = p.get_milestone("m2")
    assert m.name == "Urgency Scoring"


def test_get_milestone_not_found():
    p = Project.load(FIXTURE)
    with pytest.raises(KeyError):
        p.get_milestone("m99")


def test_next_milestone():
    p = Project.load(FIXTURE)
    assert p.next_milestone("m1").id == "m2"
    assert p.next_milestone("m2").id == "m3"
    assert p.next_milestone("m3") is None


def test_credentials():
    p = Project.load(FIXTURE)
    assert len(p.credentials) == 1
    assert p.credentials[0].key == "ANTHROPIC_API_KEY"
    assert p.credentials[0].permission == CredentialPermission.read


def test_empty_milestones_rejected():
    with pytest.raises(Exception):
        Project.model_validate({
            "project": {
                "id": "x", "name": "X", "repo": "git@g.com:x/x.git",
                "cost_cap_usd": 5.0,
            },
            "milestones": [],
        })


def test_cost_cap_bounds():
    with pytest.raises(Exception):
        ProjectConfig(id="x", name="X", repo="r", cost_cap_usd=0)
    with pytest.raises(Exception):
        ProjectConfig(id="x", name="X", repo="r", cost_cap_usd=9999)
