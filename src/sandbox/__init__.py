"""
Sandbox package: E2B cloud code execution with local fallback.
"""
from .executor import SandboxExecutor, SandboxResult, SANDBOX_PRELUDE

__all__ = ["SandboxExecutor", "SandboxResult", "SANDBOX_PRELUDE"]
