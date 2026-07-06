****# BEST-PRACTICES — Claude Code を安全に・詰まらずに使う

FINDINGS.md の実測結果を、運用の型に落としたもの。検証環境は Claude Code 2.1.201。

---

## 0. 大原則:設定は「撃って確かめる」

permission のマッチングは非公開仕様でバージョン差もあり、**書いた規則が効いている保証はない**
(FINDINGS の glob 地雷を参照)。特に `deny` は「書いたのに無効」が最悪ケース。

```bash
# その設定ディレクトリで 1 発撃って permission_denials を見る最小手順
cd <対象ディレクトリ>
claude -p "対象の操作をやって" --output-format json --max-turns 3 \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("denied:",[x["tool_name"] for x in d.get("permission_denials",[])])'
```

本リポジトリの `harness/run.py` はこれを型化したもの。**新しい deny/allow を入れたら必ず 1 ケース足して実測**。

---

## 1. 「詰まり」対策(拒否されて進まない)

### 症状: headless / CI で write が全部拒否される
- **原因**: `default` モードは write に人間承認を要求 → 承認者がいない headless では拒否(FINDINGS Q1)。
- **対処**: 意図を明示する。
  - 編集を任せたい: `--permission-mode acceptEdits`
  - 特定操作だけ許可: `settings.json` の `allow` に列挙(下記の書き方に注意)
  - フル自動の隔離環境のみ: `--dangerously-skip-permissions`(**信頼できる sandbox/CI 専用**)

### 症状: sandbox を on にしたのにファイル編集で承認を求められる
- **原因**: sandbox の auto-allow は **Bash 専用**。Write/Edit ツールは対象外(FINDINGS Q2)。
- **対処**: ファイル編集は permission 側(`acceptEdits` か `allow`)で許可する。sandbox とは別レイヤーと考える。

### `allow` の書き方(実測で効く形)
```jsonc
{
  "permissions": {
    "allow": [
      "Bash(npm run test:*)",   // コマンドは prefix + :* で
      "Edit(src/**)",           // Edit/Read のパスは gitignore 風で概ね機能
      "Write(*)"                // ★ Write ツールは Write(*) / bare "Write" が確実。
                                //   Write(**) や Write(./file) は効かない実測あり(FINDINGS 発見1)
    ]
  }
}
```

---

## 2. 「守り」対策(勝手に危険なことをさせない)

### 鉄則 A: `deny` を「うっかり防止」以上に信用しない
- `&&`/`;`/`|` チェーンは各サブコマンド個別照合なのですり抜けない(P4-b/09)——ここは強い。
- しかし **`sh -c '...'` / `bash -c '...'` / 変数展開 / `$(...)`** で文字列ベースの deny は容易にすり抜ける(P4-c)。
- → `deny` は「モデルの事故」対策。**「悪意ある実行を止める境界」ではない**。

### 鉄則 B: 本当に止めたいものは OS レイヤ(sandbox)で止める
- ネットワーク遮断: `deny Bash(curl:*)` ではなく **sandbox のネットワーク制御**を使う。
  ```jsonc
  { "sandbox": { "enabled": true,
      "network": { "allowedDomains": ["registry.npmjs.org", "*.github.com"] } } }
  ```
  これは OS レベルなので `sh -c 'curl ...'` でも効く(permission の文字列照合と違う層)。
- ファイル流出防止: sandbox の書き込み境界は **cwd + 付替え `$TMPDIR` + `allowWrite` ∪ permission の Edit 系 allow 規則**(マージ=S2-h)。cwd 外(`$HOME` 等)は既定で OS ブロック(S2-c 実測)。Edit 系 allow 規則を置くと sandbox 境界まで広がる点に注意。
  秘密ファイルの読み取りは `sandbox.credentials` / `denyRead` で塞ぐ。

### 鉄則 C: `deny` は必ず `Write(*)` 相当の効く形で書き、実測する
- 特定ファイルを守るつもりの `deny Write(secret.txt)` は **無言で無効**だった(P3-c)。
- 効いたのは `deny Write(*)`(ツール単位)。**「特定パスだけ deny」は当てにしない**。
- 秘密は「deny で守る」より「そもそも読める場所に置かない / sandbox の `denyRead` で塞ぐ」方が堅い。

### 鉄則 D: 保護パスは自動承認されない(これは味方)
- `.git` `.claude` `~/.ssh` `.npmrc` 等の**保護パス**は、`allow` や `acceptEdits` があっても
  常に個別承認を要求する(P5-a)。CI で誤って `.git` を書き換える事故は起きにくい。

### 鉄則 E: bypassPermissions で「残る境界・消える境界」を正しく覚える(横断1表)

「bypass でも最悪は防げる」という思い込みが一番危ない。実測(P1-e / P2-d / P5-e / P6-d / S9-f)と docs を1表に畳む:

| 機構 | bypass で残るか | 根拠 |
|---|:---:|---|
| `deny` 規則(効く形: `Write(*)` / `Edit(dir/**)` 等) | ✅ **残る** | 実測 P2-d(ツール除去)/ S9-f(スコープ形もハード deny 残存) |
| 明示 `ask` 規則 | ✅ **残る**(プロンプト) | 実測 P6-d |
| **保護パス(`.git` `.claude` 等)の ask** | ❌ **skip される = 書ける** | 実測 P5-e(`.git/hooks` 書換 = 任意コード実行が成立し得る) |
| 既定 ask(モードの承認プロンプト全般) | ❌ 消える(全 allow) | 実測 P1-e |
| `rm -rf /`・`rm -rf ~` circuit breaker | ✅ 残る | documented-only(破壊リスクのため非実測。→ P1/P5 要点) |
| MCP `requiresUserInteraction`(v2.1.199+) | ✅ 残る(prompt) | documented-only(→ P5/P6 要点) |
| sandbox(OS 層: FS / network / credentials) | ✅ 残る | docs: permission mode と独立の層(S1/S2 で層の独立は実測済み。bypass×sandbox の直接の組合せ実測は無し) |

- → **bypass 運用で信用してよい防御は「deny 規則・明示 ask 規則・sandbox」だけ**。保護パスは守ってくれない。
  bypass は隔離環境(コンテナ / 使い捨て VM)専用が唯一の安全側運用(P5-e)。
- **モードごと封じる公式設定がある**(→ §3)。組織で bypass/auto を禁止するならこちら。

---

## 3. 設定の優先順位(効かせ方)

高 → 低:
1. **managed settings**(`/etc/claude-code/managed-settings.json` 等、上書き不可)
2. **CLI フラグ**(`--permission-mode`, `--allowedTools` …)
3. `.claude/settings.local.json`(個人・非共有)
4. `.claude/settings.json`(プロジェクト共有)
5. `~/.claude/settings.json`(ユーザ)

- **permission の allow/ask/deny 配列は「上書き」ではなく「マージ(連結)」**。
  どこかの層に deny があれば効く(規則が正しくマッチする限り)。
- 組織で強制したいポリシーは **managed settings** に置く(利用者が消せない)。
- **モードそのものを封じる設定**(documented-only・2026-07-06 一次 docs 確認):
  `permissions.disableBypassPermissionsMode` / `permissions.disableAutoMode` に文字列 `"disable"` を
  設定すると、bypassPermissions / auto モードを**使用禁止にできる**(`--permission-mode` フラグも起動時に
  拒否され、auto は Shift+Tab サイクルからも消える)。任意スコープで書けるが、上書きされない
  **managed settings に置くのが定石**(permissions / settings / permission-modes docs 明記)。
  ```jsonc
  // managed-settings.json
  { "permissions": { "disableBypassPermissionsMode": "disable", "disableAutoMode": "disable" } }
  ```
  本リポジトリでは未実測(managed 環境前提。→ P1 README のモード封じ注記)。
- **ディレクトリ単位の設定は cwd の `.claude/settings.json` が拾われる**(本リポジトリで実測)。
  ケースごとにディレクトリを切って設定を変える運用は有効。

---

## 4. 推奨プリセット

### CI / 自動化(信頼できる作業を回す)
```jsonc
// .claude/settings.json
{
  "permissions": {
    "allow": ["Bash(npm run build:*)", "Bash(npm run test:*)", "Edit(src/**)", "Write(*)"],
    "deny":  ["Bash(curl:*)", "Bash(wget:*)"]   // 事故防止。境界は下の sandbox で担保
  },
  "sandbox": {
    "enabled": true,
    "network": { "allowedDomains": ["registry.npmjs.org", "*.github.com"] }
  }
}
```
実行: `claude -p "<task>" --permission-mode acceptEdits --output-format json`
(隔離コンテナ内なら `--dangerously-skip-permissions` も可)

### 日常の対話利用(安全寄り)
```jsonc
{
  "permissions": {
    "ask":  ["Bash(git push:*)", "WebFetch"],       // 外向き・破壊的は毎回確認
    "deny": ["Read(~/.ssh/**)", "Read(.env)", "Write(*)"] // Write(*) の形で確実に
  },
  "sandbox": { "enabled": true }                     // Bash は sandbox 内で自動実行、境界は OS が担保
}
```
> `deny Write(*)` を入れると全 write が承認待ちになる。編集も自動化したい場合は外し、
> 代わりに `acceptEdits` + 保護パス(自動で効く)に任せる、と使い分ける。

---

## 5. チェックリスト

- [ ] deny/allow を追加したら **その形が本当に効くか 1 発実測**した(特に `Write(...)` 系)
- [ ] Write の許可/拒否は **`Write(*)` / bare `Write`** で書いた(`Write(**)`・パス指定は避けた)
- [ ] ネットワーク/ファイル流出など**本当の境界は sandbox(OS)**側で担保した(deny 任せにしない)
- [ ] headless/CI で使うモード(`acceptEdits` 等)を**明示**した(default 依存で詰まらせない)
- [ ] 秘密は「読める場所に置かない / `denyRead`」で守った(`deny Write(path)` を信用しない)
- [ ] 組織ポリシーは **managed settings** に置いた
