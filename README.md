# agy-delegate

Delegate scoped tasks to your existing Google `agy` CLI from an agent with local terminal access. This project includes a reusable skill and a Python helper; it is not a replacement CLI and does not require MCP. Inspired by [antigravity-for-opencode](https://github.com/chigarow/antigravity-for-opencode).

## Install

Install directly from GitHub:

```sh
npx --yes github:italomlp/agy-delegate
```

The installer asks whether to install globally (the default) or in the current project, then uses the `skills` CLI to select agents. It installs the shared helper to `~/.local/bin`. Node.js 22.20 or newer, Python 3, and the official `agy` CLI are needed; sign in to `agy` interactively before using it. The installer warns if `agy` is unavailable and explains how to put the helper on PATH. Skill files are copied, so they do not depend on the temporary npm cache.

For automation, choose at least one agent and scope explicitly:

```sh
npx --yes github:italomlp/agy-delegate --global --agent codex --agent opencode --yes
npx --yes github:italomlp/agy-delegate --project --agent claude-code --yes
```

The supported agent list and skill locations come from the bundled `skills` CLI. Codex CLI and local Codex desktop use the Codex skill location. OpenCode 1 and 2, Claude Code, Cursor, and other agents are offered where supported by `skills`; actual discovery depends on the host and its version. Start a new session. Automatic delegation is advisory: the host must discover and follow the skill, and host policies take precedence. Cloud-only sessions cannot access a local `agy` installation without a supported connection.

The installer refuses to overwrite a different helper. To upgrade, move the existing helper aside after reviewing it, then rerun the installer; retain your configuration. For uninstall, run `npx --yes github:italomlp/agy-delegate uninstall`. This removes the helper only if it matches that package version, and preserves configuration and skill files. Inspect the installed skill before removing it with `npx skills remove agy-delegate` (add `--global` for global installations). This separate step prevents automatic deletion of modified skills.

A Node-free alternative is to clone this repository and run:

```sh
python3 install.py install --host both
```

Use `--host codex` or `--host opencode` for one host, or copy `skills/agy-delegate` and `agy-delegate.py` manually. The Python installer previews paths and refuses to overwrite different files. Run `python3 install.py uninstall --host both` to remove matching files. `--yes` skips its confirmation; `--prefix` and `--home` override destinations. Run `agy-delegate doctor` to check the helper and `agy` path.

## Usage

Ask your agent to use the `agy-delegate` skill or let it choose the skill for suitable bounded tasks. It picks a complexity and checks results. Direct invocation also works:

```sh
agy-delegate run --preview --complexity simple --read-only 'Review this module; do not edit files.'
agy-delegate run --complexity simple --read-only 'Review this module; do not edit files.'
agy-delegate run --complexity complex --dir . 'Implement the agreed change and report tests.'
agy-delegate run --model 'Gemini 3.8 Flash (Medium)' --timeout 300 'Explain the code.'
agy-delegate auto off    # disable automatic delegation
agy-delegate auto on
agy-delegate status
```

`--preview` outputs the exact prompt, workspace, requested model and potential access without starting agy. The preview includes the prompt and may contain sensitive data; it does not grant permission, enforce isolation, or verify the provider endpoint. `--automatic` respects the persistent toggle; explicit requests can use `--force`. The helper prints JSON with status, model, attempts, output, errors, workspace-change indication and, when found, a conversation ID. Use `--conversation ID` to resume; IDs are best-effort and may not be available. `--timeout` is in seconds. The default is 900 seconds and two quota retries. A retry stops if tracked, staged or non-ignored untracked files change. Outside a Git repository, retries are permitted only for tasks explicitly marked `--read-only`; that option is a promise to the caller, not an enforced sandbox. Ignored files, external files and changes made then reverted cannot be detected. Always inspect partial work before continuing. A native subagent fallback is decided by the calling agent and remains subject to its policies; otherwise it should do the work itself.

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

## Codex troubleshooting

If `agy` reports a read-only file system under `~/.gemini/antigravity-cli` and cannot open a localhost socket, the host sandbox is restricting its state directory and/or network. `environment_restricted` identifies these startup errors; it does not grant permissions or bypass a sandbox. Use the host's supported permission or approval controls to allow only the required access when authorized, or do the task without `agy`. `agy --sandbox` is an additional agy restriction and does not grant access denied by the host.

A host approval rejection may prevent the command from starting at all, so the helper cannot report it. Describe the exact prompt, workspace, files that may be accessed and configured destination (when known) to the host for review; `--preview` can help prepare that description; do not assume `--read-only` prevents data leaving the machine. If review rejects the action, respect that decision and continue locally where possible.

If the result includes `model_unconfirmed`, agy logged that it fell back to a default; the requested model in the output is not proof of the model used. Check `agy models` and configure names your installed version and account accept.
