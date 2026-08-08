import random
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ToolResult:
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }

class BaseTool:
    name: str = "base"
    description: str = ""
    risk_level: str = "low"
    timeout_seconds: int = 30
    required_permissions: list = []

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        raise NotImplementedError

    def validate_input(self, context: Dict) -> bool:
        return True

class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Get the current git repository status"
    risk_level = "low"
    required_permissions = ["filesystem.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        repo = context.get("repository", "unknown")
        branch = context.get("branch", "main")
        return ToolResult(
            success=True,
            output={
                "repository": repo,
                "branch": branch,
                "status": "clean" if random.random() > 0.3 else "modified",
                "staged": random.randint(0, 3),
                "unstaged": random.randint(0, 5),
                "dry_run": dry_run,
            },
        ).to_dict()

class GitLogTool(BaseTool):
    name = "git_log"
    description = "Get recent git commit history"
    risk_level = "low"
    required_permissions = ["filesystem.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        repo = context.get("repository", "unknown")
        count = context.get("count", 10)
        commits = []
        authors = ["alice@company.com", "bob@company.com", "carol@company.com", "dave@company.com"]
        messages = [
            "fix: resolve null pointer in payment handler",
            "feat: add retry logic to CI runner",
            "chore: update dependencies",
            "fix: correct race condition in test runner",
            "feat: implement webhook handler",
            "refactor: extract common utilities",
        ]
        for i in range(min(count, 10)):
            commits.append({
                "hash": f"{'a1b2c3d'[:7]}",
                "author": random.choice(authors),
                "message": random.choice(messages),
                "timestamp": f"2024-01-{15 + i:02d}T10:00:00Z",
            })
        return ToolResult(
            success=True,
            output={"repository": repo, "commits": commits, "dry_run": dry_run},
        ).to_dict()

class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "Get diff of recent changes"
    risk_level = "low"
    required_permissions = ["filesystem.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        commit = context.get("commit_hash", "HEAD")
        return ToolResult(
            success=True,
            output={
                "commit": commit,
                "files_changed": random.randint(1, 8),
                "insertions": random.randint(5, 200),
                "deletions": random.randint(0, 50),
                "dry_run": dry_run,
            },
        ).to_dict()

class SearchRepositoryTool(BaseTool):
    name = "search_repository"
    description = "Search the local repository for patterns"
    risk_level = "low"
    required_permissions = ["filesystem.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        query = context.get("query", "error")
        repo = context.get("repository", "unknown")
        return ToolResult(
            success=True,
            output={
                "repository": repo,
                "query": query,
                "matches": random.randint(0, 25),
                "files": [f"src/module_{i}.py" for i in range(random.randint(1, 4))],
                "dry_run": dry_run,
            },
        ).to_dict()

class RunTestsTool(BaseTool):
    name = "run_tests"
    description = "Execute the test suite for a repository"
    risk_level = "medium"
    required_permissions = ["terminal.execute", "filesystem.read"]
    timeout_seconds = 120

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        repo = context.get("repository", "unknown")
        if dry_run:
            return ToolResult(
                success=True,
                output={"dry_run": True, "would_run": "pytest tests/", "repository": repo},
            ).to_dict()
        return ToolResult(
            success=True,
            output={
                "repository": repo,
                "passed": random.randint(80, 150),
                "failed": random.randint(0, 5),
                "duration_seconds": random.uniform(15, 90),
            },
        ).to_dict()

class GetGithubPRTool(BaseTool):
    name = "get_github_pull_request"
    description = "Retrieve GitHub pull request details"
    risk_level = "low"
    required_permissions = ["github.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        repo = context.get("repository", "org/repo")
        return ToolResult(
            success=True,
            output={
                "repository": repo,
                "pr_number": random.randint(100, 999),
                "title": "Fix CI failure in test runner",
                "author": "alice",
                "status": "open",
                "reviewers": ["bob", "carol"],
                "ci_status": random.choice(["passing", "failing", "pending"]),
                "dry_run": dry_run,
            },
        ).to_dict()

class GetGithubCommitTool(BaseTool):
    name = "get_github_commit"
    description = "Retrieve GitHub commit details and CI status"
    risk_level = "low"
    required_permissions = ["github.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        commit = context.get("commit_hash", "a1b2c3d")
        return ToolResult(
            success=True,
            output={
                "commit": commit,
                "author": random.choice(["alice", "bob", "carol"]),
                "message": "fix: resolve null pointer in payment handler",
                "files_changed": random.randint(1, 10),
                "ci_checks": [
                    {"name": "unit-tests", "status": "failed"},
                    {"name": "lint", "status": "passed"},
                ],
                "dry_run": dry_run,
            },
        ).to_dict()

class GetGithubCITool(BaseTool):
    name = "get_github_ci"
    description = "Retrieve CI/CD pipeline status and logs"
    risk_level = "low"
    required_permissions = ["github.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        build_id = context.get("build_id", random.randint(1000, 9999))
        return ToolResult(
            success=True,
            output={
                "build_id": build_id,
                "status": "failed",
                "failure_step": random.choice(["unit-tests", "integration-tests", "build"]),
                "log_tail": "AssertionError: expected 200 got 500\nTraceback (most recent call last)...",
                "duration_seconds": random.randint(45, 300),
                "dry_run": dry_run,
            },
        ).to_dict()

class SearchDocumentationTool(BaseTool):
    name = "search_documentation"
    description = "Search internal or external documentation"
    risk_level = "low"
    required_permissions = ["browser.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        query = context.get("query", "CI failure")
        return ToolResult(
            success=True,
            output={
                "query": query,
                "results": [
                    {"title": "Debugging CI Failures", "url": "docs/ci/debugging.md", "relevance": 0.92},
                    {"title": "Test Environment Setup", "url": "docs/testing/setup.md", "relevance": 0.78},
                ],
                "dry_run": dry_run,
            },
        ).to_dict()

class SearchLocalHistoryTool(BaseTool):
    name = "search_local_history"
    description = "Search MOMENTUM's local observation history for similar past events"
    risk_level = "low"
    required_permissions = ["filesystem.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        trigger = context.get("trigger_event", "ci_build_failed")
        return ToolResult(
            success=True,
            output={
                "query": trigger,
                "similar_events_found": random.randint(5, 30),
                "most_recent": "2 days ago",
                "common_resolution_time_minutes": random.randint(8, 45),
                "dry_run": dry_run,
            },
        ).to_dict()

class FindCodeOwnerTool(BaseTool):
    name = "find_code_owner"
    description = "Identify the code owner for a file or module based on git history"
    risk_level = "low"
    required_permissions = ["github.read", "filesystem.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        commit = context.get("commit_hash", "a1b2c3d")
        owners = ["alice@company.com", "bob@company.com", "carol@company.com"]
        return ToolResult(
            success=True,
            output={
                "commit": commit,
                "primary_owner": random.choice(owners),
                "recent_contributors": random.sample(owners, k=min(2, len(owners))),
                "confidence": random.uniform(0.7, 0.98),
                "dry_run": dry_run,
            },
        ).to_dict()

class ClassifyCIFailureTool(BaseTool):
    name = "classify_ci_failure"
    description = "Classify the type and likely root cause of a CI failure"
    risk_level = "low"
    required_permissions = ["github.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        build_id = context.get("build_id", 1234)
        categories = ["test_failure", "build_error", "flaky_test", "dependency_issue", "timeout"]
        return ToolResult(
            success=True,
            output={
                "build_id": build_id,
                "category": random.choice(categories),
                "confidence": random.uniform(0.65, 0.97),
                "likely_cause": "Unit test assertion failed after recent change to payment module",
                "is_flaky": random.random() < 0.2,
                "affected_tests": [f"test_payment_{i}" for i in range(random.randint(1, 4))],
                "dry_run": dry_run,
            },
        ).to_dict()

class CreateDraftIssueTool(BaseTool):
    name = "create_draft_issue"
    description = "Create a draft GitHub issue (not submitted without explicit approval)"
    risk_level = "low"
    required_permissions = ["github.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        build_id = context.get("build_id", 1234)
        return ToolResult(
            success=True,
            output={
                "draft": True,
                "title": f"[CI] Build #{build_id} failed — needs investigation",
                "body": "Auto-generated draft. Please review before submitting.",
                "labels": ["ci-failure", "needs-triage"],
                "status": "draft_only",
                "submitted": False,
                "dry_run": dry_run,
            },
        ).to_dict()

class CreateDraftMessageTool(BaseTool):
    name = "create_draft_message"
    description = "Create a draft Slack/team notification message (not sent without explicit approval)"
    risk_level = "low"
    required_permissions = ["communication.draft"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        repo = context.get("repository", "unknown")
        owner = context.get("owner", "team")
        build_id = context.get("build_id", 1234)
        return ToolResult(
            success=True,
            output={
                "draft": True,
                "channel": "#engineering-alerts",
                "message": f"🔴 CI Build #{build_id} failed in `{repo}`. cc @{owner}. Investigating...",
                "status": "draft_only",
                "sent": False,
                "dry_run": dry_run,
            },
        ).to_dict()

class GenerateReleaseNotesTool(BaseTool):
    name = "generate_release_notes"
    description = "Generate draft release notes from recent commits and merged PRs"
    risk_level = "low"
    required_permissions = ["github.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        repo = context.get("repository", "unknown")
        return ToolResult(
            success=True,
            output={
                "repository": repo,
                "version": "v1.4.2",
                "draft_notes": (
                    "## What's Changed\n"
                    "- fix: resolve null pointer in payment handler\n"
                    "- feat: add retry logic to CI runner\n"
                    "- chore: update dependencies\n"
                ),
                "pr_count": random.randint(3, 15),
                "contributor_count": random.randint(2, 8),
                "status": "draft_only",
                "dry_run": dry_run,
            },
        ).to_dict()

class SummarizeIncidentTool(BaseTool):
    name = "summarize_incident"
    description = "Generate a structured incident summary from CI and communication data"
    risk_level = "low"
    required_permissions = ["github.read", "browser.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        build_id = context.get("build_id", 1234)
        return ToolResult(
            success=True,
            output={
                "build_id": build_id,
                "summary": (
                    f"Incident #{build_id}: CI pipeline failure detected. "
                    "Root cause: unit test assertion error in payment module. "
                    "Impact: low (no production deployment blocked). "
                    "Status: under investigation."
                ),
                "severity": random.choice(["low", "medium"]),
                "estimated_resolution_minutes": random.randint(15, 90),
                "dry_run": dry_run,
            },
        ).to_dict()

ALL_TOOLS = [
    GitStatusTool(),
    GitLogTool(),
    GitDiffTool(),
    SearchRepositoryTool(),
    RunTestsTool(),
    GetGithubPRTool(),
    GetGithubCommitTool(),
    GetGithubCITool(),
    SearchDocumentationTool(),
    SearchLocalHistoryTool(),
    FindCodeOwnerTool(),
    ClassifyCIFailureTool(),
    CreateDraftIssueTool(),
    CreateDraftMessageTool(),
    GenerateReleaseNotesTool(),
    SummarizeIncidentTool(),
]
