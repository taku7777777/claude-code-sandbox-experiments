# P11. mcp-tool-rules — `mcp__server__tool` 系規則のマッチングと現れ方(MCP を permission 層で締める唯一の手段の実効確認)

## この章で学ぶこと

- **MCP ツールは sandbox(OS 層)を丸ごと迂回する**(S1-h)ため、MCP を絞る設定は permission 層の
  `mcp__…` 規則しかない。本群はその規則が**どの形で効き、どの形が無言で無効か**を確定する。
- 規則の形は 3 段: **`mcp__server`(サーバ形=全ツール)/ `mcp__server__tool`(ツール形=1ツール)/
  glob(`mcp__server__*` は有効・bare `mcp__*` は allow では無効, deny/ask では有効)**。
- 評価順(deny→ask→allow)・「彫れる向きは広 allow + 狭 deny だけ」(P2-e)・deny の除去型(P2-c/d)は
  **MCP ツールでも組込ツールと同じに成立**する。
- → ロール設計への直結形: **「参照系 MCP = サーバ allow + 書込系ツール deny(h)」**と
  **「特定ツールだけ人間確認 = ask 規則(j)」**が機構として成立する。

## サブケース一覧

| サブ | 設定 | 論点 | 詳細 |
|---|---|---|---|
| a | 規則なし | baseline: MCP ツールは既定 ask | [a-baseline-ask](./a-baseline-ask/README.md) |
| b | `allow: [mcp__probe__read_path]` | ツール形 allow は 1 ツール限定(兄弟は ask のまま) | [b-allow-tool](./b-allow-tool/README.md) |
| c | `allow: [mcp__probe]` | サーバ形 allow は全ツールに波及 | [c-allow-server](./c-allow-server/README.md) |
| d | `allow: [mcp__probe__*]` | サーバ後 glob は有効(c と等価) | [d-allow-tool-glob](./d-allow-tool-glob/README.md) |
| e | `allow: [mcp__*]` | bare glob は allow では**無言で無効**(ask のまま) | [e-allow-bare-glob-noop](./e-allow-bare-glob-noop/README.md) |
| f | `deny: [mcp__probe__read_path]` | ツール deny は**除去型**・兄弟に波及しない | [f-deny-tool](./f-deny-tool/README.md) |
| g | `deny: [mcp__probe]` + `allow: [mcp__probe__read_path]` | サーバ deny の内側にツール allow で穴は開かない | [g-deny-server-beats-allow-tool](./g-deny-server-beats-allow-tool/README.md) |
| h | `allow: [mcp__probe]` + `deny: [mcp__probe__read_path]` | **広 allow + 狭 deny は成立**(最小権限の正解形) | [h-allow-server-deny-tool](./h-allow-server-deny-tool/README.md) |
| i | `deny: [mcp__*]` | deny 側 bare glob は有効=全 MCP 除去(キルスイッチ) | [i-deny-all-mcp](./i-deny-all-mcp/README.md) |
| j | `allow: [mcp__probe]` + `ask: [mcp__probe__net_get]` | ask はサーバ allow に勝つ(確認ゲート成立・ツール残存) | [j-ask-beats-allow](./j-ask-beats-allow/README.md) |

fixture: [mcp-probe-server.mjs](./mcp-probe-server.mjs)(S1-h と同一の最小 stdio MCP サーバ。
`read_path`=ファイル読取 / `net_get`=HTTP GET の 2 ツール。`arrange.mcpServers` でハーネスが刺す)。

## 対比 — 規則の形 × 対象ツール(全セル実測 headless+SDK)

セル = `許諾 結果`(approve 前提。`read` = mcp__probe__read_path / `net` = mcp__probe__net_get):

| No | 設定 | read | net | 何が確定するか |
|---|---|:---:|:---:|---|
| a | 規則なし | ask ✅ | （ask ✅）† | MCP は既定 ask(無条件承認集合に入らない) |
| b | allow ツール形(read) | allow ✅ | ask ✅ | allow はツール名完全一致・兄弟に波及しない |
| c | allow サーバ形 | allow ✅ | allow ✅ | サーバ形は全ツール事前承認 |
| d | allow `mcp__probe__*` | allow ✅ | allow ✅ | サーバ後 glob は有効(docs CONFIRMED) |
| e | allow `mcp__*` | ask ✅ | — | **bare glob は allow で無効**(無言・fail-closed 側) |
| f | deny ツール形(read) | deny - | ask ✅ | deny は**除去型**(init tools 欠落・denials 空)・1 ツール単位 |
| g | deny サーバ + allow ツール(read) | deny - | deny - | 広 deny に狭 allow で穴は開かない(P2-e 同型) |
| h | allow サーバ + deny ツール(read) | deny - | allow ✅ | **広 allow + 狭 deny は成立**(P4-a 同型) |
| i | deny `mcp__*` | deny - | （deny -）‡ | deny 側 bare glob は全 MCP 除去 |
| j | allow サーバ + ask ツール(net) | allow ✅ | ask ✅ | ask は allow に勝つ(P6-b 同型)・ツールは残存 |

† a-net は未実測(a-read と同機構の推定。b の net=ask が実測の傍証)。
‡ i-net は未実測(initMcpTools=[] の実測が全除去を直接示すため read 1 プローブで足りる)。

## e と i の非対称(運用上の要点)

| 形 | allow 側 | deny/ask 側 |
|---|---|---|
| `mcp__server__*`(サーバ後 glob) | ✅ 有効(d) | ✅ 有効(docs) |
| bare `mcp__*`(サーバ名なし) | ❌ **無言で無効**(e) | ✅ 有効(i) |

- docs はこの非対称を明記する(allow の glob はリテラルな `mcp__<server>__` 接頭辞の後ろのみ/
  unanchored な allow glob は「警告付きでスキップ」)。**実測では headless 実行の stderr に警告は
  観測されなかった**(e)——P2-g(規則形式ミスの起動時警告は見落とされがち)と同型の運用リスク。
  幸い倒れる先は fail-closed(全 ask)で、P3 の Write glob 地雷(fail-open)より安全側。
- **締める側だけ全域 glob が効く**設計は運用に都合がよい: 上位/組織スコープの `deny: ["mcp__*"]` は
  1 行で「MCP 全面禁止」になり、deny はスコープ横断で常勝(P7-a)なので project 側から外せない。

## deny の現れ方と監査

- MCP ツールの deny は **除去型**(f/g/i: init tools から消え、`permission_denials[]` にも出ない)。
  組込ツールの「deny のみ=除去型」(P2-c/d)と同じ現れ方で、**ground truth は init メッセージの
  tools 一覧の欠落**(ハーネスの除去型判定がそのまま効く)。
- 含意: 「MCP の書込ツールを deny で塞いだ」ことの監査ログは Claude Code 側には残らない
  (呼び出し自体が起きない)。試行の監査が要るなら deny でなく ask(j)に寄せるか、サービス側ログで見る。

## ロール設計への写像(この群が裏づける型)

```jsonc
// researcher の「参照系 MCP だけ許可」(h の形)
{ "permissions": {
    "allow": ["mcp__slack"],                       // サーバ形で開け
    "deny":  ["mcp__slack__post_message",          // 書込系ツールを除去(除去型・全モード生存)
              "mcp__slack__update_message"] } }

// comms の「外部書込は毎回確認」(j の形)
{ "permissions": {
    "allow": ["mcp__slack"],
    "ask":   ["mcp__slack__post_message"] } }      // 対話=承認プロンプト / headless=auto-deny

// 組織の「MCP 全面禁止」(i の形。managed/user スコープに)
{ "permissions": { "deny": ["mcp__*"] } }
```

- ツール名はサーバ実装依存なので、**導入時に必ず init tools 一覧で実ツール名を確認して deny を書き、
  空撃ちで除去を確認する**(本群のハーネスがそのまま手順になる)。
- 規則で塞いでも **MCP サーバ自体はホスト直実行**(S1-h)。サーバ選定・トークンのサービス側スコープが
  先で、`mcp__` 規則はその上の層にある。

## 要点

- **MCP 規則は「組込ツールと同じ評価系」に乗る**: 既定 ask(a)/ allow の粒度はツール名一致(b/c/d)/
  deny は除去型で常勝(f/g)/ 彫れる向きは広 allow + 狭 deny だけ(g⇔h)/ ask は allow に勝つ(j)。
  P2/P4/P6 で確定した規則系の一般則が MCP 次元でもそのまま成立する。
- **唯一の MCP 固有仕様は glob の非対称**(e⇔i): allow はサーバ名リテラル必須・deny/ask は全域 glob 可。
- MCP を絞る全体像は **サーバ選定(刺すか)→ サービス側トークンスコープ → `mcp__` 規則(本群)** の
  3 段。permission 規則は 3 段目であって 1 段目の代わりにならない(S1-h)。

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索(全 11 形)→ headless / sdk(10 サブケース) |

- 一次 docs 突合(2026-07-06, permissions.md / tools-reference.md): サーバ形・ツール形・`mcp__server__*`・
  deny/ask の `mcp__*`・allow 側 unanchored glob のスキップは **CONFIRMED**。除去型 vs 呼出時 block の
  MCP での現れ方は docs が「bare tool name=除去 / scoped=呼出時 block」と述べる一般則からの推論のみで、
  **ツール形 deny が除去型になる実測は本群が一次証拠**(docs の「bare tool name」に `mcp__server__tool` の
  full name が含まれると読める)。

## 対応する知識

- docs/FINDINGS.md 追補(MCP 規則)/ docs/COVERAGE.md
- 関連: S1-h(MCP は sandbox 迂回=本群が必要な理由)/ P2(allow/deny の評価系)/ P4-a(広 allow+狭 deny)/
  P6(ask 規則)/ P7-a(deny のスコープ横断常勝)/ P10(WebFetch/WebSearch=同じ「permission 層でしか
  締められない外向きツール」の並び)
