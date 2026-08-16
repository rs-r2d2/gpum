"""T055: container resolution from cgroup content (FR-029, FR-030, A-12)."""

from gpum.adapters.linux.containers import container_id_from_cgroup

DOCKER_V1 = """12:memory:/docker/3f2a9e1b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f
11:cpu,cpuacct:/docker/3f2a9e1b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f
"""

DOCKER_V2 = (
    "0::/system.slice/docker-"
    "3f2a9e1b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f.scope\n"
)

PODMAN = (
    "0::/user.slice/user-1000.slice/user@1000.service/user.slice/"
    "libpod-9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b.scope\n"
)

HOST = """12:memory:/user.slice/user-1000.slice/session-2.scope
11:cpu,cpuacct:/user.slice
0::/user.slice/user-1000.slice/session-2.scope
"""


class TestContainerDetection:
    def test_docker_cgroup_v1(self) -> None:
        assert container_id_from_cgroup(DOCKER_V1).startswith("3f2a9e1b4c5d")

    def test_docker_cgroup_v2(self) -> None:
        assert container_id_from_cgroup(DOCKER_V2).startswith("3f2a9e1b4c5d")

    def test_podman(self) -> None:
        assert container_id_from_cgroup(PODMAN).startswith("9a8b7c6d5e4f")

    def test_host_process_is_not_containerised(self) -> None:
        assert container_id_from_cgroup(HOST) is None

    def test_empty_content(self) -> None:
        assert container_id_from_cgroup("") is None


class TestNoPrivilegeEscalation:
    def test_imports_nothing_that_could_reach_a_daemon(self) -> None:
        """A-12 / Principle V: no Docker socket, no daemon, no elevation.

        Checked against the module's imports rather than its text, so the docstring may
        discuss the sockets it deliberately does not use.
        """
        import ast
        import pathlib

        import gpum.adapters.linux.containers as containers

        tree = ast.parse(pathlib.Path(containers.__file__).read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert imported <= {"__future__", "re"}, f"unexpected imports: {imported}"
