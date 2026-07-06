# devcontainer(手段3)— コンテナが FS(bind mount)と egress(iptables)を境界にする

> 🖥️ **実測環境**: macOS + **colima 0.10.3**(Docker 29.5.2 / VM=Ubuntu 24.04)・2026-07-06。
> a/b は **docker CLI 単体**で機構を単離(claude 非経由)、**c/d/g で claude を実際にコンテナへ入れて無人実行を
> e2e 実測**(最小イメージ node:22-bookworm + Claude Code)。h は env 秘密の境界を claude 非経由の cmd 型で実測(03-j の手段3版)。

## このグループで学ぶこと

- dev コンテナは Claude Code プロセスをコンテナに入れ、**プロジェクトを bind mount / egress を
  default-deny ファイアウォールで絞る**(公式 example dev container の3ファイル構成 → docs)。
- **FS は「マウントした所だけ」= 構造的な許可リスト**(a)。マウントしないホスト秘密はコンテナに存在しない
  (組み込みの denyRead=列挙式 fail-open と対照的に **fail-closed**)。
- **egress は iptables で default-deny + allowlist**(b)。`init-firewall.sh` が使う機構。
- **claude を実際に入れると、ツール経路(Write/Read/Bash)がそのままコンテナ境界に掛かる**(c)。
  手段2(srt)と同じ「プロセス全体を包む」効果を Docker で得る。無人運用は**非 root 必須**(g)、
  コンテナ内の認証は**読めるが egress で出せない**(d の「読める→出せない」実 e2e で裏取り = egress allowlist が最終防壁)。
- **env 秘密は「注入すれば読める(マスクなし)/ 注入しなければ存在しない(fail-closed)」**(h)。
  手段2(srt)は親プロセスの env を継承するため素通りしうる(03-j)のと対比され、手段3固有の境界。

## サブケース一覧

| サブ | 検証 | 機構 | 対応する組み込み | 詳細 |
|---|---|---|---|---|
| a | bind mount の分離 | コンテナ書込→ホスト反映 / 未マウント秘密は不可視 | S3(read)の fail-closed 版 | [a-bind-mount-isolation](./a-bind-mount-isolation/README.md) |
| b | egress firewall | iptables default-deny OUTPUT + allowlist | S6(network) | [b-egress-firewall](./b-egress-firewall/README.md) |
| c | **claude 無人実行 e2e** | Write=ホスト反映 / 未マウント=不可視 / Bash egress=遮断 | 03-a/b(手段2)/ S6 | [c-claude-e2e-unattended](./c-claude-e2e-unattended/README.md) |
| d | 認証流出面 | claude の Read で認証は**読める** → だが Bash curl は egress で**遮断**(「読める→出せない」の実 e2e) | S7(credentials) | [d-credential-exposure](./d-credential-exposure/README.md) |
| g | root bypass | `-u root` の `--dangerously-skip-permissions` は拒否(非 root 必須) | P1-e | [g-root-bypass-in-container](./g-root-bypass-in-container/README.md) |
| h | env 秘密の境界 | 注入した env は読める(マスクなし) / 注入しなければ存在しない(fail-closed) | S7-k / **03-j(手段2版)** | [h-env-secret-boundary](./h-env-secret-boundary/README.md) |

## 前提: colima で Docker を用意する

```bash
brew install colima docker
colima start --cpu 2 --memory 4
docker info                        # Server Version が出れば OK
```

- ⚠️ **共有マウント範囲**: colima は既定 `/Users/<you>` 配下だけを VM に共有(virtiofs)。`-v` の bind mount 対象は
  `$HOME` 配下に置く(`/private/tmp` 等は VM 内にこもりホストに反映されない=実測でハマった)。

## 要点

- **手段2(srt)と手段3(コンテナ)は「プロセス全体を包む」点で同じ効果**(ツール経路まで境界内)。差は
  Docker 要否・**環境の再現性**・egress の実装(srt=proxy / コンテナ=iptables)。
- **dev コンテナ固有の価値は「制限」より環境の提供・再現性**(ベースイメージ・ツールチェーン・バージョン固定)。
  純粋な分離だけなら手段2 が Docker なしで同等の OS 境界を出せる。
- ⚠️ `--dangerously-skip-permissions` × コンテナでも、**コンテナ内で読める `~/.claude` 認証情報は悪意ある
  プロジェクトが読み出せる**(d/d1 で裏取り)。**だが egress allowlist があれば非許可ドメインへは出せない**
  (d/d2 で claude の Bash curl が iptables default-deny に遮断=「読める→出せない」の実 e2e)。
  信頼できるリポジトリ限定 + 監視 + ホスト秘密は非マウント + **egress allowlist(唯一の出口規制)**。
- **無人運用は非 root 必須**(g)。root では `--dangerously-skip-permissions` が拒否される。
- **env 秘密は注入すれば読める(マスクなし)/ 注入しなければ fail-closed**(h)。手段2(srt)は親 env 継承で素通りしうる(03-j)のと対比。

## 試し方 — コンテナ内 claude を3形態から選べる

コンテナ境界(bind mount / 未マウント不可視 / iptables egress)は **srt と同じくプロセス全体**に掛かるので、
コンテナ内で claude をどの形態で起動しても同じ境界が効く(モダリティ非依存 →
[EXECUTION-MODALITIES](../../docs/EXECUTION-MODALITIES.md)「環境ケースも同じ2軸」)。読者は目的で選べる:

```bash
colima start                                    # 初回のみ
docker build -t cc-devc-e2e harness/devcontainer   # 初回のみ(node:22-bookworm + Claude Code)
```

**① ヘッドレス(記録に残す正)** — c/d/g/h を1回で e2e 実測:
```bash
bash harness/devcontainer/run_devc_e2e.sh       # 認証は自動 bootstrap・実行後撤去 → 各 results/measured.json
```
中身はコンテナ内 `claude --dangerously-skip-permissions -p …`。認証(`ANTHROPIC_API_KEY` か
Keychain `Claude Code-credentials`)が無ければ自動 skip し「未実測(認証前提)」を記録。

**② 対話(コンテナ内 TUI)** — 手で境界を体感する:
```bash
docker run -it --rm -u node -e HOME=/home/node \
  -e CLAUDE_CONFIG_DIR=/cfg -v "$HOME/.cc-devc-e2e/cfg-tpl:/cfg" \
  -v "$PWD:/workspace" -w /workspace cc-devc-e2e claude   # 認証 dir は runner が用意する形と同じ
```
コンテナ内で Read `/host-only.txt`(未マウント)が「存在しない」・Bash curl が firewall で落ちるのを対話で確認。
srt×TUI と違いコンテナ内 TUI は端末プロトコルの干渉が無いので普通に対話できる。

**③ SDK(コンテナ内 node)** — プログラムから:
コンテナ内に Agent SDK を入れて(`npm i @anthropic-ai/claude-agent-sdk`)`harness/sdk/exec_case.mjs`
相当を走らせれば、同じ境界が SDK 経路にも掛かる。境界は形態非依存なので実測は headless の e2e で代表させ、
SDK/対話は導線のみ提示(03 の a/b/h で headless=SDK 一致を実測済み = 同じ論理がコンテナにも当てはまる)。

- a/b(機構の単離)は各ケース README のコマンド参照(docker CLI 単体・claude 非経由)。
- **backlog**: e-readonly-mount(`-v …:ro` の EROFS)/ f-managed-settings-baked(`/etc/claude-code/managed-settings.json`)は
  今回スコープ外。

## 対応する知識

- [docs/DEVCONTAINER-FINDINGS.md](../../docs/DEVCONTAINER-FINDINGS.md) — runbook・手段1/2/3 比較表
- [docs/SANDBOX-ENVIRONMENTS.md](../../docs/SANDBOX-ENVIRONMENTS.md) — 手段3 の位置づけ
- 公式 example: [anthropics/claude-code/.devcontainer](https://github.com/anthropics/claude-code/tree/main/.devcontainer)
