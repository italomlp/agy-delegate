# agy-delegate

Delegate scoped tasks to your existing Google `agy` CLI from an agent with local terminal access. This project includes a reusable skill and a Python helper; it is not a replacement CLI and does not require MCP. Inspired by [antigravity-for-opencode](https://github.com/chigarow/antigravity-for-opencode).

## Install

Install Python 3, Git and the official `agy` CLI, then sign in interactively with `agy`. Clone this repository and run:

```sh
git clone https://github.com/italomlp/agy-delegate.git
cd agy-delegate
python3 install.py install --host both
agy-delegate doctor
```

Choose `--host codex` or `--host opencode` to install for one host. The installer previews paths and asks before writing, refuses to overwrite different files, and copies the helper to `~/.local/bin`; add that directory to PATH if needed. It installs the skill in `~/.agents/skills/agy-delegate` for Codex and `~/.config/opencode/skills/agy-delegate` for OpenCode. Start a new agent session to load skills. The Codex CLI and local Codex desktop share the skill convention; OpenCode discovery may differ by release, particularly OpenCode 2: verify with the host's skill list. Compatibility has not yet been verified with live host sessions. The helper needs access to the same local filesystem and `agy`; cloud-only sessions do not inherit a local installation.

For another agent, copy `skills/agy-delegate` into its skill directory and `agy-delegate.py` to a PATH directory named `agy-delegate`. If the host does not discover skills, add equivalent instructions to its own instruction file. A host may require an explicit skill invocation or user permission; automatic use cannot override its policies or be guaranteed by this package.

To remove unchanged installed files, run `python3 install.py uninstall --host both`. Modified files and configuration are preserved. `--yes` skips the confirmation; `--prefix` and `--home` change installation destinations.

## Usage

Ask your agent to use the `agy-delegate` skill or let it choose the skill for suitable bounded tasks. It picks a complexity and checks results. Direct invocation also works:

```sh
agy-delegate run --complexity simple --read-only 'Review this module; do not edit files.'
agy-delegate run --complexity complex --dir . 'Implement the agreed change and report tests.'
agy-delegate run --model 'Gemini 3.8 Flash (Medium)' --timeout 300 'Explain the code.'
agy-delegate auto off    # disable automatic delegation
agy-delegate auto on
agy-delegate status
```

`--automatic` respects the persistent toggle; explicit requests can use `--force`. The helper prints JSON with status, model, attempts, output, errors, workspace-change indication and, when found, a conversation ID. Use `--conversation ID` to resume; IDs are best-effort and may not be available. `--timeout` is in seconds. The default is 900 seconds and two quota retries. A retry stops if tracked, staged or non-ignored untracked files change. Outside a Git repository, retries are permitted only for tasks explicitly marked `--read-only`; that option is a promise to the caller, not an enforced sandbox. Ignored files, external files and changes made then reverted cannot be detected. Always inspect partial work before continuing. A native subagent fallback is decided by the calling agent and remains subject to its policies; otherwise it should do the work itself.

Settings are JSON at `~/.config/agy-delegate/config.json` (or `$XDG_CONFIG_HOME/agy-delegate/config.json`). `AGY_DELEGATE_CONFIG` overrides the path and `AGY_BIN` points to a specific executable. For example:

```json
{
  "auto": true,
  "max_retries": 2,
  "models": {
    "simple": ["Gemini 3.8 Flash (Medium)", "Claude Sonnet 5.5 (Medium)"],
    "medium": ["Claude Sonnet 5.5 (Medium)", "Gemini 3.8 Flash (Medium)"],
    "complex": ["Claude Opus 5.5 (High)", "Claude Sonnet 5.5 (Medium)"]
  }
}
```

Model names are examples from the reference project, not a guarantee of access. Check `agy models` and update your list for your account and CLI version. Set `--max-retries 0` to disable retries. Only recognized quota errors trigger model fallback; auth, permission and other errors stop. Explicit `--model` selects the first attempt; configured alternatives remain eligible for quota fallback.

## Permissions and limitations

The helper never passes `--dangerously-skip-permissions`. `--sandbox` opts into agy's terminal restrictions; it is not a complete filesystem sandbox. Headless tasks may require approvals that cannot be answered without a TTY, causing errors or a timeout; configure permissions through agy and the host according to your own policy. Do not send secrets unnecessarily. The child inherits the environment and output can contain sensitive data; review it before sharing. Running agy may use account quota. Verify service terms and account eligibility yourself.

The caller must inspect edits and verify outcomes. No ACP or MCP integration is included. A future MCP adapter could invoke the JSON interface, without changing the skill's core behavior. See `python3 -m unittest discover -s tests -v` for offline tests.
