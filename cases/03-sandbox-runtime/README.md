# sandbox-runtime(手段2)— srt はプロセス全体を包み、ツール経路まで OS 層で塞ぐ

> 🖥️ **実測環境**: macOS(Seatbelt)・Claude Code v2.1.201・`@anthropic-ai/sandbox-runtime` **v0.0.63**
> (ベータ研究プレビュー・設定形式は変わりうる)・2026-07-06。Linux(bubblewrap)は再実測要。

## このグループで学ぶこと

- srt は組み込み Bash sandbox(`cases/S*`)と**同じ Seatbelt を使うが、Bash だけでなく Claude Code
  プロセス全体**(組込ツール・MCP・hooks 含む)を包む(一次 docs)。
- そのため**組み込みでは迂回されるツール経路(Read/Write/Edit ツール)を OS 層で塞ぐ**(a, b, e)。
  組み込み側の対応ケース S3-d / S1-f では同じ操作が迂回して成功していた。
- **別プロセス経路(MCP サーバ・hook)も srt 境界内に入る**(f, g)。claude が spawn する子プロセスも
  Seatbelt 内なので、組み込みでは丸ごと迂回した MCP の read/net(S1-h)・hook の cwd 外書込(S1-i)も塞がる。
- **WebFetch も srt の network 境界に掛かる**(h)。組み込みでは egress を迂回した(S6-h)が、srt では
  WebFetch のローカル socket が localhost proxy に掛かり、非許可ドメインは `Socket is closed` で遮断。
- 一方 **permission 層の判定(deny 勝ち・正当書込は通す)は srt でも不変**(c)。
  srt が足すのは OS 境界であって、許諾エンジンは変えない。
- **ただし srt の境界は FS/network のみ。環境変数の秘密は対象外**(j)= env に置いた秘密は srt では守れない。
- network も既定全ブロック + allowlist で、Bash 経路を OS 層で遮断(d、組み込み S6 と同型)。

## サブケース一覧

| サブ | 環境で変える1変数 | 論点 | 対応する組み込みケース | 詳細 |
|---|---|---|---|---|
| a | Read ツールで denyRead 先を読む | srt はツール経路の read を塞ぐか | S3-d(組み込みは迂回=漏洩) | [a-read-tool-caught](./a-read-tool-caught/README.md) |
| b | Write ツールで denyWrite 先に書く | srt はツール経路の write を塞ぐか | S1-f(組み込みは迂回=書ける) | [b-write-tool-caught](./b-write-tool-caught/README.md) |
| c | `deny Write(*)` / 正当な cwd 書込 | srt は permission 層を変えないか(対照) | P2-b / P2-a | [c-permission-layer-invariant](./c-permission-layer-invariant/README.md) |
| d | Bash curl を許可/非許可ドメインへ | srt の network 境界(Bash 経路) | S6-a/b | [d-network-egress-boundary](./d-network-egress-boundary/README.md) |
| e | Edit ツールで denyWrite 先の既存ファイルを書換 | srt はツール経路の Edit を塞ぐか(Read/Write に続く3経路目) | S1-f 系 / S9(`Edit(dir/**)` deny の正解形) | [e-edit-tool-caught](./e-edit-tool-caught/README.md) |
| f | MCP サーバ(claude の子プロセス)の read / net | srt は別プロセス経路(MCP)も境界内に入れるか | S1-h(組み込みは丸ごと迂回) | [f-mcp-vs-boundary](./f-mcp-vs-boundary/README.md) |
| g | PreToolUse hook(claude が spawn する副プロセス)の cwd 外書込 | srt は別プロセス経路(hook)も境界内に入れるか | S1-i(組み込みはホスト実行で迂回) | [g-hook-vs-boundary](./g-hook-vs-boundary/README.md) |
| h | WebFetch で非許可ドメインを取得 | srt の network 境界は WebFetch にも掛かるか | S6-h(組み込みは egress を迂回) | [h-webfetch-vs-network](./h-webfetch-vs-network/README.md) |
| j | env 番兵を srt 配下で echo | srt の境界は env 秘密を隠すか(境界条件・倒せない面) | S7-d〜g(組み込みの envVars deny/マスク) | [j-credentials-env-out-of-scope](./j-credentials-env-out-of-scope/README.md) |

## 対比(環境 × 操作・実測 2026-07-06)

セル = その環境での結果。`builtin~` = srt 無し(sandbox 無効 + permission のみ)で組み込みのツール迂回を近似。

| 操作 | builtin~ | srt | 差分の意味 |
|---|:---:|:---:|---|
| Read ツール → denyRead 先(a) | ✅ 漏洩 | **❌ EPERM** | srt がツール経路の read を OS 層で塞ぐ |
| Write ツール → denyWrite 先(b) | ✅ 書ける | **❌ EPERM** | srt がツール経路の write を塞ぐ |
| Edit ツール → denyWrite 先の既存書換(e) | ✅ 書換 | **❌ EPERM** | srt がツール経路の edit を塞ぐ(3経路目) |
| MCP `read_path` → denyRead 先(f) | ✅ 漏洩 | **❌ EPERM** | MCP 子プロセスも srt 境界内(S1-h の反転) |
| MCP `net_get` → 非許可ドメイン(f) | ✅ 到達 | **❌ 遮断** | MCP の外向き通信も srt egress 内(`ENOTFOUND`)。許可側でも遮断 = 生 node が proxy 非対応で直結 DNS block(allowlist 前・下記) |
| hook が cwd 外 `$HOME` に書く(g) | ✅ 書ける | **❌ 遮断** | hook 副プロセスも srt 境界内(S1-i の反転)。実 EPERM は副プロセスゆえ取れず消去法帰属(発火証跡は出る+proof 出ない+denials 空+builtin~ では書けた) |
| WebFetch → 非許可ドメイン(h) | ✅ 到達 | **❌ 遮断** | WebFetch の socket も srt egress 内(`Socket is closed`・S6-h の反転)。許可側=到達で allowlist 帰属を両側確定 |
| env 番兵を echo(j) | ✅ 素通り | ✅ 素通り | **srt は env をマスクしない**(境界は FS/network のみ・倒せない面) |
| 正当な cwd 書込(c) | ✅ | ✅ | srt は正当操作を壊さない(陽性対照) |
| `deny Write(*)`(c) | ❌ deny | ❌ deny | permission 層は srt 非依存(陰性対照) |
| Bash curl 許可ドメイン(d) | ✅ | ✅ | allowedDomains は通す |
| Bash curl 非許可ドメイン(d) | (組み込みは要 sandbox) | **❌ 遮断** | 既定全ブロック |

**a/b/e が反転**(組込ツール read/write/edit)+ **f/g が反転**(MCP・hook の別プロセス)+ **h が反転**(WebFetch)
= srt にしかできない防御。組込ツールも別プロセスも WebFetch も OS 層で塞がる。しかも srt 側は
`permission_denials` が空のまま失敗 = OS 層が止めた証拠(permission の ask/deny ではない)。
**ただし env(j)は両環境で素通り** = srt の境界は FS/network に限定される(倒せない面)。

**⚠️ srt の egress は2機構**(d/h/f の allowlist 許可側対照で判明): (1) `HTTPS_PROXY` 等を張り **proxy 対応クライアント**
(Bash `curl`=d / WebFetch=h)を localhost proxy に誘導し **allowedDomains 判定**を掛ける(許可側で到達=両側で allowlist が効く) /
(2) 直結ネットワーク/DNS を **hard block**(proxy 非対応クライアント = f の MCP fixture の生 `node https.get` は allowedDomains に
example.com を足しても `ENOTFOUND` で落ちる=allowlist に届かず直結遮断)。**どちらも「srt が egress を塞ぐ」点は同じだが、
allowlist で開けられるかはクライアントが proxy env を尊重するか次第**。

## 要点

- **srt = permission 層はそのまま、OS 境界だけをプロセス全体へ拡張**。組み込みの「Bash 限定」制約を外す。
- FS の倒れる向きが「許可リスト方式」なので、組み込みの弱点(denyRead の列挙漏れ=fail-open、S3-d/S7-k)に強い。
- ただし permission 層の罠(deny の効く形 P3/S9・trust P7-c・保護パス P5)は srt 配下でも同じ。
- ⚠️ ベータ。設定形式が変わりうるので運用前に自分の版で smoke(→ `harness/srt/`)。

## 試し方 — 3つの実行形態から好きな方法で

srt は「claude プロセスをまるごと OS 境界で包む」手段なので、**claude をどの形態で起動しても
srt を頭に付けるだけ**で同じ境界が掛かる。読者は目的に合わせて選べる(全形態を総当たりする必要はない。
挙動は許諾×結果の2軸で確定する → [EXECUTION-MODALITIES](../../docs/EXECUTION-MODALITIES.md))。

```bash
npm i -g @anthropic-ai/sandbox-runtime           # 初回のみ(macOS/Seatbelt)
```

**① 対話(TUI)— いちばん手軽に体感する**
各ケースの `prompt.ja.txt` 冒頭【前提】の手順で番兵/設定を用意し、`srt --settings <settings> claude` を
起動してプロンプトを貼るだけ。承認プロンプトの有無と、srt 配下で操作が黙って失敗する様子をその場で見られる
(a/b/c/e/f/g/h に `prompt.ja.txt` あり)。
⚠️ **srt 配下の TUI は cmux 等での socket 自動駆動が効かない**(srt のプロセス包みが端末のキーボード
プロトコル交渉と干渉し、矢印/Enter が届かない)。**対話は人間が手で駆動する用途**。自動記録は ②③ を使う。

**② ヘッドレス(`claude -p`)— 記録に残す正**
```bash
python3 harness/srt/run_srt_cases.py             # a/b/c/e/f/g/h/j を builtin~/srt で実測 → 各 results/measured.json
python3 harness/srt/run_srt_cases.py h-webfetch-vs-network   # 単一ケースだけ
```

**③ SDK(Claude Agent SDK)— プログラムから同じ境界を確認**
```bash
cd harness/sdk && npm install && cd -            # 初回のみ
python3 harness/srt/run_srt_cases.py -m sdk a-read-tool-caught   # → results/sdk.json(measured.json は触らない)
```
`-m sdk` は同じ probes を `srt … node harness/sdk/exec_case.mjs`(SDK)で回す。SDK が spawn する claude
プロセスも srt(Seatbelt)内に入ることの実測。ask は `canUseTool` で allow に解決し、`askFired` を記録する。

- `run_srt_cases.py` は各ケースの `case.json` の probes[] を読み、builtin~ / srt の2環境で回して結果 JSON
  (スタンプ付き)を生成。verdict は ALLOWED / DENIED(permission 層)/ DENIED_OS(denials 空 + OS 層 EPERM)。
  期待と食い違ったら結果 JSON は上書きしない(要人間確認)。
- **モダリティ非依存の裏づけ**: a(FS read)/ b(FS write)/ e(Edit)/ h(WebFetch)は headless と SDK の
  両方で同じ verdict(builtin~=ALLOWED / srt=DENIED_OS)を実測済み。srt の OS 境界は許諾エンジンの外側で
  効くので、残りのケースも形態を変えても結論は同じ(2軸から導出)。
  - c(permission 不変)は SDK 併測の対象外: deny のツール除去型は SDK 経路だと対象ツールの denial が出ず
    層帰属が OS に寄る。permission 層が形態非依存であることは 01/02 の P2-a/P2-b が SDK で実測済み(そちらに委譲)。
- 旧 `bash harness/srt/run_differential.sh` は a/b/c の差分表を1枚出す簡易版(後継が上記)。
- d は cmd 型(claude 非経由)。既定の全ケース実行(無指定)では回さない(明示選択で回る)。j も cmd 型だが
  runner 所有なので既定で回る。cmd 型は claude を経由しないためモダリティ軸が無い(`-m sdk` では skip)。

## 対応する知識

- [docs/SANDBOX-RUNTIME-FINDINGS.md](../../docs/SANDBOX-RUNTIME-FINDINGS.md) — 差分実測の総括・未決事項
- [docs/SANDBOX-ENVIRONMENTS.md](../../docs/SANDBOX-ENVIRONMENTS.md) — 手段2 の位置づけ
- 組み込み側の迂回実測: `cases/S1-sandbox-scope-vs-tools`(S1-f) / `cases/S3-sandbox-fs-read`(S3-d) / `cases/S6-sandbox-network`
- 組み込み側の別プロセス迂回: `cases/S1-sandbox-scope-vs-tools`(S1-h=MCP / S1-i=hook)/ `cases/S6-*`(S6-h=WebFetch)
- 実測済み経路: Read(a)/Write(b)/Edit(e)/MCP(f)/hook(g)/WebFetch(h) は srt が OS 層で塞ぐ。env(j)は srt の対象外(倒せない面)。
- モダリティ: headless は全ケース。SDK は a/b/e/h で headless と一致(`results/sdk.json`)= srt 境界は形態非依存。対話は prompt.ja.txt で手動再現(自動駆動は srt×TUI のキーボード交渉制約で不可)。
- 未実測: Linux(bubblewrap)(→ FINDINGS 未決事項)
