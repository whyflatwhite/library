"""Статические проверки эксплуатационных требований к контейнерному окружению.

Docker для них не нужен: тесты читают Dockerfile, .dockerignore и docker-compose.yml.
Полную проверку на живом окружении выполняет make container-check.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
DOCKERIGNORE = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
SERVICES = COMPOSE["services"]


def _instructions(name):
    lines = DOCKERFILE.splitlines()
    return [line.split(None, 1)[1] for line in lines if line.startswith(name + " ")]


def _has_pinned_tag(image):
    return ":" in image and not image.endswith(":latest")


def test_dockerfile_base_image_is_pinned():
    images = _instructions("FROM")
    assert images
    assert all(_has_pinned_tag(image) for image in images)


def test_dockerfile_runs_as_non_root_user():
    users = _instructions("USER")
    assert users
    assert users[-1].split(":")[0] not in ("root", "0")


def test_dockerfile_has_no_secrets():
    assert not re.search(r"password|secret|token", DOCKERFILE, re.IGNORECASE)


def test_dockerfile_cmd_uses_exec_form_for_signal_handling():
    cmd = _instructions("CMD")[-1]
    assert cmd.startswith('["uvicorn"')


def test_dockerignore_keeps_secrets_and_git_out_of_image():
    assert ".env" in DOCKERIGNORE
    assert ".git" in DOCKERIGNORE


def test_compose_images_are_pinned():
    for name, service in SERVICES.items():
        assert _has_pinned_tag(service["image"]), name


def test_database_port_is_not_published():
    assert "ports" not in SERVICES["db"]


def test_only_api_publishes_a_port():
    published = [name for name, service in SERVICES.items() if service.get("ports")]
    assert published == ["api"]


def test_all_services_have_enabled_healthcheck():
    for name, service in SERVICES.items():
        healthcheck = service.get("healthcheck")
        assert healthcheck, name
        assert not healthcheck.get("disable"), name
        assert healthcheck["test"] != ["NONE"], name


def test_api_starts_only_after_healthy_database():
    assert SERVICES["api"]["depends_on"]["db"]["condition"] == "service_healthy"


def test_all_services_have_resource_limits():
    for name, service in SERVICES.items():
        assert service.get("mem_limit"), name
        assert service.get("cpus"), name


def test_database_data_is_stored_in_named_volume():
    assert SERVICES["db"]["volumes"] == ["pgdata:/var/lib/postgresql/data"]
    assert "pgdata" in COMPOSE["volumes"]


def test_source_code_is_not_mounted_into_container():
    assert not SERVICES["api"].get("volumes")


def test_services_share_internal_network():
    assert "backend" in COMPOSE["networks"]
    for name, service in SERVICES.items():
        assert service["networks"] == ["backend"], name


def test_passwords_come_from_environment_not_from_file():
    password = SERVICES["db"]["environment"]["POSTGRES_PASSWORD"]
    assert password.startswith("${")
    assert "library_pass" not in (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "${POSTGRES_PASSWORD}" in SERVICES["api"]["environment"]["DATABASE_URL"]


def test_api_has_graceful_stop_period():
    assert SERVICES["api"]["stop_grace_period"]
