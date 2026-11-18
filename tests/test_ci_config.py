from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_TEXT = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
WORKFLOW = yaml.safe_load(WORKFLOW_TEXT)
JOBS = WORKFLOW["jobs"]
TRIGGERS = WORKFLOW.get("on", WORKFLOW.get(True))
CODEOWNERS = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
MANDATORY = ["style", "tests", "migrations", "backup", "security", "container-check"]
DIND_HOST = "tcp://docker:2375"
DOCKER_COMMANDS = ("docker ", "make container-check", "ci_db_check.sh")


def _steps(job):
    return JOBS[job]["steps"]


def _commands(*names):
    return " ".join(step.get("run", "") for name in names for step in _steps(name))


def test_pipeline_runs_on_push_and_pull_request():
    assert "push" in TRIGGERS
    assert "pull_request" in TRIGGERS


def test_pipeline_has_all_required_stages():
    for name in MANDATORY + ["build", "publish"]:
        assert name in JOBS, name


def test_every_job_runs_in_docker_in_docker():
    for name, job in JOBS.items():
        assert job.get("container"), name
        dind = job["services"]["docker"]
        assert "dind" in dind["image"], name
        assert not dind["image"].endswith(":latest"), name
        assert "--privileged" in dind["options"], name


def test_docker_commands_use_the_dind_daemon():
    for name, job in JOBS.items():
        job_host = job.get("env", {}).get("DOCKER_HOST")
        for step in _steps(name):
            run = step.get("run", "")
            if any(command in run for command in DOCKER_COMMANDS):
                assert job_host == DIND_HOST or f"DOCKER_HOST={DIND_HOST}" in run, (
                    name,
                    step.get("name"),
                )


def test_build_waits_for_every_mandatory_check():
    assert set(MANDATORY) <= set(JOBS["build"]["needs"])


def test_publish_waits_for_every_check_and_runs_only_on_main():
    assert set(MANDATORY + ["build"]) <= set(JOBS["publish"]["needs"])
    assert "refs/heads/main" in JOBS["publish"]["if"]
    assert "push" in JOBS["publish"]["if"]


def test_no_step_ignores_failures():
    assert "continue-on-error" not in WORKFLOW_TEXT
    assert "|| true" not in WORKFLOW_TEXT


def test_image_tag_is_tied_to_commit_sha_and_is_not_latest():
    tag_lines = [line for line in WORKFLOW_TEXT.splitlines() if "TAG=" in line]
    assert tag_lines
    assert all("GITHUB_SHA" in line for line in tag_lines)
    assert ":latest" not in WORKFLOW_TEXT


def test_secrets_are_not_hardcoded():
    assert "secrets.GITHUB_TOKEN" in WORKFLOW_TEXT
    assert "CI_DB_PASSWORD: ${{ secrets.CI_DB_PASSWORD }}" in WORKFLOW_TEXT
    for line in WORKFLOW_TEXT.splitlines():
        if line.strip().startswith("- name:") or "--password-stdin" in line:
            continue
        if "PASSWORD" in line.upper():
            assert "CI_DB_PASSWORD" in line, line


def test_dependencies_are_cached():
    for name in ["style", "tests", "security"]:
        caches = [s for s in _steps(name) if s.get("uses", "").startswith("actions/cache@")]
        assert caches and "pip" in caches[0]["with"]["path"], name


def test_security_stage_scans_code_dependencies_and_secrets():
    commands = _commands("security")
    assert "make sast" in commands
    assert "pip-audit" in commands
    assert "gitleaks detect" in commands


def test_build_stage_scans_image_and_fails_on_findings():
    commands = _commands("build")
    assert "trivy image" in commands
    assert "--exit-code 1" in commands


def test_pipeline_uses_the_same_commands_as_local_work():
    commands = _commands(*JOBS)
    for command in ["make lint", "make test", "make sast", "make container-check"]:
        assert command in commands, command


def test_database_checks_run_on_a_separate_test_database():
    assert "POSTGRES_DB=library_ci" in _commands("migrations")
    assert "POSTGRES_DB=library_ci" in _commands("backup")


def test_codeowners_cover_critical_files():
    paths = [line.split()[0] for line in CODEOWNERS.splitlines() if line.startswith("/")]
    for critical in ["/.github/", "/tests/", "/Makefile", "/pyproject.toml", "/setup.cfg"]:
        assert critical in paths, critical
