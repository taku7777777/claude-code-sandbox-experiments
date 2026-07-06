# devc-b: egress firewall — iptables default-deny + allowlist(init-firewall.sh の機構)

## 目的

- 公式 example dev container の [`init-firewall.sh`](https://github.com/anthropics/claude-code/blob/main/.devcontainer/init-firewall.sh)
  が使う「**全 egress を default-deny にして許可ドメインだけ通す**」機構が実際に効くことを、最小コンテナで確認する。
- 組み込み sandbox の network(`cases/S6`)がコマンド単位なのに対し、コンテナは**全プロセスの egress を1本で絞る**。

## 前提

- colima で Docker(→ グループ README)。
- iptables を張るには `NET_ADMIN`/`NET_RAW` 権限が要る(公式は `runArgs` で付与)。ここでは
  `docker run --cap-add=NET_ADMIN --cap-add=NET_RAW` で再現。

## 実行内容

1. ファイアウォール適用**前**に example.com へ到達できることを確認(対照)。
2. `iptables -P OUTPUT DROP` + lo/DNS/特定 IP だけ ACCEPT の allowlist を張る。
3. 適用**後**に非許可(example.com)と許可(1.1.1.1)への到達を比較。

## 期待結果

| No | 操作 | 期待 | 結果 |
|---|---|:---:|---|
| 1 | 適用前 example.com | ✅ | HTTP 200(到達) |
| 2 | 適用後 example.com(非許可) | ❌ | HTTP 000(遮断) |
| 3 | 適用後 1.1.1.1(allowlist) | ✅ | HTTP 301(到達) |

## なぜそうなるか

- `iptables -P OUTPUT DROP` で送信を既定拒否にし、必要な宛先(DNS・推論/認証ドメイン等)だけを ACCEPT で
  開ける。コンテナの netns 全体に効くので、**コンテナ内のどのプロセスの egress も allowlist に縛られる**
  (組み込み sandbox の Bash 限定 network より広くかかる)。
- これにより `--dangerously-skip-permissions` の無人セッションでも、到達できる先が allowlist に限定される
  (公式が「bypass はファイアウォールと組み合わせよ」と言う理由)。

## 運用時の留意事項

- 許可ドメインは自分のツールチェーン(npm registry・社内 proxy)+ Claude 推論/認証ドメイン
  ([network-config](https://code.claude.com/docs/ja/network-config))に合わせる。狭すぎると claude が動かない。
- ファイアウォール自体は Claude Code に必須ではない(公式)。egress を別手段で担保するなら外してよい。

## 試し方

```bash
docker run --rm --cap-add=NET_ADMIN --cap-add=NET_RAW alpine sh -c '
  apk add --no-cache iptables curl >/dev/null 2>&1
  curl -s -o /dev/null -w "before: %{http_code}\n" --max-time 8 https://example.com
  iptables -P OUTPUT DROP
  iptables -A OUTPUT -o lo -j ACCEPT
  iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
  iptables -A OUTPUT -d 1.1.1.1 -j ACCEPT
  curl -s -o /dev/null -w "example(非許可): %{http_code}\n" --max-time 6 https://example.com || echo BLOCKED
  curl -s -o /dev/null -w "1.1.1.1(許可): %{http_code}\n" --max-time 6 https://1.1.1.1'
```

## 検証記録

| 日付 | 環境 | 実測 |
|---|---|---|
| 2026-07-06 | colima 0.10.3 / Docker 29.5.2 | 適用前 example.com=200 / 適用後 example.com=000(遮断)/ 1.1.1.1=301(到達) |

## 対応する知識

- [docs/DEVCONTAINER-FINDINGS.md §2.2](../../../docs/DEVCONTAINER-FINDINGS.md)
- 対照(組み込みの network): `cases/S6-sandbox-network`(既定全ブロック・allowedDomains・deniedDomains 優先)
- 公式: [init-firewall.sh](https://github.com/anthropics/claude-code/blob/main/.devcontainer/init-firewall.sh)
