# S2-g: 広い allowWrite + 内側 denyWrite → 外は書けるが内は deny 勝ち(`allow ❌`)

## 目的

- sandbox FS で「広く allowWrite → 内側を denyWrite」したとき、**外側は書けて内側だけ deny が勝つ**ことを2プローブで実測する。
- 外側プローブ(書ける)を置くことで、「deny が勝った」を「そもそも allow が効いていない」から**分離**する。

## 前提(設定)

```json
{ "sandbox": { "enabled": true,
  "filesystem": { "allowWrite": ["~/lab-nest"], "denyWrite": ["~/lab-nest/sub"] } } }
```

- `allowWrite` は `~/lab-nest` を覆い、`denyWrite` がその内側 `~/lab-nest/sub` を抜く。
- 旧版にあった `permissions.allow:["Bash(*)"]` は削除。sandbox が Bash を自動許可する(S2-a/S4-a)ため不要で、パス規則でもない。
- `arrange`: `~/lab-nest`(外)と `~/lab-nest/sub`(内)を先に作り、実行後 `cleanup` で `~/lab-nest` を撤去。

## 実行内容

1. Bash で `~/lab-nest/f.txt`(allow の内側・deny の外側)に書込
2. Bash で `~/lab-nest/sub/f.txt`(denyWrite で抜いた内側)に書込

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo x > ~/lab-nest/f.txt` | allow | ✅ | **allowWrite が実際にツリーを開けている**ことの証拠 |
| 2 | Bash `echo x > ~/lab-nest/sub/f.txt` | allow | ❌ | 内側の denyWrite が広い allow に勝つ |

- プローブ1(✅)が無いと、2の ❌ が「deny 勝ち」なのか「allow が最初から効いていない」のか区別できない。2プローブで初めて「deny 勝ち」が言える。

## なぜそうなるか

- **sandbox FS 層でも deny が allow に勝つ**(docs: permissions —「広い deny は、より狭い allow にマッチする呼び出しも含めてブロックする」)。広い `allowWrite` で覆っても、内側の `denyWrite` 領域は書けない。
- 【要裏取り】「deny 領域の内側をさらに再 allow できるか」(read 側の `allowRead` に相当する write 側の再許可)は**公式 docs に記載が無く、本ケースでも未実測**。ここで確定しているのは「広 allow + 内 deny → 内は deny 勝ち」までで、「再 allow が効かない」という1段強い主張は S2 GAPS G2 のバックログ。

## 運用時の留意事項

- **書かせたいものは deny 領域の「外」に置く**。「広く許可して内側を deny、さらに内側を再許可」の入れ子には頼らない(write 側の再 allow は未確認)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。1 は成功、2 は `operation not permitted` になり、外は書けて内だけ止まることが見える。

```bash
cd cases/S2-sandbox-fs-write/g-nested-deny-wins && claude
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S2-sandbox-fs-write/g-nested-deny-wins
python3 harness/run.py -m sdk S2-sandbox-fs-write/g-nested-deny-wins
```

> probe=`fs-write`。判定は対象パスの存在。deny は OS 層で効くため canUseTool には現れない。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致) |

## 対応する知識

- refactor-plan.md §2.5(W3)/ グループ [S2 README](../README.md)
- 関連: S2-b(allowWrite は効く)/ S2-d(denyWrite:["~"] の罠)/ S9-b(sandbox denyWrite の Bash `allow ❌`)/ P2(permission 層の deny-first)
