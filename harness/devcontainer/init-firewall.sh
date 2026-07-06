#!/bin/bash
# init-firewall.sh(最小版) — 公式 anthropics/claude-code の init-firewall.sh の要点だけを抜き出したもの。
# egress を default-deny にし、DNS / loopback / established と Claude 推論ドメイン(api.anthropic.com)だけを許可する。
# これで「claude 本体は API に到達できる=無人実行できる」が「Bash curl での非許可ドメイン(example.com)は遮断」を両立させる。
# 要 root(CAP_NET_ADMIN)。コンテナ起動時に root で実行してから非 root の claude を起動する。
set -euo pipefail

# 許可する Claude 系ホスト(推論・認証・アップデート)。IP は起動時に解決して allowlist する。
ALLOW_HOSTS="${ALLOW_HOSTS:-api.anthropic.com statsig.anthropic.com sentry.io}"

iptables -F OUTPUT || true
iptables -P OUTPUT DROP
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
# DNS(名前解決)を許可(egress 検証は「解決できるが接続できない」= egress 遮断を見たいため DNS は開ける)
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

for h in $ALLOW_HOSTS; do
  for ip in $(getent ahostsv4 "$h" 2>/dev/null | awk '{print $1}' | sort -u); do
    iptables -A OUTPUT -d "$ip" -p tcp --dport 443 -j ACCEPT
  done
done

echo "init-firewall: OUTPUT default-deny 適用。許可ホスト: $ALLOW_HOSTS"
