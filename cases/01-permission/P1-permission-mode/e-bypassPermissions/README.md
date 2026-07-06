# P1-e: bypassPermissions モード → permission プロンプト省略で書込系がすべて通る

## 目的

- bypassPermissions が permission プロンプトを省略し、規則なしで書込がパス・ツールによらず通ることを確認する

## 前提(設定)

```json
{}
```

- settings.json は空。挙動を変えているのは CLI フラグ `--permission-mode bypassPermissions`
  (`--dangerously-skip-permissions` 相当)のみ
- P1-a と同一プローブ・同一設定で、差分はモードだけ

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成
2. Write でホームディレクトリ(cwd 外)にファイルを作成
3. Write でケース内のサブディレクトリにファイルを作成
4. Edit で既存ファイル(cwd 内)の文字列を置換

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | allow | ✅ | - |
| 2 | Write `~/p1e-proof.txt`(cwd 外) | allow | ✅ | **cwd 外も素通し**(acceptEdits との違い → P1-b) |
| 3 | Write `./sub/proof.txt`(サブdir) | allow | ✅ | - |
| 4 | Edit `./note.txt`(既存ファイル) | allow | ✅ | - |

## なぜそうなるか

- **bypassPermissions は permission プロンプトを丸ごと省略する。** acceptEdits のような cwd 境界もない。
- **保護パス（`.git` 等）への write も skip される**（公式 permissions.md 明記）。acceptEdits は保護パスでプロンプトを出す（→ P5）が、bypassPermissions はそれも省く。
- 残る例外は 2 つだけ: **明示的な `ask` 規則**、**`rm -rf /`・`rm -rf ~` の circuit breaker**（＋ deny 規則は deny-first で先に評価され残る）。【裏取り: 公式 permissions.md「Permission modes」Warning box, 2026-07-05 claude-code-guide 経由確認】

## 運用時の留意事項

- **隔離環境(コンテナ/VM)専用**。permission 層を実質無効化するので、通常の作業で常用しない。
- root/sudo では起動を拒否する(認識された sandbox 内では例外)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

⚠️ 隔離環境でのみ。このディレクトリで bypassPermissions モードの `claude` を起動し、
[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。cwd 外を含む4操作すべてが
承認なしで即実行されることがその場で確認できる。

```bash
cd cases/P1-permission-mode/e-bypassPermissions && claude --permission-mode bypassPermissions
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py P1-permission-mode/e-bypassPermissions
python3 harness/run.py -m sdk P1-permission-mode/e-bypassPermissions
```

> permission を丸ごと省略してどの形態でも通すため**全形態で同結論**。
> SDK では追加スイッチ `allowDangerouslySkipPermissions` が必要(ハーネスが自動付与)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(4プローブとも一致) |
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | sdk(4プローブとも ALLOWED で一致。canUseTool 非発火 + 副作用あり=事前 allow の実証) |

## 対応する知識

- グループ [P1 README](../README.md)
- 関連: P1-a(default は ask)/ P1-b(acceptEdits は cwd 境界あり)/ P5(**acceptEdits では保護パスにプロンプト。bypassPermissions では保護パスも skip**)
