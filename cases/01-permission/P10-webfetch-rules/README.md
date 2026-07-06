# P10. webfetch-rules — `WebFetch(domain:…)` は permission 層の domain allowlist / WebSearch は bare 二値（S6 の「ネットワークを止める2層目」の後段）

## この章で学ぶこと

- **WebFetch は sandbox network（OS 層 egress）を迂回する**（S6-h の発見）。だが **permission 層の `WebFetch(domain:…)` 規則には従う** — ここがネットワークを絞る**もう一つの層**。
- 規則は **domain ごとの allow/deny/ask**。`WebFetch(domain:example.com)` は example.com **完全一致**のみを対象にし、別ドメインは既定 ask に落ちる（**allowlist**）。
- deny は当該ドメイン取得を permission 層でハードにブロック。**ワイルドカード `domain:*.example.com`** はサブドメインにマッチ（sandbox network の `allowedDomains` ワイルドカード=S6-c2 と同型）。
- **WebSearch は specifier を取らない**（bare `WebSearch` が唯一の形＝docs 明記）: 既定 ask（e）/ allow は全か無か（f・ドメイン限定不可）/ deny は除去型（g）。**「限定的な web search」を規則で書く手段は無い**。
- → **ネットワークを本当に絞るには sandbox network 層（Bash・サブプロセス＝S6）＋ 取得系ツールの permission 層（本群: WebFetch domain 規則 + WebSearch 二値）の2層**。片方だけでは WebFetch/WebSearch（S6 を迂回）または Bash egress（本群の対象外）が残る。

## サブケース一覧

| サブ | 設定 / 取得先 | 論点 | 詳細 |
|---|---|---|---|
| a | `deny WebFetch(domain:example.com)` / example.com | deny は当該ドメイン取得を permission 層でブロック | [a-deny-domain](./a-deny-domain/README.md) |
| b | `allow WebFetch(domain:example.com)` / **example.org** | 列挙外ドメインは不一致 → ask（allowlist の特異性） | [b-nomatch-asks](./b-nomatch-asks/README.md) |
| c | `allow WebFetch(domain:example.com)` / example.com | 当該ドメインは事前承認 → allow（陽性対照） | [c-allow-match](./c-allow-match/README.md) |
| d | `allow WebFetch(domain:*.example.com)` / **www**.example.com | ワイルドカードはサブドメインにマッチ → allow | [d-wildcard-domain](./d-wildcard-domain/README.md) |
| e | 規則なし / WebSearch | WebSearch は既定 ask（read-only 無条件集合に入らない） | [e-websearch-default](./e-websearch-default/README.md) |
| f | `allow WebSearch` / WebSearch | bare allow で事前承認（domain 限定は書けない＝全か無か） | [f-websearch-allow](./f-websearch-allow/README.md) |
| g | `deny WebSearch` / WebSearch | bare deny は除去型（init tools から消える） | [g-websearch-deny](./g-websearch-deny/README.md) |

## 対比 — 設定 × 取得先（全セル実測 headless+SDK）

セル = `許諾 結果`（approve 前提）。probe=`permission`（a/b は denials・canUseTool で判定 / c/d は WebFetch 成功時に Write するマーカーの有無で ALLOWED を確定）:

| No | 設定 | 取得先 | 許諾 | 結果 | 補足 |
|---|---|---|:---:|:---:|---|
| a | deny `WebFetch(domain:example.com)` | example.com | deny | - | permission 層でブロック（SDK=DENIED_HARD） |
| b | allow `WebFetch(domain:example.com)` | example.org | **ask** | ✅ | 列挙外は不一致 → 既定 ask（SDK canUseTool 発火） |
| c | allow `WebFetch(domain:example.com)` | example.com | allow | ✅ | 完全一致は事前承認 |
| d | allow `WebFetch(domain:*.example.com)` | www.example.com | allow | ✅ | ワイルドカードがサブドメインに一致 |
| e | （規則なし） | WebSearch | **ask** | ✅ | 既定 ask（denials=[WebSearch]・ツールは残存） |
| f | allow `WebSearch` | WebSearch | allow | ✅ | bare が唯一の形（specifier 不可＝docs 明記） |
| g | deny `WebSearch` | WebSearch | deny | - | **除去型**（init tools から消え denials 空） |

- **a と c** で deny/allow が同一ドメインに対して反転。**b** が「allowlist は列挙ドメインだけ」を示す（example.com を allow しても example.org は ask）。**d** がワイルドカードの効きを示す。
- SDK で ask/deny を分離（a=DENIED_HARD / b=ASK。headless では両方 DENIED に見える）。

## S6 との関係（ネットワークを止める2層）

| 層 | 対象 | 止め方 | 迂回されるもの | 群 |
|---|---|---|---|---|
| sandbox network（OS 層） | Bash・サブプロセスの egress | `sandbox.network.allowedDomains/deniedDomains` | **WebFetch ツール**（S6-h で迂回を実測） | S6 |
| WebFetch permission（本群） | WebFetch ツールの取得 | `permissions` の `WebFetch(domain:…)` allow/deny/ask | **Bash egress**（本群は WebFetch のみ） | P10 |

- **2層は互いに相手の経路をカバーしない**。sandbox `allowedDomains:[]` だけでは WebFetch が到達し（S6-h）、`WebFetch(domain:…)` deny だけでは Bash curl が残る。両方書いて初めてネットワークが締まる。

## 要点

- **`WebFetch(domain:…)` は domain allowlist**。allow は完全一致ドメインのみ事前承認（b: example.com allow でも example.org は ask）。deny は当該ドメイン取得をハードブロック（a）。ワイルドカード `*.example.com` はサブドメインに効く（d）。
- **WebSearch は bare 二値**（e/f/g）: 既定 ask・allow は全域・deny は除去型。domain 限定を書けるのは WebFetch 側だけなので、「取得先を絞った web 参照」は **WebFetch(domain allowlist) + deny WebSearch** の組みで書くのが唯一の規則形。
- **WebFetch/WebSearch は S6（sandbox network）を迂回するが本群（permission）には従う** — 層が違う。ネットワーク遮断は S6 + P10 の2層で設計する。
- 判定の注意: WebFetch/WebSearch はディスク副作用を持たないため、陽性対照（c/d/f）は「取得成功時にだけ Write するマーカー」で ALLOWED を観測する（deny/ask ならマーカーも出ない）。到達性は S6-h の preflight で確認済み（オフライン時は c/d/f が誤 DENIED になり得る）。
- **未カバー（documented-only）**: apex ドメインが `*.example.com` にマッチするか（一般に glob はラベルを要求）は未検証（d はサブドメイン一致のみ確定）。

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | headless / sdk（4 サブケース一致。a=DENIED/DENIED_HARD / b=DENIED/ASK / c・d=ALLOWED） |
| 2026-07-06 | v2.1.201 | macOS(darwin) | e/f/g（WebSearch）を追加実測: headless / sdk（e=DENIED/ASK・f=ALLOWED・g=除去型 DENIED/DENIED_HARD）。一次 docs 突合: WebSearch は specifier 不可・bare のみ（tools-reference, CONFIRMED） |

- 一次 docs: permissions の `WebFetch(domain:…)` 規則形式（domain マッチ、gitignore 準拠のパス規則とは別体系）。WebFetch が sandbox network を迂回する点は **SILENT**（S6-h の実測が一次証拠）。

## 対応する知識

- docs/FINDINGS.md: WebFetch permission 規則（domain allowlist）/ ネットワーク2層モデル
- 関連: S6（sandbox network=OS 層 egress・本群と対の層）/ S6-h（WebFetch は sandbox network を迂回＝本群が必要な理由）/ P4-c（`sh -c` で文字列 deny はすり抜け＝permission 層の限界）
