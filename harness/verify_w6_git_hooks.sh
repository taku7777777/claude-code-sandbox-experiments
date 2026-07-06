#!/usr/bin/env bash
# W6: pre-push hook のバイパス経路を確認する（claude 非依存の git 挙動）。
# SHARE-to-workspace-repo.md の指摘「唯一の抜け穴は --no-verify だけではない」を実証。
# hook は「常にブロック(exit 1)」にし、各 push 方法で ref が push されたか＝hook を回避したかを見る。
set -u
W=/private/tmp/w6work; B=/private/tmp/w6bare
rm -rf "$W" "$B"
git init --bare -q "$B"
git init -q "$W"
cd "$W"
git config user.email x@example.com; git config user.name x
printf '#!/bin/sh\nexit 1\n' > .git/hooks/pre-push; chmod +x .git/hooks/pre-push
echo a > f; git add f; git commit -qm c
git remote add origin "$B"

pushed() { git --git-dir="$B" show-ref --verify --quiet "refs/heads/$1" && echo "PUSHED(hook bypassed)" || echo "blocked(hook ran)"; }

echo "pre-push hook = 常に exit 1（全 push をブロックする想定）:"
git push -q origin HEAD:normal            2>/dev/null; echo "  normal push          -> $(pushed normal)"
git push -q --no-verify origin HEAD:nv    2>/dev/null; echo "  --no-verify          -> $(pushed nv)"
git -c core.hooksPath=/dev/null push -q origin HEAD:hp 2>/dev/null; echo "  -c core.hooksPath=/dev/null -> $(pushed hp)"
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null \
  git push -q origin HEAD:env 2>/dev/null; echo "  env core.hooksPath   -> $(pushed env)"

echo
echo "結論: normal だけが blocked。--no-verify / core.hooksPath(フラグ・環境変数) は全て hook を回避。"
echo "→ pre-push hook は「唯一の抜け穴が --no-verify」ではない。push を人が Terminal で実行する運用で担保する。"
rm -rf "$W" "$B"
