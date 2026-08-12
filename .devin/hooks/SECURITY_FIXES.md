# Security Fixes — Devin CLI Hook Logging Scripts

**Audit date:** 2026-07-07
**Branch:** feature/monitoring-integration
**Pre-fix checkpoint tag:** pre-hook-security-fixes
**Pre-fix HEAD (committed):** c3de4408316dbd2fc5b0798eb6fd3cb163eff439
**Baseline captured:** 2026-07-08T15:50:56Z

## Pre-Fix Baseline

### Committed State (at tag `pre-hook-security-fixes`)
- `log_exec.py`: 225c1736654f4d370ac7a76b62c9374ba2f4b04073284c673e0da501e1544e14 (108 lines) — committed version
- `log_permissions.py`: NOT TRACKED in git at baseline (untracked file)
- `export_csv.py`: NOT TRACKED in git at baseline (untracked file)

### On-Disk State (working tree at baseline, post-stash-pop)
| File | SHA256 | Lines | Git Status |
|------|--------|-------|------------|
| .devin/hooks/log_exec.py | a98daad741b4b5e4c4734362ad1fe063b181ab3c555d2239656041b3aeef501f | 142 | modified |
| .devin/hooks/log_permissions.py | 23d5521059e3bce673dca7e45fca472be8ee1d5afcb1ce2ec2b2fbfce10ed6df | 110 | untracked |
| .devin/hooks/export_csv.py | 53063f8151a3cf37eb1bff39c2cc183f42f3126e29d15a5c3b0f74efde645a89 | 133 | untracked |

### Rollback Instructions
To restore the pre-fix state:
```bash
git checkout pre-hook-security-fixes -- .devin/hooks/log_exec.py .devin/hooks.v1.json
# log_permissions.py and export_csv.py were untracked — restore from stash if needed:
# git stash list  # find the stash ref
# git checkout <stash-ref> -- .devin/hooks/log_permissions.py .devin/hooks/export_csv.py
```

## Issues Identified

| # | Severity | Issue | File(s) | Specialist |
|---|----------|-------|---------|------------|
| 2 | CRITICAL | Full tool_input logged (credential leakage) | log_permissions.py | security-auditor |
| 3 | HIGH | Unbounded log growth + O(n²) rewrite | log_exec.py, log_permissions.py | python-reviewer |
| 4 | MEDIUM | World-readable log files (0644) | all three | security-auditor |
| 5 | MEDIUM | CSV formula injection | export_csv.py | security-auditor |
| 6 | MEDIUM | Non-atomic truncate + write | log_exec.py, log_permissions.py | python-reviewer |
| 7 | MEDIUM | Silent failures hide security events | log_exec.py, log_permissions.py | python-reviewer |
| 8 | LOW | Debug log unsanitized + wrong permissions | log_exec.py, log_permissions.py | security-auditor |

## Execution Plan

### Wave 1 (parallel)
- security-auditor → Issue #2 (log_permissions.py: remove tool_input from records)
- python-reviewer → Issue #5 (export_csv.py: CSV formula injection sanitization)

### Wave 2 (parallel)
- python-reviewer → Issues #3+#6+#7 (log_exec.py + log_permissions.py: JSON Lines, atomic writes, error handling)
- security-auditor → Issue #4 (export_csv.py: 0600 file permissions)

### Wave 3 (sequential)
- security-auditor → Issue #4 on log_*.py + Issue #8 (debug log redaction/permissions)

### Verification
- security-auditor re-audits #2, #4, #5, #8
- python-reviewer reviews #3, #6, #7
- testing-guardian adds test coverage

## Fixes Applied

### Wave 1 — Completed 2026-07-08

#### Issue #2 (CRITICAL) — Fixed by `security-auditor`
**File:** `.devin/hooks/log_permissions.py`
**Change:** Removed the `tool_input` field from the log record dict (was line 76). For non-exec tools, the `command` field now logs only `<tool_name>` instead of serializing the full `tool_input` (which could contain entire file contents, private keys, and credentials). Added a `safe_args` field with an allow-list of non-sensitive metadata fields (`file_path`, `shell_id`, `timeout`, `idle_timeout`, `pattern`, `path`), with values truncated to 200 chars.

**Before:**
```python
command = json.dumps(tool_input, ensure_ascii=False)[:2000]
...
"tool_input": tool_input,
```

**After:**
```python
command = f"<{tool_name}>"
...
"safe_args": safe_args if safe_args else None,
```

**Verification:** Syntax OK (`ast.parse`). Only `log_permissions.py` modified.
**Post-fix checksum:** `d66df31f92207c0b87ce9a22a7be0850fa7cffaef5927ec16d16956d86c45506` (131 lines)

---

#### Issue #5 (MEDIUM) — Fixed by `python-reviewer`
**File:** `.devin/hooks/export_csv.py`
**Change:** Added a `_sanitize_csv()` helper function that prefixes dangerous leading characters (`=`, `+`, `-`, `@`, tab, CR) with a single quote to prevent spreadsheet formula injection. Both `export_permissions()` and `export_exec()` now sanitize every field value before writing to CSV.

**Before:**
```python
writer.writerow(r)
```

**After:**
```python
writer.writerow({k: _sanitize_csv(r.get(k)) for k in fields})
```

**Verification:** Syntax OK (`ast.parse`). Sanitization tests passed (`=CMD` → `'=CMD`, `@SUM` → `'@SUM`, `normal` → `normal`, `None` → ``, `123` → `123`). Only `export_csv.py` modified.
**Post-fix checksum:** `83cc2f1c2a8c1cbd93ff1bccda6f6972f63049f39cd031d76a3625730b25e1f2` (147 lines)

---

### Wave 2 — Completed 2026-07-08

#### Issues #3+#6+#7 (HIGH+MEDIUM+MEDIUM) — Fixed by `python-reviewer`
**Files:** `.devin/hooks/log_exec.py` + `.devin/hooks/log_permissions.py`
**Change:** Combined refactoring of the write loop in both log scripts. Replaced the O(n²) JSON-array read/parse/append/truncate/rewrite pattern with append-only JSON Lines writes. Added 10MB size-capped log rotation (keeping one `.1` backup). Fixed silent failure on `json.JSONDecodeError` — now prints diagnostics to stderr and returns exit code 1.

**Before (both files):**
```python
except json.JSONDecodeError:
    return 0  # silent failure

# 25-27 line block: open("a+"), seek(0), read(), json.loads(),
# append, truncate(), json.dump() — O(n²), non-atomic
```

**After (both files):**
```python
except json.JSONDecodeError as e:
    print(f"devin hook: invalid JSON on stdin: {e}", file=sys.stderr)
    return 1

# O(1) atomic append:
try:
    _append_record(log_path, record)
except Exception as e:
    print(f"devin hook: failed to write audit record: {e}", file=sys.stderr)
    return 1
```

**New helpers added to both files:**
- `MAX_LOG_BYTES = 10 * 1024 * 1024` — 10MB rotation cap
- `_rotate_if_needed(path)` — renames to `.1` backup when size exceeded
- `_append_record(path, record)` — atomic single-line JSON append under file lock

**Verification:**
- Syntax OK for both files
- JSON Lines append test: PASS (2 lines, correct content)
- Rotation test: PASS (file renamed to `.1`)
- Bad stdin JSON → exit 1 + stderr: PASS
- End-to-end valid events: PASS
- `export_csv.py` JSON Lines compatibility: Confirmed (fallback parser intact)
- Wave 1 changes to `log_permissions.py` intact: `safe_args` present, `tool_input` removed

**Post-fix checksums:**
- `log_exec.py`: `2e3069d3b871687144b51fb67077c9312bdc9a0c15448a9ce14e716a3428ee99` (144 lines)
- `log_permissions.py`: `22edad1fade060c5374e0f4c21f79c857658ab0288bc1edd90d11e605b347b7b` (134 lines)

---

#### Issue #4 (MEDIUM) — Fixed by `security-auditor`
**File:** `.devin/hooks/export_csv.py`
**Change:** Added `_ensure_private_perms()` helper that sets file permissions to `0600` (owner read/write only). Both `export_permissions()` and `export_exec()` now call it pre-write (for existing files) and post-write (for newly created files), ensuring CSV output is never world-readable.

**Before:**
```python
# No permission management — files created with umask (typically 0644)
```

**After:**
```python
def _ensure_private_perms(path: Path) -> None:
    """Set file permissions to 0600 (owner read/write only)."""
    try:
        path.chmod(0o600)
    except OSError:
        pass

# Pre-write and post-write calls in both export functions
if out.exists():
    _ensure_private_perms(out)
# ... write CSV ...
_ensure_private_perms(out)
```

**Verification:** Syntax OK. Permission test: PASS (file mode verified as `0o600`). Only `export_csv.py` modified.
**Post-fix checksum:** `fa534445e048a7cbb29b1bce6baeb5e3b2ddb863add3d287aa0bb911229825f0` (166 lines)

---

### Wave 3 — Completed 2026-07-08

#### Issue #4 (MEDIUM) on log scripts — Fixed by `security-auditor`
**Files:** `.devin/hooks/log_exec.py` + `.devin/hooks/log_permissions.py`
**Change:** Added `_ensure_private_perms()` helper to both log scripts. Called pre-write (tightens existing file) and post-write (ensures newly created file is private) inside `_append_record()`. Log files now created/maintained with `0600` permissions.

**Before:**
```python
# No permission management — files created with umask (typically 0644)
def _append_record(path, record):
    _rotate_if_needed(path)
    line = json.dumps(record, ...) + "\n"
    with path.open("a", ...) as f, _file_lock(f):
        f.write(line)
```

**After:**
```python
def _ensure_private_perms(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass

def _append_record(path, record):
    _rotate_if_needed(path)
    _ensure_private_perms(path)  # pre-write
    line = json.dumps(record, ...) + "\n"
    with path.open("a", ...) as f, _file_lock(f):
        f.write(line)
    _ensure_private_perms(path)  # post-write
```

---

#### Issue #8 (LOW) — Fixed by `security-auditor`
**Files:** `.devin/hooks/log_exec.py` + `.devin/hooks/log_permissions.py`
**Change:** Added `import re`, `_SECRET_RE` and `_AUTH_BEARER_RE` compiled regex patterns, and `_redact()` helper to both scripts. The debug block (`DEVIN_HOOK_DEBUG`) now: (1) applies `_ensure_private_perms()` pre/post write to `~/.devin-hook-debug.log`, and (2) passes the JSON output through `_redact()` before writing, redacting API keys, passwords, tokens, bearer tokens, and authorization headers.

**Before:**
```python
if os.environ.get("DEVIN_HOOK_DEBUG"):
    debug_path = Path.home() / ".devin-hook-debug.log"
    try:
        with debug_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n---\n")
    except Exception:
        pass
```

**After:**
```python
if os.environ.get("DEVIN_HOOK_DEBUG"):
    debug_path = Path.home() / ".devin-hook-debug.log"
    try:
        _ensure_private_perms(debug_path)
        redacted = _redact(json.dumps(data, ensure_ascii=False, indent=2))
        with debug_path.open("a", encoding="utf-8") as f:
            f.write(redacted + "\n---\n")
        _ensure_private_perms(debug_path)
    except Exception:
        pass
```

**Verification:** Syntax OK for both files. Redaction tests PASS (`api_key=sk-...` → redacted, `Authorization: Bearer ...` → redacted, normal text unchanged). Permission test PASS (file mode `0o600`). Wave 1 + Wave 2 changes confirmed intact.

**Post-fix checksums:**
- `log_exec.py`: `c8fcedd5c9801e459867c603b485ad5b782ea42650245201767d6a859058835f` (173 lines)
- `log_permissions.py`: `78acf0f85ecf3edbd10eb05e2c56d1c08abbb58698fcd3b73d918d1f3ce09294` (163 lines)

## Verification Results

### Verification Pass — Completed 2026-07-08

Three independent verification sub-agents ran in parallel:

#### Security Re-Audit (security-auditor) — Issues #2, #4, #5, #8
**Verdict: PASS**

| Issue | Verdict | Evidence |
|-------|---------|----------|
| #2 (CRITICAL) | VERIFIED FIXED | `tool_input` field absent from record dict (line 150 comment confirms). Non-exec tools use `f"<{tool_name}>"`. `safe_args` with 6-field allowlist + 200-char truncation. |
| #4 (MEDIUM) | VERIFIED FIXED | `_ensure_private_perms()` present in all 3 files, sets `0o600`, called pre/post write in `_append_record()` and both export functions. `OSError` handled non-fatally. |
| #5 (MEDIUM) | VERIFIED FIXED | `_sanitize_csv()` prefixes `=`, `+`, `-`, `@`, tab, CR with `'`. Both export functions use it. `None` → `""`. |
| #8 (LOW) | VERIFIED FIXED | `_redact()` + `_SECRET_RE` + `_AUTH_BEARER_RE` in both log scripts. Debug block applies redaction + `0600` perms pre/post write. |

**New-issue scan:** No new vulnerabilities introduced. Regex patterns correctly anchored and escaped. All imports present. No residual secret-leakage paths introduced by the fixes.

**Info observations (not blocking):**
- `log_exec.py` logs raw `command`/`output_snippet`/`error_snippet` without `_redact()` — pre-existing design decision for command auditing. Consider applying `_redact()` in a future hardening pass.
- `_AUTH_BEARER_RE` token character class may not cover all JWT characters (`{`, `}`), but `_SECRET_RE` provides fallback coverage.

---

#### Code Review (python-reviewer) — Issues #3, #6, #7
**Verdict: PASS**

| Issue | Verdict | Evidence |
|-------|---------|----------|
| #3 (HIGH) | VERIFIED FIXED | No `json.load()`/`json.dump()`/`truncate()` of log file. `_append_record()` is O(1) single-line append. `_rotate_if_needed()` with `MAX_LOG_BYTES=10MB`, one `.1` backup. |
| #6 (MEDIUM) | VERIFIED FIXED | No `truncate()` or full-array `json.dump()`. Append-only writes are line-atomic. `_file_lock` still used during append. |
| #7 (MEDIUM) | VERIFIED FIXED | `json.JSONDecodeError` → stderr + exit 1. Write failures → stderr + exit 1. No silent `except Exception: pass` on security-relevant paths. |

**Code quality findings (INFO, not blocking):**
- INFO-1: Rotation race condition on backup file (not active log) — acceptable for CLI hook
- INFO-2: `_ensure_private_perms` pre-write call on non-existent file is harmless redundancy
- INFO-3: `_redact()` only used in debug path, not audit record path — design decision
- INFO-4: `default=str` in `json.dumps` is correct safety net
- INFO-5: Code duplication between two log scripts — acceptable for self-contained hooks
- INFO-6: Non-dict `tool_input` edge case — low likelihood (Devin CLI controls schema)
- INFO-7: Bare `dict` type hint — minor
- INFO-8: Import ordering correct

---

#### Test Coverage (testing-guardian) — New test file
**Verdict: PASS (41/41 tests passing)**

**File created:** `tests/test_hook_security.py` (394 lines)

| Test Category | Tests | Status |
|---------------|-------|--------|
| CSV sanitization (`_sanitize_csv`) | 10 | PASS |
| Secret redaction (`_redact`) | 8 | PASS |
| File permissions (`_ensure_private_perms`) | 6 | PASS |
| JSON Lines append (`_append_record`) | 4 | PASS |
| Log rotation (`_rotate_if_needed`) | 3 | PASS |
| End-to-end hook execution | 7 | PASS |
| CSV export integration | 3 | PASS |
| **Total** | **41** | **ALL PASS** |

Test run: `.venv/bin/pytest tests/test_hook_security.py -v` → 41 passed in 0.17s

---

## Post-Fix State

### Final File Checksums and Line Counts

| File | SHA256 | Lines | Git Status |
|------|--------|-------|------------|
| `.devin/hooks/log_exec.py` | `c8fcedd5c9801e459867c603b485ad5b782ea42650245201767d6a859058835f` | 173 | modified |
| `.devin/hooks/log_permissions.py` | `78acf0f85ecf3edbd10eb05e2c56d1c08abbb58698fcd3b73d918d1f3ce09294` | 163 | untracked |
| `.devin/hooks/export_csv.py` | `fa534445e048a7cbb29b1bce6baeb5e3b2ddb863add3d287aa0bb911229825f0` | 166 | untracked |
| `tests/test_hook_security.py` | `f4c915d6c32f463d1cf2cc24933f8954a6db1dc53640031146001ed393d83cea` | 394 | untracked (new) |
| `.devin/hooks/SECURITY_FIXES.md` | (this file) | — | untracked (new) |

### Issues Resolution Summary

| # | Severity | Issue | Status | Fixed By |
|---|----------|-------|--------|----------|
| 2 | CRITICAL | Full tool_input logged (credential leakage) | **FIXED** | security-auditor |
| 3 | HIGH | Unbounded log growth + O(n²) rewrite | **FIXED** | python-reviewer |
| 4 | MEDIUM | World-readable log files (0644) | **FIXED** | security-auditor |
| 5 | MEDIUM | CSV formula injection | **FIXED** | python-reviewer |
| 6 | MEDIUM | Non-atomic truncate + write | **FIXED** | python-reviewer |
| 7 | MEDIUM | Silent failures hide security events | **FIXED** | python-reviewer |
| 8 | LOW | Debug log unsanitized + wrong permissions | **FIXED** | security-auditor |

### Overall Verdict: **PASS**

All 7 issues (excluding #1 which was out of scope) are fixed, verified by three independent sub-agents, and covered by 41 passing tests. No new vulnerabilities were introduced. The hook logging scripts are ready for commit.
