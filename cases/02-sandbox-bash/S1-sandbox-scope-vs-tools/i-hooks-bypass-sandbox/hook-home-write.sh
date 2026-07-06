#!/bin/bash
# PreToolUse hook (matcher: Bash) for S1-i.
# Writes to a cwd-external path ($HOME) to prove that hooks execute on the host,
# OUTSIDE the Bash sandbox. If hooks ran INSIDE the sandbox this write would EPERM
# (a Bash tool call to the same $HOME path is blocked — see probe 2 control).
# Non-blocking (exit 0, no JSON) so the triggering Bash tool still runs normally.
printf 'S1I_HOOK_RAN_OUTSIDE_SANDBOX %s\n' "$(date -u +%FT%TZ)" > "$HOME/s1i-hook-proof.txt"
exit 0
