# S3-m: allowRead の内側に切った denyRead が勝つ — read 側でも「狭い deny > 広い allow」

## 目的

- `allowRead` で開けた領域の**内側に、より狭い `denyRead` を入れ子**にしたとき、どちらが勝つかを確定する(S2-g が write 側で示した「狭い deny > 広い allow」の read 側パリティ)。
- b が示した1段の入れ子(`denyRead:["~"]` を `allowRead:[file]` で戻す)の**逆方向**(allow の中を deny で塞ぎ直す)を測る。

## 前提(設定)

```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": {
      "denyRead": ["~", "~/lab-nest-m/inner"],
      "allowRead": ["~/lab-nest-m"]
    }
  }
}
```

- `denyRead:["~"]` で home 全域を塞ぎ、`allowRead:["~/lab-nest-m"]` で1ディレクトリだけ戻し、さらに `denyRead:["~/lab-nest-m/inner"]` でその内側を塞ぎ直す3層。

## 実行内容

1. Bash で `cat ~/lab-nest-m/f.txt`(allowRead 内・inner の外)
2. Bash で `cat ~/lab-nest-m/inner/f.txt`(allowRead 内だが内側 denyRead の中)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `cat ~/lab-nest-m/f.txt` | allow | ✅ | allowRead が効いて読める → 番兵が漏れる(allow が実際に開いた証明) |
| 2 | Bash `cat ~/lab-nest-m/inner/f.txt` | allow | ❌ | 内側の denyRead が広い allowRead に勝ち OS 層で遮断(`MARK_S3M_IN` は出るが番兵は出ない) |

- **1(外側=読める)が対照**: これが無いと 2 の ❌ が「deny が勝った」のか「そもそも allow が効いていない」のか区別できない。1 で allow の発効を確認した上で 2 の遮断を見るので、「入れ子の deny 勝ち」が確定する。

## なぜそうなるか

- **sandbox FS 層では、より具体的(狭い)な deny が広い allow に勝つ。再許可した領域の内側を deny で塞ぎ直せる。** write 側(S2-g)と同じ優先則が read 側でも成り立ち、非対称(read だけ allow が勝つ等)は無い。

## 運用時の留意事項

- allowRead で広めに開けても、その中の秘密サブディレクトリは `denyRead` を追記すれば個別に塞げる。順序ではなく**具体度で deny が勝つ**ので、記述順を気にせず「開けてから穴を塞ぐ」構成が書ける。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

```bash
cd cases/S3-sandbox-fs-read/m-nested-denyread-wins && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S3-sandbox-fs-read/m-nested-denyread-wins
python3 harness/run.py -m sdk S3-sandbox-fs-read/m-nested-denyread-wins
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(2回反復で安定)/ sdk(2プローブ一致) |

## 対応する知識

- docs/FINDINGS.md: 「sandbox FS 層は deny が allow に勝つ(具体度優先)」(S2-g で write 側、本ケースで read 側)
- 関連: [S2-g](../../S2-sandbox-fs-write/g-nested-deny-wins/README.md)(write 側パリティ)/ [b](../b-allowread-reallow/README.md)(1段の再許可)/ [グループ README](../README.md)
