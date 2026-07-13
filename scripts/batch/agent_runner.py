"""Agent invocation dispatcher.

Supports multiple agent backends: Cursor CLI (default) and iFlow SDK.
The backend is selected via ``BatchConfig.agent_provider``.
"""

from __future__ import annotations

from pathlib import Path

from batch.config import BatchConfig


def run_agent(
    cfg: BatchConfig,
    workspace: Path,
    prompt: str,
    *,
    log_section_title: str = "",
) -> bool:
    """Run an agent using the configured provider.

    Args:
        cfg: Runtime configuration, including ``agent_provider``.
        workspace: The workspace directory for the agent.
        prompt: The prompt text to send to the agent.
        log_section_title: Optional section title for batch logs.

    Returns:
        True if the agent completed successfully, False otherwise.
    """
    if cfg.agent_provider == "iflow":
        from batch.iflow_runner import run_iflow_agent

        return run_iflow_agent(
            cfg, workspace, prompt, log_section_title=log_section_title
        )

    from batch.cursor_runner import run_cursor_agent

    return run_cursor_agent(
        cfg, workspace, prompt, log_section_title=log_section_title
    )
