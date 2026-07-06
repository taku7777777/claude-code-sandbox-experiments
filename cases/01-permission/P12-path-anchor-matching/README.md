# P12. path-anchor-matching — 規則のパス表記(相対/絶対/`~/`/`//`)× 呼び出しパス表記でマッチが変わるか

## この章で学ぶこと

「`permissions.allow`/`deny` を**相対パスで書いた規則が、絶対パスでのツール呼び出しに効くのか**」
「**絶対パスで実行されたら制御対象外に抜けないか**」——この 2 つを Edit 規則(パスマッチが docs 保証される
唯一の編集系規則)で 1 変数ずつ実測する。結論を先に:

- **エスケープは起きない**。相対(cwd 起点)の規則は、**絶対パス**でのツール呼び出しにマッチしてブロック/承認する
  (deny=a / allow=f)。`sub/../sub/` のような**非正規化パスでも抜けられない**(b)=マッチは表記でなく
  **解決済みパス**で行われる。
- **ただし絶対パスで規則を書くときは表記で無言に割れる**: **`~/`(home アンカー)と `//`(二重スラッシュ)は効く**
  (e / d)が、**単一スラッシュ `/abs/...` は allow も deny も無言 no-op**(c / g)。P3 の Write path no-op と同系の
  「書いたのに効かない・エラーも警告も出ない」罠。

> 注: Write のパス限定規則は**どの表記でも no-op**(P3 / S9-a)なので、この「表記で割れる」問題が意味を持つのは
> **Edit / Read 規則**(パスマッチが docs 保証される側)。本群は Edit で測る。

## サブケース一覧

| サブ | 規則 | 呼び出しパス | モード | 論点 | 詳細 |
|---|---|---|---|---|---|
| a | deny `Edit(sub/**)`(相対) | 絶対 `$CASE_DIR/sub/note.txt` | acceptEdits | 相対 deny は絶対呼び出しを捕捉(エスケープ不成立) | [a-rel-deny-abs-call](./a-rel-deny-abs-call/README.md) |
| b | deny `Edit(sub/**)`(相対) | 非正規化 `…/sub/../sub/note.txt` | acceptEdits | `..` 難読化でも捕捉(正規化後にマッチ) | [b-rel-deny-nonnormalized-call](./b-rel-deny-nonnormalized-call/README.md) |
| c | deny `Edit(/abs/sub/**)`(単一 `/`) | 絶対 | acceptEdits | ⚠️ 単一スラッシュ絶対 deny は**無言 no-op** | [c-singleslash-abs-deny-noop](./c-singleslash-abs-deny-noop/README.md) |
| d | deny `Edit(//abs/sub/**)`(二重 `//`) | 絶対 | acceptEdits | 二重スラッシュ絶対 deny は**効く**(c と 1 スラッシュ差) | [d-doubleslash-abs-deny](./d-doubleslash-abs-deny/README.md) |
| e | deny `Edit(~/dir/sub/**)`(home) | 絶対 `$HOME/lab-p12/sub/…` | acceptEdits | `~/` home アンカーは**効く** | [e-home-anchor-deny](./e-home-anchor-deny/README.md) |
| f | allow `Edit(sub/**)`(相対) | 絶対 | default | 相対 allow は絶対呼び出しを事前承認(a と対称) | [f-rel-allow-abs-call](./f-rel-allow-abs-call/README.md) |
| g | allow `Edit(/abs/sub/**)`(単一 `/`) | 絶対 | default | ⚠️ 単一スラッシュ絶対 allow も**無言 no-op**(ask に落ちる) | [g-singleslash-allow-noop](./g-singleslash-allow-noop/README.md) |

すべて cwd 内の `sub/note.txt` を対象にし(e のみ home 配下 + `additionalDirectories`)、
**規則の表記**か**呼び出しの表記**のどちらか 1 つだけを振って対照する。

## 対比 — 規則アンカー形 × 効くか(全セル実測 headless+SDK)

| No | 規則の書き方 | 種別 | 効くか | headless | SDK | 意味 |
|---|---|---|:---:|:---:|:---:|---|
| a | `Edit(sub/**)` 相対 | deny | ✅ 効く | INCONCLUSIVE† | DENIED_HARD | 相対規則が絶対呼び出しを捕捉 |
| b | `Edit(sub/**)` 相対 + `..` 呼び出し | deny | ✅ 効く | INCONCLUSIVE† | DENIED_HARD | 正規化後にマッチ(難読化不成立) |
| c | `Edit(/abs/sub/**)` 単一スラッシュ | deny | ❌ **no-op** | ALLOWED | ALLOWED | ⚠️ 書いたのに素通り(編集成立) |
| d | `Edit(//abs/sub/**)` 二重スラッシュ | deny | ✅ 効く | INCONCLUSIVE† | DENIED_HARD | 絶対で効く形は `//` |
| e | `Edit(~/dir/sub/**)` home | deny | ✅ 効く | INCONCLUSIVE† | DENIED_HARD | 絶対で効く形は `~/` |
| f | `Edit(sub/**)` 相対 | allow | ✅ 効く | ALLOWED | ALLOWED | 相対 allow が絶対呼び出しを事前承認 |
| g | `Edit(/abs/sub/**)` 単一スラッシュ | allow | ❌ **no-op** | DENIED(auto-deny) | ASK | ⚠️ 事前承認されず ask のまま |

† Edit deny は headless では denials に載らず内容も変わらないため構造的に INCONCLUSIVE(by-design)。
SDK の canUseTool 非発火 + 編集不成立で DENIED_HARD を確定する(S9-a3 と同じ計測方式)。

## 効く形・効かない形(まとめ)

| アンカー形 | 例 | allow | deny |
|---|---|:---:|:---:|
| 相対(cwd 起点) | `Edit(sub/**)` | ✅(f) | ✅(a,b) |
| home | `Edit(~/dir/sub/**)` | (✅)‡ | ✅(e) |
| 二重スラッシュ絶対 | `Edit(//abs/sub/**)` | (✅)‡ | ✅(d) |
| **単一スラッシュ絶対** | `Edit(/abs/sub/**)` | ❌ **no-op**(g) | ❌ **no-op**(c) |

‡ home/`//` の allow 側は本群では未実測(deny 側 e/d が効くことと、相対 allow f が効くことからの推定。
別ケースで実測したら裸の値へ格上げ)。

## 運用時の留意事項

- **ユーザーの懸念への答え**: 相対パスで書いた規則は絶対パス実行で無効化されない(a/b/f)。マッチは
  **解決済みの絶対パス**で行われ、規則側の表記(相対/絶対)・呼び出し側の表記(正規化/非正規化)の差では抜けない。
- **本当の罠は絶対パスで規則を書くときの `/` の数**: 死守パスを絶対で指定したいなら **`~/` か `//`** を使う。
  単一 `/abs/...` は allow(CI で通らない)/ deny(守れない)どちらも**無言で失敗**する。
- **迷ったら相対形が最も堅い**(cwd 起点で解決され、a/b/f のとおり表記差に強い)。絶対を使う必然が無ければ相対で書く。
- どの形も**書いたら空撃ちで確認**(BEST-PRACTICES §0)。この no-op はエラーも警告も出ない(P3 と同型)。

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索(a〜g)→ headless / sdk(7 サブケース一致) |

- Edit 規則のパスマッチは docs 保証(「Edit/Read rules は gitignore 準拠のパス」)。**絶対アンカーの `//` 有効・単一 `/` 無効は
  docs 未明記=本群が一次証拠**(FINDINGS の `Write(//<abs>/**)` 記述と整合)。

## 対応する知識

- docs/FINDINGS.md「パスアンカーの罠」/ docs/ARCHITECTURE.md §2.3(マッチングの罠)
- 関連: P3(Write path は全表記 no-op=表記問題が Edit 限定である理由)/ S9-d/d2(additionalDirectories の別ルートに
  cwd 起点規則がマッチしない=別軸のアンカー罠。`~/` アンカーで修正)/ P7-c(additionalDirectories は未 trust で無視)
