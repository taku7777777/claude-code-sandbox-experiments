# S1-g: 未 trust の workspace でも sandbox は生きる — `sandbox.enabled`/`allowWrite` は workspace trust の非ゲート対象

## 目的

- **未 trust(trust ダイアログ未承認)の workspace で、project settings の `sandbox.enabled` が有効化されるか**を実測する。
- 運用上の含意(→ multi-repo-workspace.md): worker の settings.json は project スコープで、
  open-task.sh が Phase 1 で `hasTrustDialogAccepted=true` を注入する = **安全モデル全体が「trust 設定の成功」を暗黙の前提にしている**。
  もし未 trust で sandbox が off になるなら、trust 注入が失敗した worker は OS 境界ごと消えて全開になる(最悪の失敗モード)。
  これが起きないことを確認する。

## 前提(設定)

project(`.claude/settings.json`):

```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": { "allowWrite": ["~/lab-untrust-allowed"] }
  }
}
```

- workspace は**未 trust**(ハーネスが `arrange.configDir: { "trusted": false }` で再現。trust は git repo root 単位で
  `~/.claude.json` の `projects[<root>].hasTrustDialogAccepted` に保存される → P7-c と同型)。

## 実行内容

1. Bash で cwd 直下 `inside.txt` に書込(sandbox の autoAllow が生きているかの一次シグナル)
2. Bash で cwd 外・非 allowlist `~/lab-untrust-probe/probe.txt` に書込(OS 境界が生きているかの対照)
3. Bash で allowWrite 登録先 `~/lab-untrust-allowed/probe.txt` に書込(allowWrite が未 trust でも効くか)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > inside.txt`(cwd 内) | allow | ✅ | **未 trust でも autoAllow が発火** = sandbox 有効。off なら permission 層に落ち headless で ask→auto-deny ❌ になるはず |
| 2 | Bash `echo > ~/lab-untrust-probe/probe.txt`(cwd 外・非 allowlist) | allow | ❌ | **OS 境界も生きている**(EPERM)。sandbox off ではこの遮断が消える |
| 3 | Bash `echo > ~/lab-untrust-allowed/probe.txt`(allowWrite 登録先) | allow | ✅ | **`allowWrite` は未 trust でも有効** = sandbox.filesystem は trust 非ゲート |

## なぜそうなるか

- **`sandbox.enabled` と `sandbox.filesystem.*` は workspace trust のゲート対象外**。docs(permissions: workspace trust)は
  trust が縛るのは **`permissions.allow` と `additionalDirectories`** だけと明記し、sandbox キーを列挙しない。
  ゆえに未 trust でも sandbox 境界はそのまま張られる(cwd auto-allow・cwd 外 EPERM・allowWrite 適用のすべてが生きる)。
- 対比: P7-c は「未 trust → project の `permissions.allow` が無視され Write ツールが ask に落ちる」を実測した。
  **落ちるのは permission 層の allow だけで、OS 層の sandbox は落ちない**——この2層の trust 依存の差が本ケースの核心。
- probe 1 が ✅ であること自体が「autoAllowBashIfSandboxed が発火 = sandbox 有効」の証跡
  (sandbox off なら Bash は sandbox auto-allow を受けられず permission 層へ落ち、headless default で ask→auto-deny ❌ になる)。

## 運用時の留意事項

- **trust 注入が失敗しても sandbox の OS 境界は落ちない**——これは defense-in-depth として朗報。
  worker が何らかの理由で未 trust のまま起動しても、denyWrite/allowWrite/network の OS 層制御は効き続ける。
- ただし**未 trust で失われるものはある**: project の `permissions.allow`(Bash 個別 allow・Edit/Write 系 allow)と
  `additionalDirectories` は無視される(P7-c)。つまり未 trust の worker は「sandbox は効くが、permission 層の
  利便化(allow 済みが通る・追加ディレクトリが見える)が消えて ask だらけになる」= **安全側に倒れる**。
  安全性ではなく**可用性**の問題として trust 注入の成否を監視する。
- 注意の非対称: sandbox は trust に依存しないが、**local スコープの settings は trust と無関係に効く**ため、
  sandbox 境界を local から緩める経路(→ S2-n / S3-n / S6-i)は未 trust でも成立する。trust は「project allow の
  ゲート」であって「local ドリフトの防波堤」ではない。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

未 trust 状態の再現には分離 `CLAUDE_CONFIG_DIR`(trust 未設定)での起動が要るため、手軽な再現はハーネス推奨。
プロンプトの要点は [prompt.ja.txt](./prompt.ja.txt)。

### ハーネスで実測する

```bash
python3 harness/run.py S1-sandbox-scope-vs-tools/g-untrusted-sandbox-enforced
python3 harness/run.py -m sdk S1-sandbox-scope-vs-tools/g-untrusted-sandbox-enforced
```

> `arrange.configDir: { trusted: false }` が未 trust の分離 config dir を組み立てる(credentials は Keychain/
> `~/.claude/.credentials.json` からコピー、finally で必ず削除)。probe=`fs-write`。EPERM 文言は evidenceMarker で記録。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-06 | v2.1.201 / SDK 0.3.200 | headless / sdk(3プローブとも一致。未 trust でも 1,3=✅ / 2=EPERM=sandbox 有効を確定) |

## 対応する知識

- docs/FINDINGS.md: グループ [S1 README](../README.md)
- 一次 docs: permissions(workspace trust が縛るのは allow/additionalDirectories のみ)、sandboxing(OS 層の境界)
- 関連: P7-c(未 trust → project allow 無視・deny/ask は有効 = permission 層の trust 依存)/
  S2-n・S3-n・S6-i(local ドリフトは trust 非依存で成立)/ S1-a(trusted 前提の sandbox baseline)
