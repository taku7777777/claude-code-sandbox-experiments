# 04-c e2e: node + Claude Code + iptables/curl。手段3(コンテナ)で claude を無人実行する最小イメージ。
# 公式 .devcontainer を丸ごとビルドするのは重いので、a/b の alpine 単離に「claude 入り」を足す最小構成。
FROM node:22-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends iptables curl ca-certificates dnsutils iproute2 \
 && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code \
 && claude --version

# init-firewall(最小版): DNS + loopback + established + api.anthropic.com を許可し、それ以外の egress を default-deny。
COPY init-firewall.sh /usr/local/bin/init-firewall.sh
RUN chmod +x /usr/local/bin/init-firewall.sh

# 非 root 運用(--dangerously-skip-permissions は root 起動時に拒否される)。node イメージの node(uid 1000)を使う。
USER node
WORKDIR /workspace
