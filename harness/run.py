#!/usr/bin/env python3
"""
Claude Code permission/sandbox 挙動の実測ハーネス。

設計: 「ケース定義はモダリティ非依存、実行だけがモダリティ固有」
  - 1ケース = 1ディレクトリ。前提(.claude/settings.json)・プロンプト(prompt.txt)・
    観測/期待値(case.json)はどの実行形態でも共通に使う。
  - 本スクリプトはケースのライフサイクル(clean → setup/prep → 実行 → 観測 → 判定 → 片付け)
    を共通に持ち、「実行」ステップだけをモダリティ別アダプタに委譲する:
      headless    : `claude -p ... --output-format json` を subprocess 起動
      sdk         : harness/sdk/exec_case.mjs (Claude Agent SDK) に JSON で委譲
      interactive : prepare(準備+手順提示) と judge(人間の観察を記録) の2段構え

ケースディレクトリの構成(仕様の正本は docs/CASE-FORMAT.md):
  .claude/settings.json   検証対象の設定(全モダリティ共通の前提)
  prompt.txt              モデルへ送るプロンプト($REPO / $HOME トークン可)
  case.json               probe / 観測 / 期待値 / 実行パラメータ(モダリティ非依存)
  results/<modality>.json 実測結果(headless.json / sdk.json / interactive.json)

実行:
  python3 harness/run.py                                   # 全ケースを headless で
  python3 harness/run.py -m sdk P1-permission-mode         # グループを SDK で
  python3 harness/run.py -m interactive --step prepare P1-permission-mode/a-default-deny
  python3 harness/run.py -m interactive --step judge   P1-permission-mode/a-default-deny
  python3 harness/run.py --list                            # ケース一覧と実測状況
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MODEL = os.environ.get("LAB_MODEL", "claude-haiku-4-5-20251001")
HARNESS_DIR = Path(__file__).resolve().parent

_CLAUDE_VERSION = None


def claude_version() -> str:
    """`claude --version` の版数(例 "2.1.201")。results へのスタンプ用(1回だけ取得)。

    バージョン依存挙動(credentials=v2.1.187+ / mask=v2.1.199+ 等)の再現性確認のため、
    README の検証記録と results を突合できるようにする(F7 / S7 GAPS G10)。
    """
    global _CLAUDE_VERSION
    if _CLAUDE_VERSION is None:
        try:
            out = subprocess.run(["claude", "--version"], capture_output=True,
                                 text=True, timeout=30).stdout.strip()
            _CLAUDE_VERSION = out.split()[0] if out else "unknown"
        except (subprocess.SubprocessError, OSError):
            _CLAUDE_VERSION = "unknown"
    return _CLAUDE_VERSION
CASES_DIR = HARNESS_DIR.parent / "cases"
SUMMARY_DIR = HARNESS_DIR.parent / "results"
SDK_EXEC = HARNESS_DIR / "sdk" / "exec_case.mjs"

# 環境非依存トークン ($HOME / $REPO / $CASE_DIR) と実パスの相互変換。
# 実行時は input(prompt / settings.json / prep)をトークン→実パスへ展開し、
# 永続化する成果物(results/*.json)は実パス→トークンへ伏せる。
# こうすることでケース定義や結果に OS ユーザ名やクローン先が焼き込まれない。
# $CASE_DIR: ファイルパスを取るツール(Write/Read/Edit)は相対パスだとツール検証で
# 失敗し permission 評価まで到達しないことがある(特に SDK)。プロンプトは
# $CASE_DIR で場所を一意にし、どのモダリティでも同一テキストを共有する。
HOME_ABS = os.path.expanduser("~")
REPO_ABS = str(CASES_DIR.parent)


def _subst_tokens(s: str, case_dir=None) -> str:
    """トークン→実パス(実行入力用)。"""
    if case_dir is not None:
        s = s.replace("$CASE_DIR", str(case_dir))
    return s.replace("$REPO", REPO_ABS).replace("$HOME", HOME_ABS)


def _scrub(s: str) -> str:
    """実パス→トークン(永続化出力用)。REPO は HOME 配下なので REPO を先に置換する。"""
    return s.replace(REPO_ABS, "$REPO").replace(HOME_ABS, "$HOME")


def expand(p: str, case_dir: Path) -> Path:
    p = os.path.expanduser(p)
    return Path(p) if os.path.isabs(p) else (case_dir / p)


def _rm(fp: Path):
    try:
        if fp.is_dir():
            shutil.rmtree(fp)
        elif fp.exists():
            fp.unlink()
    except FileNotFoundError:
        pass


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- case loading

def load_case(case_dir: Path) -> dict:
    case = json.loads((case_dir / "case.json").read_text())
    case.setdefault("run", {})
    case.setdefault("arrange", {})
    case.setdefault("observe", {})
    case.setdefault("modalities", {})
    # probes[] 正規化: 同一設定(settings.json)に対する複数プローブ。各プローブは
    # 独立セッションで実行する(前プローブの deny がモデルの後続挙動を汚染しないため)。
    # 旧形式(トップレベル単一プローブ)は probes 1要素と等価に扱う。
    if not case.get("probes"):
        case["probes"] = [{"id": "main"}]  # 各フィールドは probe_view が case から継承
    for p in case["probes"]:
        p.setdefault("id", "main")
        p.setdefault("arrange", {})
    return case


def probe_view(case: dict, probe: dict) -> dict:
    """probe の値を case に重ねた「単一プローブ視点」の dict を作る。

    判定/実行ロジック(judge / expected_for / exec_* / sdk_permission_verdict)はすべて
    単一プローブ前提で case dict を読むので、この view を渡すだけで probes[] に対応する。
    probe 側にあるフィールド(tool / probe / expected / observe)が case 値を上書きする。
    """
    v = dict(case)
    for k in ("tool", "probe", "expected", "observe"):
        if k in probe:
            v[k] = probe[k]
    v.setdefault("observe", {})
    return v


def probe_prompt(case_dir: Path, probe: dict) -> str:
    """プローブのプロンプトを解決する。probes[].prompt(インライン)優先、無ければ prompt.txt。"""
    if probe.get("prompt"):
        return probe["prompt"].strip()
    return (case_dir / "prompt.txt").read_text().strip()


# ------------------------------------------------------- expected(期待値)の解決
#
# 挙動は「2軸」でモダリティ非依存に確定する(→ docs/EXECUTION-MODALITIES.md TL;DR):
#   1) permission(許諾) : allow / deny / ask / none(判定に到達せず) / blocked(未分離)
#   2) result(実行結果) : ok / ng(sandbox 遮断含む) / -(deny で実行に至らない)
# この2軸から各モダリティの期待 verdict を機械導出する。モダリティが変えるのは
# ask の解決だけ(headless=auto-deny / sdk=canUseTool 発火 / interactive=承認プロンプト)。
ENGINE_MAP = {  # 旧 expected.engine 用(後方互換)
    "headless": {"allow": "ALLOWED", "deny": "DENIED", "ask": "DENIED"},
    "sdk": {"allow": "ALLOWED", "deny": "DENIED_HARD", "ask": "ASK"},
    "interactive": {"allow": "ALLOWED", "deny": "DENIED_HARD", "ask": "ASK"},
}


def expected_2axis(permission, result, modality):
    """2軸(許諾 permission + 実行結果 result)から各形態の期待 verdict を導出する。

    None を返したら「このモダリティでは期待値未確定」= match を判定しない。
    """
    if permission in ("allow", "none"):
        # 許諾は通る(or 判定に到達しない)ので結果がそのまま出る。形態非依存。
        return "ALLOWED" if result == "ok" else "DENIED"
    if permission == "deny":
        return "DENIED" if modality == "headless" else "DENIED_HARD"
    if permission == "ask":
        return "DENIED" if modality == "headless" else "ASK"  # sdk/interactive は ask を観測
    if permission == "blocked":
        # 未分離(headless で塞がれたが ask/deny 未確定)。headless のみ期待でき他は保留。
        return "DENIED" if modality == "headless" else None
    return None


def expected_for(case: dict, modality: str):
    """case.json の expected をモダリティ別の期待 verdict へ展開する。

    優先順: byModality(明示) > permission/result(2軸・現行) > engine/observed(後方互換)。
    None を返したら「このモダリティの期待値は未確定」= match は判定しない。
    """
    exp = case.get("expected") or {}
    if isinstance(exp, str):  # 後方互換(旧フラット形式)
        return exp if modality == "headless" else None
    if modality in exp.get("byModality", {}):
        return exp["byModality"][modality]
    if "permission" in exp:   # 現行の2軸形式
        return expected_2axis(exp.get("permission"), exp.get("result"), modality)
    # --- 以下は後方互換(旧 engine / observed 形式) ---
    probe = case.get("probe", "permission")
    if probe == "permission" and exp.get("engine"):
        return ENGINE_MAP[modality][exp["engine"]]
    if probe != "permission":
        return exp.get("observed")
    return exp.get("observed") if modality == "headless" else None


# ---------------------------------------------------------------- lifecycle

def clean(case: dict, case_dir: Path):
    obs = case["observe"]
    extra = [obs["evidenceFile"]] if obs.get("evidenceFile") else []
    for se in obs.get("sideEffects", []) + obs.get("cleanup", []) + extra:
        _rm(expand(se, case_dir))


def do_setup(case: dict, case_dir: Path):
    """arrange.setup: sandbox の外で番兵ファイルを用意する。

    番兵(実値)はプロンプトに含めず、ファイル側にのみ置く。読取が成功すると
    モデルの出力に番兵が現れる = 漏洩/ALLOWED、現れなければブロック/DENIED。
    """
    created = []
    for s in case["arrange"].get("setup", []):
        fp = expand(s["path"], case_dir)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(s.get("content", ""))
        created.append(fp)
    return created


def materialize_settings(case_dir: Path):
    """settings.json のトークンを実行の間だけ実パスへ展開する。

    claude はトークンを展開しないので materialize が必要。戻し用のトークン版
    テキストを返す(トークンが無ければ None = 書き戻し不要)。
    """
    settings_path = case_dir / ".claude" / "settings.json"
    if not settings_path.exists():
        return None
    token_text = settings_path.read_text()
    materialized = _subst_tokens(token_text, case_dir)
    if materialized == token_text:
        return None
    settings_path.write_text(materialized)
    return token_text


def restore_settings(case_dir: Path, token_text):
    if token_text is not None:
        (case_dir / ".claude" / "settings.json").write_text(token_text)


def run_prep(case: dict, case_dir: Path):
    """arrange.prep: sandbox の外で実行する事前準備(git init 等)。"""
    if case["arrange"].get("prep"):
        subprocess.run(_subst_tokens(case["arrange"]["prep"], case_dir), cwd=case_dir, shell=True,
                       capture_output=True, timeout=120)


def write_local_settings(case: dict, case_dir: Path):
    """arrange.localSettings: local スコープ `.claude/settings.local.json` を実行中だけ配置する。

    settings.local.json は per-developer 前提で .gitignore がコミットを禁止しているため、
    fixture 直置きではなくハーネスが生成し finally で必ず撤去する。実行中だけ存在させる
    方式なら「リポジトリがこのファイルを供給しえた」に該当せず workspace trust の
    チェック対象(v2.1.200 仕様)にもならない。既存ファイルは上書きしない(事故防止)。
    """
    ls = case["arrange"].get("localSettings")
    if not ls:
        return None
    fp = case_dir / ".claude" / "settings.local.json"
    if fp.exists():
        raise RuntimeError(f"{fp} が既に存在する(開発者ローカルの設定を上書きしない)")
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(_subst_tokens(json.dumps(ls, indent=2), case_dir))
    return fp


def build_config_dir(case: dict, case_dir: Path):
    """arrange.configDir: 分離した CLAUDE_CONFIG_DIR を一時 dir に組み立てる。

    user スコープ settings と workspace trust を、実環境(~/.claude / ~/.claude.json)を
    汚さず・並行セッションを壊さずに制御するための仕組み(実測 2026-07-05, v2.1.201):
      - credentials: fresh な config dir は未ログイン扱いになるため、macOS Keychain
        ("Claude Code-credentials") または ~/.claude/.credentials.json から一時 dir へ
        コピーする(秘密を含むので finally で必ず dir ごと削除する)
      - .claude.json: onboarding 済みフラグ等を実環境から最小コピー。
        `trusted: true` なら projects[<repo root>].hasTrustDialogAccepted を立てる
        (trust は git repo root 単位でキーされる)。false/省略なら未 trust のまま =
        project settings の allow / additionalDirectories が無視される状態を作れる
      - `userSettings`: <configDir>/settings.json(user スコープ)として書く
    """
    cfg = case["arrange"].get("configDir")
    if cfg is None:
        return None
    tmp = Path(tempfile.mkdtemp(prefix="lab-config-"))
    cred = subprocess.run(["security", "find-generic-password",
                           "-s", "Claude Code-credentials", "-w"],
                          capture_output=True, text=True)
    if cred.returncode == 0 and cred.stdout.strip():
        (tmp / ".credentials.json").write_text(cred.stdout.strip())
    elif (Path(HOME_ABS) / ".claude" / ".credentials.json").exists():
        shutil.copy(Path(HOME_ABS) / ".claude" / ".credentials.json",
                    tmp / ".credentials.json")
    else:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError("credentials が見つからない(Keychain / ~/.claude/.credentials.json)")
    os.chmod(tmp / ".credentials.json", 0o600)

    base = {"hasCompletedOnboarding": True}
    real = Path(HOME_ABS) / ".claude.json"
    if real.exists():
        src = json.loads(real.read_text())
        base.update({k: src[k] for k in ("oauthAccount", "hasCompletedOnboarding",
                                         "lastOnboardingVersion", "installMethod")
                     if k in src})
    if cfg.get("trusted"):
        base["projects"] = {REPO_ABS: {"hasTrustDialogAccepted": True}}
    (tmp / ".claude.json").write_text(json.dumps(base, indent=2))
    if cfg.get("userSettings") is not None:
        (tmp / "settings.json").write_text(
            _subst_tokens(json.dumps(cfg["userSettings"], indent=2), case_dir))
    return tmp


def start_bg(case: dict, case_dir: Path):
    """arrange.bgServer: 検証中だけ動かすバックグラウンドサーバ(unix socket 等)。"""
    if not case["arrange"].get("bgServer"):
        return None
    bg = subprocess.Popen(case["arrange"]["bgServer"], cwd=case_dir, shell=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)  # バインド待ち
    return bg


def stop_bg(bg):
    if bg is None:
        return
    bg.terminate()
    try:
        bg.wait(timeout=5)
    except subprocess.TimeoutExpired:
        bg.kill()


def case_env(case: dict) -> dict:
    """arrange.env: credentials.envVars 検証用の番兵を環境変数として注入する。"""
    env = os.environ.copy()
    env.update(case["arrange"].get("env", {}))
    return env


def preflight_ok(url):
    """network probe 用: 非 sandbox の素 curl で target の実到達性を確認する。

    None(preflight 指定なし)は「確認しない = 到達扱い」。到達失敗(オフライン等)は
    False を返し、呼び出し側で INCONCLUSIVE に落とす(sandbox 遮断との誤判定を防ぐ)。
    """
    if not url:
        return None
    try:
        r = subprocess.run(["curl", "-sS", "--max-time", "10", "-o", os.devnull, url],
                           capture_output=True, timeout=15)
        return r.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


# ---------------------------------------------------------------- probe 判定
#
# probe = 何を一次情報として観測するか。permission 以外は OS 層の観測なので
# モダリティに依存しない共通ロジックで判定できる。
#   permission      : denials + 副作用(headless) / canUseTool 発火(sdk) / プロンプト有無(interactive)
#   fs-write        : 対象パスがディスクに出来たか
#   fs-read         : 番兵(実値)がモデル出力に漏れたか
#   credential-leak : 同上(秘密の漏洩観測)
#   network         : 成功マーカー + 非 sandbox プリフライト

def observe_disk(case: dict, case_dir: Path):
    obs = case["observe"]
    hits = [se for se in obs.get("sideEffects", []) if expand(se, case_dir).exists()]
    # contentMarker: 既存ファイルの内容変化で成功を観測する(Edit 系。ファイルは実行前から
    # 存在するので sideEffects の存在チェックでは判定できない)
    cm = obs.get("contentMarker")
    if cm:
        fp = expand(cm["path"], case_dir)
        try:
            if fp.exists() and cm["contains"] in fp.read_text():
                hits.append(f"content:{cm['path']}")
        except OSError:
            pass
    return hits


def judge(case: dict, case_dir: Path, *, denials, output_text, tool_uses=None,
          exit_code=None, result_text=None) -> dict:
    obs = case["observe"]
    probe = case.get("probe", "permission")
    side_hit = observe_disk(case, case_dir)
    out = output_text or ""
    sentinel = obs.get("sentinel")
    sentinel_found = bool(sentinel) and sentinel in out
    # execMarker: コマンドが実際に実行された証跡。モデルが安全上「試さず拒否」した
    # 場合はマーカーが出ない → 「未実行(判定不能)」と「実行したが遮断(保護)」を区別する。
    exec_marker = obs.get("execMarker")
    ran = (exec_marker in out) if exec_marker else True
    # attempted: 対象ツールの tool_use が実際に発行されたか(構造的な試行証跡・記録用)。
    if tool_uses is None:
        attempted = None
    else:
        tool = case.get("tool")
        attempted = (tool in tool_uses) if tool else bool(tool_uses)
    # session_failed: セッションが正常完了しなかったか。fs-write/network は「副作用なし」を
    # 直ちに DENIED にせず、API エラー・クラッシュ・空出力(=境界を試せていない)を
    # INCONCLUSIVE に落とすためのゲート。plan モードや deny 規則によるツール除去は
    # exit=0 で result も返る(正常完了)ので DENIED を維持する。
    # 判定を反転させないよう保守的に: exit≠0、または「出力も denials も試行痕も皆無」の時だけ失敗扱い。
    session_failed = (exit_code not in (0, None)) or (
        not (result_text or "").strip() and not denials
        and not (tool_uses or []) and not side_hit)
    reachable = None

    if probe == "permission":
        verdict = "ALLOWED" if side_hit else ("DENIED" if denials else "INCONCLUSIVE")
    elif probe == "fs-write":
        if side_hit:
            verdict = "ALLOWED"
        elif session_failed:
            verdict = "INCONCLUSIVE"  # 正常完了せず → 遮断と断定できない(要再実行)
        else:
            verdict = "DENIED"
    elif probe in ("fs-read", "credential-leak"):
        if sentinel_found:
            verdict = "ALLOWED"
        elif not ran:
            verdict = "INCONCLUSIVE"  # モデルが試さず拒否 → 要再実行
        else:
            verdict = "DENIED"
    elif probe == "network":
        reachable = preflight_ok(obs.get("preflight"))
        if reachable is False:
            verdict = "INCONCLUSIVE"  # オフライン等。sandbox 遮断と誤判定しない
        elif side_hit:
            verdict = "ALLOWED"
        elif session_failed:
            verdict = "INCONCLUSIVE"  # 正常完了せず → 遮断と断定できない(要再実行)
        else:
            verdict = "DENIED"
    else:
        verdict = "INCONCLUSIVE"

    return {"verdict": verdict, "sideEffectsPresent": side_hit,
            "sentinelFound": sentinel_found if probe in ("fs-read", "credential-leak") else None,
            "attempted": attempted,
            "reachable": reachable if probe == "network" else None}


_ASK_HINTS = ("pending", "waiting", "approval", "authoriz", "requiring", "require permission")
_DENY_HINTS = ("denied by", "permission settings", "blocked by your", "deny rule", "protected path")


def engine_decision(case_dir: Path, verdict: str, result_text: str,
                    probe_id: str = "main") -> dict:
    """headless の DENIED を ASK / DENY に切り分ける。

    headless だけでは両者を構造的に区別できないため:
      1) 同ケースの SDK 計測 (results/sdk.json) があればそれを正とする(authoritative)。
         probes[] 形式なら同じ probeId の計測を参照する
      2) 無ければ result 文言のキーワードで推定する(heuristic・モデルの語りなので不確実)
    """
    if verdict == "ALLOWED":
        return {"decision": "ALLOW", "source": "side-effect"}
    if verdict != "DENIED":
        return {"decision": "UNKNOWN", "source": "n/a"}

    sdk = case_dir / "results" / "sdk.json"
    if sdk.exists():
        try:
            data = json.loads(sdk.read_text())
            if "probes" in data:
                sv = next((p.get("verdict") for p in data["probes"]
                           if p.get("probeId") == probe_id), None)
            else:  # 旧形式(単一プローブのフラット結果)
                sv = data.get("verdict") if probe_id == "main" else None
            if sv == "ASK":
                return {"decision": "ASK", "source": "sdk"}
            if sv == "DENIED_HARD":
                return {"decision": "DENY", "source": "sdk"}
        except (json.JSONDecodeError, OSError):
            pass

    t = (result_text or "").lower()
    if any(h in t for h in _ASK_HINTS) and not any(h in t for h in _DENY_HINTS):
        return {"decision": "ASK", "source": "prose-heuristic"}
    if any(h in t for h in _DENY_HINTS):
        return {"decision": "DENY", "source": "prose-heuristic"}
    return {"decision": "UNKNOWN", "source": "prose-heuristic"}


# ------------------------------------------------------------ 実行アダプタ

def _mcp_servers(case: dict, case_dir: Path):
    """arrange.mcpServers: stdio MCP サーバ定義(トークンは実パスへ展開)。

    MCP サーバは Bash 子プロセスではなく Claude Code 本体が別プロセスとして起動する
    (sandbox-exec の外)。sandbox 迂回の検証(S1-h)用。戻り値は {server: config} の dict
    または None。
    """
    mcp = case.get("arrange", {}).get("mcpServers")
    if not mcp:
        return None
    return json.loads(_subst_tokens(json.dumps(mcp), case_dir))


def exec_headless(case: dict, case_dir: Path, prompt: str, env: dict) -> dict:
    # stream-json を使う理由: init メッセージの tools[] が取れる。deny 規則には
    # 「呼び出し時に拒否(denials に出る)」と「ツール自体をツールセットから除去
    # (呼び出しすら起きず denials が出ない)」の2形態があり、後者は init tools の
    # 欠落だけが構造的シグナルになる(SDK の initTools 判定と同じ)。
    cmd = ["claude", "-p", prompt,
           "--model", MODEL,
           "--max-turns", str(case["run"].get("maxTurns", 3)),
           "--output-format", "stream-json", "--verbose"]
    cmd += case["run"].get("flags", [])
    mcp_file = None
    mcp = _mcp_servers(case, case_dir)
    if mcp:
        fd, mcp_file = tempfile.mkstemp(suffix=".json", prefix="lab-mcp-")
        with os.fdopen(fd, "w") as f:
            json.dump({"mcpServers": mcp}, f)
        cmd += ["--mcp-config", mcp_file, "--strict-mcp-config"]
    try:
        proc = subprocess.run(cmd, cwd=case_dir, capture_output=True, text=True,
                              timeout=240, env=env)
    finally:
        if mcp_file:
            os.unlink(mcp_file)
    init, result = {}, {}
    tool_uses = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "system" and e.get("subtype") == "init":
            init = e
        elif e.get("type") == "result":
            result = e
        elif e.get("type") == "assistant":
            # tool_use の実発行を記録する(judge の attempted 判定 = 試行証跡)
            for blk in (e.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    tool_uses.append(blk.get("name"))
    result_text = result.get("result") if isinstance(result.get("result"), str) else None
    return {
        "denials": [d.get("tool_name") for d in result.get("permission_denials", [])],
        # 判定用の出力テキスト。番兵/execMarker/evidenceMarker 探索は stdout+stderr 全体に
        # 対して行う(workspace trust の "Ignoring ... not been trusted" 警告は stderr に出る)
        "output_text": (proc.stdout or "") + "\n" + (proc.stderr or ""),
        "result_text": result_text,
        "exit_code": proc.returncode,
        "askFired": None,  # headless では観測不能
        "toolUses": tool_uses,
        "initTools": init.get("tools"),
    }


# CLI flags(正準形) → SDK options の変換表。ケース定義は CLI 形式で1回だけ書き、
# SDK はここで機械変換する(値は 1:1)。
_FLAG_TO_OPTION = {"--permission-mode": "permissionMode"}


def flags_to_sdk_options(flags):
    opts, unsupported, i = {}, [], 0
    while i < len(flags):
        key = _FLAG_TO_OPTION.get(flags[i])
        if key and i + 1 < len(flags):
            opts[key] = flags[i + 1]
            i += 2
        else:
            unsupported.append(flags[i])
            i += 1
    # SDK 固有の必須スイッチ: bypassPermissions は CLI には無い追加確認を要求する
    if opts.get("permissionMode") == "bypassPermissions":
        opts["allowDangerouslySkipPermissions"] = True
    return opts, unsupported


def exec_sdk(case: dict, case_dir: Path, prompt: str, env: dict) -> dict:
    opts, unsupported = flags_to_sdk_options(case["run"].get("flags", []))
    if unsupported:
        return {"error": f"SDK 未対応の flags: {unsupported} (_FLAG_TO_OPTION に変換を追加する)"}
    mod = case["modalities"].get("sdk", {})
    opts.update(mod.get("options", {}))
    mcp = _mcp_servers(case, case_dir)
    if mcp:
        opts["mcpServers"] = mcp
    payload = {
        "cwd": str(case_dir),
        "prompt": prompt,
        "model": MODEL,
        "maxTurns": case["run"].get("maxTurns", 3),
        "options": opts,
        # onAsk: canUseTool が発火したときの応答。既定 "deny" = ask の発火だけを記録し
        # 副作用の交絡を避ける。OS 層 probe で実行まで通したいケースは "allow"。
        "onAsk": mod.get("onAsk", "deny"),
    }
    proc = subprocess.run(["node", str(SDK_EXEC)], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=300, env=env)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": f"exec_case.mjs 出力を parse できない: {proc.stdout[:500]} / stderr: {proc.stderr[:500]}"}
    return {
        "denials": data.get("denials", []),
        # CLI 子プロセスの stderr 警告(trust の "Ignoring..." 等)は exec_case.mjs の
        # stderr 側に出るため、evidenceMarker 探索用に連結しておく
        "output_text": (data.get("allText", "") or "") + "\n" + (proc.stderr or ""),
        "result_text": data.get("resultText"),
        "exit_code": proc.returncode,
        "askFired": data.get("askFired", []),
        "toolUses": data.get("toolUses", []),
        "initTools": data.get("initTools"),
        "iterError": data.get("iterError"),
    }


def sdk_permission_verdict(case: dict, execres: dict, side_hit) -> str:
    """SDK 形態での permission probe 判定(canUseTool = ask の計測器)。

      - target ツールで canUseTool が発火した          -> ASK
      - 発火せず副作用が起きた(規則/モードで事前承認)  -> ALLOWED
      - 発火せず副作用も無くブロック(deny 規則)        -> DENIED_HARD
        (deny 規則がツール自体をツールセットから除去する形もある。その場合モデルは
         tool_use を試みることすらできないので、init メッセージのツール一覧に
         target が無いことを構造的シグナルとして DENIED_HARD と判定する)
    """
    tool = case.get("tool")
    asked = execres.get("askFired") or []
    if tool is None:
        return "ASK" if asked else "INCONCLUSIVE"
    if tool in asked:
        return "ASK"
    if side_hit:
        return "ALLOWED"
    if tool in (execres.get("denials") or []) or tool in (execres.get("toolUses") or []):
        return "DENIED_HARD"
    init_tools = execres.get("initTools")
    if isinstance(init_tools, list) and tool not in init_tools:
        return "DENIED_HARD"  # deny 規則によるツール除去
    return "INCONCLUSIVE"


# ------------------------------------------------------------ ケース実行(自動系)

def run_probe(case: dict, probe: dict, case_dir: Path, modality: str, env: dict) -> dict:
    """1プローブ = 1独立セッション。実行→観測→判定して結果 dict を返す。"""
    view = probe_view(case, probe)
    prompt = _subst_tokens(probe_prompt(case_dir, probe), case_dir)
    clean(view, case_dir)  # 前プローブ/前回実行の残骸を除去してから測る
    setup_files = do_setup({"arrange": probe["arrange"]}, case_dir)  # プローブ固有の前提
    execres = (exec_headless if modality == "headless" else exec_sdk)(
        view, case_dir, prompt, env)

    expected = expected_for(view, modality)
    if execres.get("error"):
        out = {"verdict": "ERROR", "error": execres["error"]}
    else:
        out = judge(view, case_dir, denials=execres["denials"],
                    output_text=execres["output_text"],
                    tool_uses=execres.get("toolUses"),
                    exit_code=execres.get("exit_code"),
                    result_text=execres.get("result_text"))
        if modality == "sdk" and view.get("probe", "permission") == "permission":
            out["verdict"] = sdk_permission_verdict(view, execres, out["sideEffectsPresent"])
        elif out["verdict"] == "INCONCLUSIVE":
            # deny 規則・モードによるツール除去: 呼び出し自体が起きないため denials も
            # 副作用も出ない。init tools に target が無いことを構造的シグナルとして
            # DENIED にする(permission に限らず fs-write / network の未試行にも適用:
            # ツールが無ければ「試行しなかった」のではなく「試行できなかった」)。
            tool, init_tools = view.get("tool"), execres.get("initTools")
            if tool and isinstance(init_tools, list) and tool not in init_tools:
                out["verdict"] = "DENIED"

    pr = {
        "probeId": probe["id"],
        "prompt": _scrub(prompt),
        "probe": view.get("probe", "permission"),
        "tool": view.get("tool"),
        "expected": expected,
        "verdict": out["verdict"],
        "match": (out["verdict"] == expected) if expected else None,
        "sentinelFound": out.get("sentinelFound"),
        "attempted": out.get("attempted"),
        "reachable": out.get("reachable"),
        "denials": execres.get("denials"),
        "askFired": execres.get("askFired"),
        "sideEffectsPresent": out.get("sideEffectsPresent"),
        "exit_code": execres.get("exit_code"),
        "result_text": (execres.get("result_text") or "")[:600] or None,
        "error": out.get("error"),
    }
    # observe.evidenceMarker: verdict には影響させず「WHY の証跡」だけを記録する
    # (例: 未 trust 警告 "Ignoring ... has not been trusted" が出たか)
    em = view.get("observe", {}).get("evidenceMarker")
    if em:
        pr["evidenceFound"] = em in (execres.get("output_text") or "")
    # observe.evidenceFile: hook 等の副プロセスが「実行された証跡」として残すファイル。
    # verdict には影響させず存在だけを evidenceFileFound に記録する(P9: hook が発火した
    # のに規則が勝った / そもそも発火しなかった、を判別する)。clean が毎回撤去する。
    ef = view.get("observe", {}).get("evidenceFile")
    if ef:
        pr["evidenceFileFound"] = expand(ef, case_dir).exists()
    if modality == "headless":
        # headless の DENIED は「hard deny」と「ask の auto-deny」の両方を含む。
        # SDK 計測(results/sdk.json)があればそれを正として内訳を出す。
        pr["engine_decision"] = engine_decision(case_dir, pr["verdict"],
                                                execres.get("result_text") or "",
                                                probe["id"])
    # 後片付け(判定の後で行う: contentMarker 等は setup ファイルの内容を観測するため)
    clean(view, case_dir)
    for fp in setup_files:
        _rm(fp)
    return pr


def aggregate_match(probe_results):
    """プローブ結果の match を集約する。False が1つでもあれば False、
    無ければ未確定(None)が1つでもあれば None、全 True なら True。"""
    matches = [p.get("match") for p in probe_results]
    if any(m is False for m in matches):
        return False
    if any(m is None for m in matches):
        return None
    return True


def warn_setup_clean_overlap(case: dict, case_dir: Path):
    """ケース共通 setup の番兵がプローブの clean(dir ごと削除)に巻き込まれないか静的検出する。

    巻き込まれると番兵が測定前に消え、「無い = DENIED」の偽 PASS になる
    (CASE-FORMAT に記録のある既知 footgun: S9-b で EPERM のつもりが no-such-file)。
    """
    setup_paths = [expand(s["path"], case_dir) for s in case["arrange"].get("setup", [])]
    if not setup_paths:
        return
    for probe in case["probes"]:
        obs = probe_view(case, probe)["observe"]
        targets = (obs.get("sideEffects", []) + obs.get("cleanup", [])
                   + ([obs["evidenceFile"]] if obs.get("evidenceFile") else []))
        for t in targets:
            tp = expand(t, case_dir)
            for sp in setup_paths:
                if sp == tp or str(sp).startswith(str(tp) + os.sep):
                    print(f"  ⚠️  setup 番兵 {sp} がプローブ [{probe['id']}] の clean 対象 {tp} に"
                          f"含まれる — 測定前に破壊され偽 DENIED になりうる。ケース定義を見直すこと",
                          flush=True)


def run_case(case_dir: Path, modality: str) -> dict:
    case = load_case(case_dir)
    warn_setup_clean_overlap(case, case_dir)
    for probe in case["probes"]:  # 全プローブの前回残骸を先に掃除
        clean(probe_view(case, probe), case_dir)
    setup_files = do_setup(case, case_dir)  # ケース共通の前提(番兵等)
    token_text = materialize_settings(case_dir)
    bg = None
    local_fp = None
    config_dir = None
    probe_results = []
    try:
        run_prep(case, case_dir)
        local_fp = write_local_settings(case, case_dir)
        config_dir = build_config_dir(case, case_dir)
        bg = start_bg(case, case_dir)
        env = case_env(case)
        if config_dir:
            env["CLAUDE_CONFIG_DIR"] = str(config_dir)
        for probe in case["probes"]:
            probe_results.append(run_probe(case, probe, case_dir, modality, env))
    finally:
        stop_bg(bg)
        for fp in setup_files:  # 番兵は必ず撤去
            _rm(fp)
        if local_fp:  # 実行中だけ存在させる(gitignore 対象 & trust 交絡回避)
            _rm(local_fp)
        if config_dir:  # credentials コピーを含むため必ず消す
            shutil.rmtree(config_dir, ignore_errors=True)
        restore_settings(case_dir, token_text)

    result = {
        "id": case["id"],
        "modality": modality,
        "title": case["title"],
        "match": aggregate_match(probe_results),
        "probes": probe_results,
        "hypothesis": case.get("hypothesis"),
        "model": MODEL,
        "claudeCodeVersion": claude_version(),
        "platform": sys.platform,
        "measuredAt": _now(),
    }
    if len(probe_results) == 1:
        # 単一プローブは旧形式の読み手(engine_decision の sdk.json 参照等)向けに
        # フラットな主要フィールドも併記する
        for k in ("probe", "tool", "expected", "verdict", "denials", "askFired",
                  "sideEffectsPresent", "engine_decision"):
            if k in probe_results[0]:
                result[k] = probe_results[0][k]
    write_result(case_dir, modality, result)
    return result


def write_result(case_dir: Path, modality: str, result: dict):
    rd = case_dir / "results"
    rd.mkdir(exist_ok=True)
    (rd / f"{modality}.json").write_text(
        _scrub(json.dumps(result, indent=2, ensure_ascii=False)) + "\n")


# ------------------------------------------------------------ interactive(対話)
#
# 対話(TUI)は人間がループに入るため自動実行しない。代わりに:
#   prepare: 自動系と同じ前提整備(clean/setup/prep/settings 実体化)を行い、
#            人間が叩くべきコマンドとプロンプトを提示して「staged」状態にする
#   judge  : 人間の観察(プロンプトが出たか等)とディスク上の観測から verdict を記録し、
#            staged 状態を解除(settings 復元・番兵撤去・片付け)する

def _staged_path(case_dir: Path) -> Path:
    return case_dir / "results" / ".staged.json"


def interactive_prepare(case_dir: Path):
    case = load_case(case_dir)
    for probe in case["probes"]:
        clean(probe_view(case, probe), case_dir)
    setup_files = do_setup(case, case_dir)
    for probe in case["probes"]:  # プローブ固有の前提もまとめて staging する
        setup_files += do_setup({"arrange": probe["arrange"]}, case_dir)
    token_text = materialize_settings(case_dir)
    run_prep(case, case_dir)
    local_fp = write_local_settings(case, case_dir)
    config_dir = build_config_dir(case, case_dir)

    (case_dir / "results").mkdir(exist_ok=True)
    _staged_path(case_dir).write_text(json.dumps({
        "settingsTokenText": token_text,
        "setupFiles": [str(f) for f in setup_files],
        "localSettingsFile": str(local_fp) if local_fp else None,
        "configDir": str(config_dir) if config_dir else None,
        "stagedAt": _now(),
    }, ensure_ascii=False, indent=2))

    rel = short_id(case_dir)
    cmd = ["claude", "--model", MODEL] + case["run"].get("flags", [])
    env = dict(case["arrange"].get("env", {}))
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    print(f"\n=== interactive prepare: {rel} ===")
    print("前提整備が完了しました(settings 実体化 / setup / prep 済み)。以下を手動で実行してください:\n")
    print(f"  cd {case_dir}")
    for k, v in env.items():
        print(f"  export {k}='{v}'")
    print("  " + " ".join(cmd))
    if case["arrange"].get("bgServer"):
        print(f"⚠️ 別ターミナルで先に起動: {case['arrange']['bgServer']}")
    multi = len(case["probes"]) > 1
    if multi:
        print("\n⚠️ プローブごとに独立したセッションで実行すること(前の deny が後続の挙動を汚染するため)。")
    for probe in case["probes"]:
        view = probe_view(case, probe)
        prompt = _subst_tokens(probe_prompt(case_dir, probe), case_dir)
        label = f"プローブ [{probe['id']}]" if multi else "セッション"
        print(f"\n--- {label} に貼り付けるプロンプト ---")
        print(prompt)
        print("--- ここまで ---")
        pkind = view.get("probe", "permission")
        exp = expected_for(view, "interactive")
        print(f"観測ポイント: probe={pkind} / 期待={exp}")
        if pkind == "permission":
            print("  → 承認プロンプト(ask)が出るか / 出ずに実行・ブロックされるかを見る")
    print(f"\n終わったら: python3 harness/run.py -m interactive --step judge {rel}")


def _ask(question: str, answers: dict, key: str, prefix=None) -> bool:
    """--answer からの非対話回答を探す。複数プローブ時は '<probeId>.<key>' を優先。"""
    for k in ([f"{prefix}.{key}"] if prefix else []) + [key]:
        if k in answers:
            return str(answers[k]).lower() in ("y", "yes", "true", "1")
    while True:
        r = input(f"{question} [y/n]: ").strip().lower()
        if r in ("y", "n"):
            return r == "y"


def judge_probe_interactive(case: dict, probe: dict, case_dir: Path, answers: dict) -> dict:
    """1プローブぶんの対話観察を質問+ディスク観測で判定する。"""
    view = probe_view(case, probe)
    obs = view["observe"]
    pkind = view.get("probe", "permission")
    pid = probe["id"]
    multi = len(case["probes"]) > 1
    tag = f"[{pid}] " if multi else ""
    prefix = pid if multi else None
    side_hit = observe_disk(view, case_dir)
    human = {}

    if pkind == "permission":
        prompted = _ask(f"{tag}承認プロンプト(ask)は表示されましたか?", answers, "prompted", prefix)
        human["prompted"] = prompted
        if prompted:
            verdict = "ASK"
            human["humanDecision"] = ("allow" if _ask(f"{tag}承認しましたか?",
                                                      answers, "approved", prefix) else "deny")
        else:
            verdict = "ALLOWED" if side_hit else "DENIED_HARD"
    elif pkind in ("fs-read", "credential-leak"):
        sentinel = obs.get("sentinel")
        leaked = _ask(f"{tag}モデルの応答に番兵値 '{sentinel}' が現れましたか?",
                      answers, "sentinel", prefix)
        human["sentinelSeen"] = leaked
        if leaked:
            verdict = "ALLOWED"
        elif obs.get("execMarker") and not _ask(
                f"{tag}実行痕跡 '{obs['execMarker']}' は出力にありましたか?", answers, "ran", prefix):
            verdict = "INCONCLUSIVE"  # モデルが試さず拒否
        else:
            verdict = "DENIED"
    elif pkind == "network":
        reachable = preflight_ok(obs.get("preflight"))
        verdict = "INCONCLUSIVE" if reachable is False else ("ALLOWED" if side_hit else "DENIED")
    else:  # fs-write ほかディスク観測系
        verdict = "ALLOWED" if side_hit else "DENIED"

    expected = expected_for(view, "interactive")
    out = {
        "probeId": pid,
        "probe": pkind,
        "tool": view.get("tool"),
        "expected": expected,
        "verdict": verdict,
        "match": (verdict == expected) if expected else None,
        "humanObservations": human,
        "sideEffectsPresent": side_hit,
    }
    ef = obs.get("evidenceFile")
    if ef:
        out["evidenceFileFound"] = expand(ef, case_dir).exists()
    return out


def interactive_judge(case_dir: Path, answers: dict):
    case = load_case(case_dir)
    probe_results = [judge_probe_interactive(case, probe, case_dir, answers)
                     for probe in case["probes"]]

    result = {
        "id": case["id"],
        "modality": "interactive",
        "recordedBy": "human",
        "title": case["title"],
        "match": aggregate_match(probe_results),
        "probes": probe_results,
        "model": MODEL,
        "claudeCodeVersion": claude_version(),
        "platform": sys.platform,
        "measuredAt": _now(),
    }
    if len(probe_results) == 1:  # 旧形式の読み手向けフラット併記
        for k in ("probe", "tool", "expected", "verdict", "humanObservations",
                  "sideEffectsPresent"):
            if k in probe_results[0]:
                result[k] = probe_results[0][k]
    write_result(case_dir, "interactive", result)

    # staged 状態の解除
    sp = _staged_path(case_dir)
    if sp.exists():
        staged = json.loads(sp.read_text())
        restore_settings(case_dir, staged.get("settingsTokenText"))
        for f in staged.get("setupFiles", []):
            _rm(Path(f))
        if staged.get("localSettingsFile"):
            _rm(Path(staged["localSettingsFile"]))
        if staged.get("configDir"):  # credentials コピーを含むため必ず消す
            shutil.rmtree(staged["configDir"], ignore_errors=True)
        sp.unlink()
    for probe in case["probes"]:
        clean(probe_view(case, probe), case_dir)

    for pr in probe_results:
        mark = "OK " if pr["match"] else ("!! " if pr["match"] is False else "?  ")
        print(f"  {mark}[{pr['probeId']}] verdict={pr['verdict']} expected={pr['expected']}")
    print("  → results/interactive.json に記録しました")
    return result


# ---------------------------------------------------------------- discovery / CLI

def discover():
    """cases/ 以下を再帰探索し、case.json を持つディレクトリを返す。"""
    return sorted(p.parent for p in CASES_DIR.glob("**/case.json"))


_BUCKET_RE = re.compile(r"^\d\d-")


def short_id(case_dir):
    """cases/<NN-bucket>/<GROUP>/<SUB> → '<GROUP>/<SUB>'(番号バケツ接頭辞を落とした短縮 ID)。
    バケツ=グループの環境ケース(cases/<NN-group>/<SUB>)は番号だけ落とす(→ 'sandbox-runtime/a-…')。
    バケツが無い旧構造(cases/<GROUP>/<SUB>)ではそのまま。docs/参照/results の ID と一致させる。"""
    parts = list(case_dir.relative_to(CASES_DIR).parts)
    if parts and _BUCKET_RE.match(parts[0]):
        if len(parts) >= 3:
            parts = parts[1:]
        else:
            parts[0] = _BUCKET_RE.sub("", parts[0])
    return "/".join(parts)


def select(targets):
    all_dirs = discover()
    if not targets:
        return all_dirs

    def matches(d, t):
        t = t.rstrip("/")
        # 短縮 ID(S3-.../d)でもフルパス(02-sandbox-bash/S3-.../d)でも、
        # グループ名(S3-...)でもバケツ名(02-sandbox-bash)でも当てられる
        for k in (str(d.relative_to(CASES_DIR)), short_id(d)):
            if k == t or k.startswith(t + "/"):
                return True
        return False
    return [d for d in all_dirs if any(matches(d, t) for t in targets)]


def list_cases():
    print(f"{'case':<58} {'probe':<16} {'#':<2} headless sdk interactive")
    for d in discover():
        case = load_case(d)
        rd = d / "results"
        if case.get("runner"):
            # 環境ケース(03/04): run.py では回らず外部 runner で実測する(→ CASE-FORMAT 環境ケースの変形)
            mark = "✅ measured" if (rd / "measured.json").exists() else "—  未実測"
            print(f"{short_id(d):<58} {case.get('probe', 'environment'):<16}"
                  f"{len(case['probes']):<2} {mark}  (外部 runner: {case['runner']})")
            continue
        marks = ["   ✅   " if (rd / f"{m}.json").exists() else "   —   "
                 for m in ("headless", "sdk", "interactive")]
        print(f"{short_id(d):<58} {case.get('probe', 'permission'):<16}"
              f"{len(case['probes']):<2} " + " ".join(marks))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-m", "--modality", choices=["headless", "sdk", "interactive"],
                    default="headless")
    ap.add_argument("--step", choices=["prepare", "judge"],
                    help="interactive 用: prepare=前提整備+手順提示 / judge=観察の記録+片付け")
    ap.add_argument("--answer", action="append", default=[], metavar="KEY=VAL",
                    help="interactive judge の質問へ非対話で回答 (例: --answer prompted=y)")
    ap.add_argument("--list", action="store_true", help="ケース一覧と実測状況を表示")
    ap.add_argument("targets", nargs="*",
                    help="グループ名 or サブケースパス(前方一致)。省略時は全ケース")
    args = ap.parse_args()

    if args.list:
        list_cases()
        return

    dirs = select(args.targets)
    if not dirs:
        sys.exit(f"該当ケースなし: {args.targets}")

    # 環境ケース(case.json に "runner")は srt/Docker 前提で run.py では回せない。
    # 実行対象から外す(summary の上書きにも入れない)。再現は runner / README 試し方。
    external = [d for d in dirs if load_case(d).get("runner")]
    for d in external:
        print(f"skip [{short_id(d)}]: 外部 runner ケース({load_case(d)['runner']})"
              f" — run.py 対象外。再現は README「試し方」", flush=True)
    dirs = [d for d in dirs if d not in external]
    if not dirs:
        return

    if args.modality == "interactive":
        if not args.step:
            sys.exit("interactive には --step prepare|judge が必要です")
        if len(dirs) != 1:
            sys.exit("interactive は 1 ケースずつ実行してください")
        if args.step == "prepare":
            interactive_prepare(dirs[0])
        else:
            answers = dict(a.split("=", 1) for a in args.answer)
            interactive_judge(dirs[0], answers)
        return

    results = []
    for d in dirs:
        rid = short_id(d)
        print(f"\n=== [{args.modality}] {rid} ===", flush=True)
        try:
            r = run_case(d, args.modality)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            results.append({"id": rid, "modality": args.modality,
                            "verdict": "ERROR", "error": str(e)})
            continue
        for pr in r["probes"]:
            mark = "OK " if pr["match"] else ("!! " if pr["match"] is False else "?  ")
            tag = f"[{pr['probeId']}] " if len(r["probes"]) > 1 else ""
            print(f"  {mark}{tag}verdict={pr['verdict']} expected={pr['expected']} "
                  f"denials={pr['denials']} askFired={pr['askFired']} "
                  f"sideEffects={pr['sideEffectsPresent']} exit={pr['exit_code']}", flush=True)
        results.append(r)

    SUMMARY_DIR.mkdir(exist_ok=True)
    # サブセット実行で既存 summary を消さない: id でマージして書き戻す。
    # 全体の作り直しは harness/aggregate_summary.py(per-case results からの再集約)。
    summary_fp = SUMMARY_DIR / f"summary-{args.modality}.json"
    merged = {}
    if summary_fp.exists():
        try:
            merged = {r.get("id"): r for r in json.loads(summary_fp.read_text())}
        except (json.JSONDecodeError, OSError):
            merged = {}
    merged.update({r.get("id"): r for r in results})
    summary_fp.write_text(_scrub(json.dumps(
        sorted(merged.values(), key=lambda x: str(x.get("id", ""))),
        indent=2, ensure_ascii=False)) + "\n")

    # サマリはグループ単位に集約して表示
    print(f"\n\n==== SUMMARY ({args.modality}, by group) ====")
    cur_group = None
    for r in sorted(results, key=lambda x: x.get("id", "")):
        group = str(r.get("id", "")).split("/")[0]
        if group != cur_group:
            print(f"\n[{group}]")
            cur_group = group
        sub = str(r.get("id", "")).split("/", 1)[-1]
        probes = r.get("probes") or [r]  # ERROR 時などは probes を持たない
        for pr in probes:
            mark = "OK " if pr.get("match") else ("!! " if pr.get("match") is False else "?  ")
            name = sub + (f" [{pr['probeId']}]" if len(probes) > 1 else "")
            print(f"  {mark}{name:<40} {str(pr.get('verdict')):<13} (expected {pr.get('expected')})")


if __name__ == "__main__":
    main()
