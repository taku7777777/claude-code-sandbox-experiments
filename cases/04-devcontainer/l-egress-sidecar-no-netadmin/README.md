# devc-l: egress 制御をサイドカーへ分離(work コンテナは NET_ADMIN 無し・firewall 書換不可)

## 目的

「ネットワークを制御するコンテナを**サイドカー形式**で立てる」案を裏取りする。egress 制御を**別コンテナ**へ切り出し、
claude が動く **work コンテナは `NET_ADMIN` 無し**でそのサイドカーの network namespace を共有すると:

1. egress は **default-deny + allowlist のまま効く**(work は NET_ADMIN 不要)、
2. **work コンテナからは自分の firewall を書き換えられない**(`CAP_NET_ADMIN` 不在=特権分離)。

これにより **claude コンテナから `NET_ADMIN`/`NET_RAW` を剥がせる**(firewall 自己書き換え=自己昇格の経路が1本消える)。

## 前提

- サイドカーを先に起動: `-u root --cap-add=NET_ADMIN --cap-add=NET_RAW` で `init-firewall.sh` を適用し常駐。
- work コンテナは `--network container:<sidecar>` で netns を共有・**caps 無し**。claude 非経由の機構単離(curl で確認)。
- ⚠️ サイドカーの firewall 適用は **`-u root`** で行う(node ユーザーだと `CAP_NET_ADMIN` を保持せず iptables が
  **無言失敗**する=実測でハマった点。→ 検証記録)。

## 実行内容と期待結果

| No | 操作 | 期待 | 結果 |
|---|---|:---:|---|
| l-1 | work(NET_ADMIN 無し)から `curl https://example.com`(非許可) | 🔒 遮断 | `HTTP=000`(サイドカーの default-deny が共有 netns 全体に効く) |
| l-2 | work(`-u root` だが CAP_NET_ADMIN 無し)から `iptables -F` / `-A OUTPUT ... ACCEPT` | 🔒 拒否 | `Permission denied (you must be root)`(firewall を書き換えられない) |
| l-3 | work から `curl https://api.anthropic.com`(allowlist) | 🔓 到達 | `HTTP=2xx/4xx`(全遮断でなく allowlist・claude 推論経路は生きる) |

## なぜそうなるか

- **l-1(サイドカーの firewall が共有 netns 全体に効く)**: `--network container:X` は X の network namespace を**共有**する。
  X(サイドカー)が `iptables OUTPUT DROP` を張れば、同じ netns の work コンテナの egress も同じルールで濾される。
  04-b/04-c の in-container iptables と同じ「既定全ブロック + allowlist」機構を、**別コンテナから**適用した形。
- **l-2(firewall は書き換え不可)**: iptables の変更には netns 内の `CAP_NET_ADMIN` が要る。work コンテナを caps 無しで
  起動すれば、`-u root` でも保持していないので変更できない(nf_tables が `you must be root` を返すのは uid ではなく
  **cap 不在**の意)。=**自分の egress 遮断を無効化できない**。
- **l-3(allowlist の陽性対照)**: 許可先 `api.anthropic.com` には到達する=サイドカーは全遮断ではなく allowlist。
  claude 本体の推論経路は生き、**ツール経路(Bash curl 等)も同じ netns 境界に掛かる**(04-c と同機構)。

## 運用時の留意事項

- **claude コンテナから `NET_ADMIN` を剥がす**構成にできる。firewall はサイドカー(root 所有・work から書換不可)が持つので、
  work 側でエージェントが firewall を緩める経路が消える(orchestrator 設計の「firewall allowlist は root 所有・
  エージェント書込不可」要件と同方向。Phase 4 の TLS 終端 egress プロキシへ発展できる)。
- サイドカー firewall の適用は **root**(node では cap 不在で無言失敗)。allowlist は自分のツールチェーン
  (npm registry・社内 proxy 等)+ Claude 推論/認証ドメイン([network-config](https://code.claude.com/docs/ja/network-config))に合わせる。
- ⚠️ 素の iptables allowlist は TLS 検査をしないので domain-fronting / DNS トンネルは残る(orchestrator の残余リスク)。
  「物理的に exfiltrate 不可能」は TLS 終端プロキシ + allowlist 限定 DNS まで行って初めて達成。

## 検証記録

| 日付 | 環境 | 実測 |
|---|---|---|
| 2026-07-11 | colima 0.10.3 / Docker 29.5.2 / node:22-bookworm + CC 2.1.201 | l-1=遮断(`HTTP=000`・work は NET_ADMIN 無しでサイドカー netns を共有)/ l-2=拒否(work から iptables 変更不可=CAP_NET_ADMIN 不在)/ l-3=到達(allowlist の api.anthropic.com)。不一致 0。※サイドカー firewall は `-u root` で適用(node では無言失敗) |

## 対応する知識

- in-container egress の原型: [b-egress-firewall](../b-egress-firewall/README.md) / [c-claude-e2e-unattended](../c-claude-e2e-unattended/README.md)
- 認証は読めるが出せない(egress allowlist が最終防壁): [d-credential-exposure](../d-credential-exposure/README.md)
- 組み込み network 境界(Bash 限定): `cases/02-sandbox-bash/S6-sandbox-network`
- [docs/DEVCONTAINER-FINDINGS.md §6](../../../docs/DEVCONTAINER-FINDINGS.md)
