"""
Sandbox executor: runs Python code snippets in an E2B cloud sandbox.
Falls back to a restricted local subprocess when E2B_API_KEY is not set.

Each execution is deterministic (seeded), budget-tracked, and returns a
SandboxResult dataclass that the tree pipeline can inspect.
"""

import os
import io
import sys
import time
import logging
import textwrap
import traceback
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cost constants (E2B pricing: ~$0.000014 / second of sandbox time)
# ---------------------------------------------------------------------------
_COST_PER_SECOND_USD = 0.000014

# ---------------------------------------------------------------------------
# Deterministic prelude injected before every user snippet
# ---------------------------------------------------------------------------
SANDBOX_PRELUDE = textwrap.dedent("""\
    import random, json, sys, os
    import numpy as np
    import warnings
    from io import StringIO
    warnings.filterwarnings('ignore')

    # Deterministic seeds — every experiment reproducible
    random.seed(42)
    np.random.seed(42)
""")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class SandboxResult:
    """Returned by every executor.run() call."""
    success: bool
    stdout: str
    stderr: str
    output_files: dict[str, str]  # filename -> base64-encoded content
    execution_time_ms: int
    error: Optional[str]
    cost_estimate_usd: float = 0.0

    def summary(self) -> str:
        status = "OK" if self.success else "FAIL"
        return (
            f"[{status}] {self.execution_time_ms}ms | "
            f"${self.cost_estimate_usd:.6f} | "
            f"stdout={len(self.stdout)}chars"
        )


# ---------------------------------------------------------------------------
# Local fallback executor (no E2B key needed)
# ---------------------------------------------------------------------------
class _LocalExecutor:
    """
    Runs code in an isolated subprocess using the current Python interpreter.
    Not a real sandbox — do not use for untrusted code in production.
    Only used when E2B_API_KEY is absent (dev / CI / test mode).
    """

    def __init__(self, timeout_seconds: int = 30):
        self.timeout = timeout_seconds

    def run(self, code: str) -> SandboxResult:
        full_code = SANDBOX_PRELUDE + "\n" + code
        start = time.monotonic()
        try:
            result = subprocess.run(
                [sys.executable, "-c", full_code],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            success = result.returncode == 0
            return SandboxResult(
                success=success,
                stdout=result.stdout,
                stderr=result.stderr,
                output_files={},
                execution_time_ms=elapsed_ms,
                error=None if success else result.stderr.strip(),
                cost_estimate_usd=0.0,  # local — no cost
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return SandboxResult(
                success=False,
                stdout="",
                stderr="",
                output_files={},
                execution_time_ms=elapsed_ms,
                error=f"Execution timed out after {self.timeout}s",
                cost_estimate_usd=0.0,
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return SandboxResult(
                success=False,
                stdout="",
                stderr=traceback.format_exc(),
                output_files={},
                execution_time_ms=elapsed_ms,
                error=str(exc),
                cost_estimate_usd=0.0,
            )


# ---------------------------------------------------------------------------
# E2B cloud executor
# ---------------------------------------------------------------------------
class _E2BExecutor:
    """
    Runs code in an E2B cloud sandbox (https://e2b.dev).
    Requires E2B_API_KEY in the environment.
    """

    def __init__(self, timeout_seconds: int = 60):
        self.timeout = timeout_seconds
        self._validate_api_key()

    def _validate_api_key(self):
        if not os.getenv("E2B_API_KEY"):
            raise EnvironmentError(
                "E2B_API_KEY not set. Get your key at https://e2b.dev"
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def run(self, code: str) -> SandboxResult:
        try:
            from e2b_code_interpreter import Sandbox  # type: ignore
        except ImportError:
            raise ImportError(
                "e2b-code-interpreter is not installed. "
                "Run: pip install e2b-code-interpreter"
            )

        full_code = SANDBOX_PRELUDE + "\n" + code
        start = time.monotonic()

        try:
            with Sandbox(timeout=self.timeout) as sbx:
                execution = sbx.run_code(full_code)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                elapsed_s = elapsed_ms / 1000.0
                cost = elapsed_s * _COST_PER_SECOND_USD

                logs_out = getattr(execution.logs, "stdout", [])
                logs_err = getattr(execution.logs, "stderr", [])
                stdout_full = "\n".join(logs_out)
                stderr_full = "\n".join(logs_err)

                success = execution.error is None
                error_msg = str(execution.error) if execution.error else None

                logger.info(
                    "E2B execution: %dms $%.6f success=%s",
                    elapsed_ms, cost, success,
                )

                return SandboxResult(
                    success=success,
                    stdout=stdout_full.strip(),
                    stderr=stderr_full.strip(),
                    output_files={},
                    execution_time_ms=elapsed_ms,
                    error=error_msg,
                    cost_estimate_usd=cost,
                )

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error("E2B execution failed: %s", exc)
            return SandboxResult(
                success=False,
                stdout="",
                stderr=traceback.format_exc(),
                output_files={},
                execution_time_ms=elapsed_ms,
                error=str(exc),
                cost_estimate_usd=0.0,
            )


# ---------------------------------------------------------------------------
# Public SandboxExecutor — auto-selects E2B or local fallback
# ---------------------------------------------------------------------------
class SandboxExecutor:
    """
    Main entry point for Stage 2.

    Usage::

        executor = SandboxExecutor()
        result = executor.run("print(1 + 1)")
        print(result.stdout)   # "2"

    Auto-detects E2B_API_KEY. Falls back to local subprocess when absent.
    Tracks cumulative spend so callers can enforce a budget cap.
    """

    def __init__(self, timeout_seconds: int = 60, budget_usd: float = 1.0):
        self.budget_usd = budget_usd
        self._spent_usd = 0.0

        if os.getenv("E2B_API_KEY") and not os.getenv("E2B_API_KEY", "").startswith("your_"):
            try:
                self._backend: _E2BExecutor | _LocalExecutor = _E2BExecutor(
                    timeout_seconds=timeout_seconds
                )
                self._mode = "e2b"
                logger.info("SandboxExecutor: using E2B cloud sandbox")
            except Exception as exc:
                logger.warning("E2B init failed (%s); falling back to local executor", exc)
                self._backend = _LocalExecutor(timeout_seconds=min(timeout_seconds, 30))
                self._mode = "local"
        else:
            self._backend = _LocalExecutor(timeout_seconds=min(timeout_seconds, 30))
            self._mode = "local"
            logger.info("SandboxExecutor: using local subprocess (no E2B key)")

    @property
    def mode(self) -> str:
        """'e2b' or 'local'"""
        return self._mode

    @property
    def spent_usd(self) -> float:
        return self._spent_usd

    def budget_remaining_usd(self) -> float:
        return max(0.0, self.budget_usd - self._spent_usd)

    def run(self, code: str) -> SandboxResult:
        """
        Execute Python *code* in the sandbox.

        Args:
            code: Python source to run. SANDBOX_PRELUDE is auto-prepended.

        Returns:
            SandboxResult with stdout, stderr, timing, and cost.

        Raises:
            RuntimeError: if budget is exhausted.
        """
        if self._spent_usd >= self.budget_usd:
            raise RuntimeError(
                f"Sandbox budget exhausted: ${self._spent_usd:.4f} spent, "
                f"${self.budget_usd:.4f} limit"
            )

        result = self._backend.run(code)
        self._spent_usd += result.cost_estimate_usd
        logger.debug("Sandbox: %s", result.summary())
        return result

    def run_analysis(self, description: str, code: str) -> SandboxResult:
        """
        Convenience wrapper: logs the description, runs code, returns result.
        Used by tree nodes that want labelled executions.
        """
        logger.info("Sandbox analysis: %s", description)
        return self.run(code)