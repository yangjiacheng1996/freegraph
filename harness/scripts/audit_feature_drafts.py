"""harness/features 提示词初稿的**质量审计器**。

为什么需要它
------------
`harness/features/` 下的每份 Phase 初稿是 `/speckit.specify` 的提示词底稿——
它一旦有错，错误会被复制到该 Phase 的 spec / tasks / 实现里，且**很难在下游被发现**
（因为下游都"照抄"了它）。而本仓库的宪法原则 VIII 要求「结论必须可追溯」。

本脚本把「初稿 ↔ 立项书 §5.2 总表 ↔ Q8 契约清单」的一致性变成**可自动执行**的检查：

1. **覆盖性**：立项书每个 Phase 有且仅有一份初稿；README 行序表覆盖全部初稿；
2. **元信息对齐**：每份初稿的「层 / 依赖 / 行数」与立项书 §5.2 逐项比对；
3. **结构完整性**：10 个必备章节齐全，FR / SC 编号不重复，验收判据 ≥ 3 条；
4. **引用有效性**：引用的契约条目（C1–C27）与 Phase ID 必须真实存在；
5. **陈旧表述扫描**：已落定的决策（砍 Store / D11 批准 / 恢复必须挂 checkpointer /
   新的 totals）不得以旧措辞残留。

用法
----
    python harness/scripts/audit_feature_drafts.py     # 退出码 0 = 无 ERROR
"""
import pathlib
import re
import sys

ROOT = pathlib.Path('/home/ctyun/workspace/github/freegraph')
FEAT = ROOT / 'harness/features'
CHARTER = ROOT / 'harness/proposals/立项书.md'
Q8 = ROOT / 'harness/reports/Q8-图运行时最小契约.md'

errors, warns = [], []


def err(f, msg):
    errors.append(f"{f.name}: {msg}")


def warn(f, msg):
    warns.append(f"{f.name}: {msg}")


# ───────── 1. 解析立项书 §5.2 总表（权威） ─────────
charter = CHARTER.read_text(encoding='utf-8')
# §5.2 总表列位：Phase | 层 | 跨层 | Feature | 名称 | 里程碑 | 依赖 | 行数 | 小目标 | 人日 | 成本
rows = {}
for line in charter.splitlines():
    if not line.startswith('| F'):
        continue
    c = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(c) < 8 or not re.fullmatch(r'F\d+P\d+', c[0]):
        continue
    rows[c[0]] = {'layer': c[1], 'dep': c[6], 'lines': int(re.sub(r'[^0-9]', '', c[7]))}

# ───────── 2. 解析 README 行序表（开发顺序） ─────────
readme = (FEAT / 'README.md').read_text(encoding='utf-8')
order = []
for line in readme.splitlines():
    m = re.match(r'^\|\s*(\d+)\s*\|\s*\*\*(F\d+P\d+)\*\*\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|', line)
    if m:
        order.append({'step': int(m.group(1)), 'pid': m.group(2), 'label': m.group(3), 'file': m.group(4)})

drafts = sorted(FEAT.glob('F*.md'))
draft_ids = {p.name.split('_')[0]: p for p in drafts}

# ───────── 3. 覆盖性：每个 Phase 有且仅有一个初稿 ─────────
if set(draft_ids) != set(rows):
    for miss in sorted(set(rows) - set(draft_ids)):
        err(draft_ids.get(list(draft_ids)[0], FEAT / 'x'), f"缺少初稿：{miss}")
    for extra in sorted(set(draft_ids) - set(rows)):
        err(draft_ids[extra], "初稿无对应立项书 Phase 行（可能已砍）")

# ───────── 4. README 行序 vs 立项书行序 ─────────
order_ids = [o['pid'] for o in order]
if len(order_ids) != len(set(order_ids)):
    err(FEAT / 'README.md', "行序表存在重复 Phase")
if [o['step'] for o in order] != list(range(1, len(order) + 1)):
    err(FEAT / 'README.md', "行序表的步次不是连续 1..N")
for o in order:
    if o['file'] != o['label']:
        err(FEAT / 'README.md', f"{o['pid']} 链接文本与文件名不一致：{o['label']} vs {o['file']}")
    if not (FEAT / o['file']).exists():
        err(FEAT / 'README.md', f"{o['pid']} 链接指向不存在的文件：{o['file']}")
orphan = set(p.name for p in drafts) - set(o['file'] for o in order)
for o in orphan:
    err(FEAT / 'README.md', f"初稿未进入行序表：{o}")

# ───────── 5. 每份初稿的结构与元信息 vs 立项书 ─────────
REQUIRED = ['### 1. 目标', '### 2. 背景', '### 3. 用户场景', '### 4. 功能需求',
            '### 5. 成功标准', '### 6. 验收判据', '### 7. 关键实体', '### 8. 边界',
            '### 9. 红线与质量门禁', '### 10. 交付物与后续']
for pid, p in sorted(draft_ids.items()):
    t = p.read_text(encoding='utf-8')
    for sec in REQUIRED:
        if sec not in t:
            err(p, f"缺少章节：{sec}")
    # FR / SC 编号连续性
    frs = re.findall(r'\*\*FR-(\d+[a-z]?)\*\*', t)
    if len(frs) < 3:
        err(p, f"功能需求少于 3 条（{len(frs)}）")
    if len(set(frs)) != len(frs):
        err(p, "功能需求编号重复")
    scs = re.findall(r'\*\*SC-(\d+[a-z]?)\*\*', t)
    if len(scs) < 3:
        err(p, f"成功标准少于 3 条（{len(scs)}）")
    if len(set(scs)) != len(scs):
        err(p, "成功标准编号重复")
    # 验收判据表至少 3 条
    ac = t.split('### 6. 验收判据')[1].split('### 7.')[0] if '### 6. 验收判据' in t else ''
    n_ac = len(re.findall(r'^\| A\d+', ac, re.M))
    if n_ac < 3:
        err(p, f"验收判据少于 3 条（{n_ac}）")
    # 元信息 vs 立项书
    if pid in rows:
        r = rows[pid]
        m = re.search(r'\| 规模 \| \*?\*?([\d,]+) 行', t)
        if m and int(m.group(1).replace(',', '')) != r['lines']:
            err(p, f"行数与立项书不符：初稿 {m.group(1)} vs 立项书 {r['lines']:,}")
        lm = re.search(r'\| 架构层 \| ([^|]+?) \|', t)
        if lm:
            layer = lm.group(1).strip()
            if r['layer'].startswith('L') and not layer.startswith(r['layer'][:2]):
                err(p, f"层与立项书不符：初稿 {layer[:20]} vs 立项书 {r['layer']}")
        dm = re.search(r'\| 前置依赖 \| ([^|]+?) \|', t)
        if dm and r['dep'] and r['dep'] != '—':
            deps = set(re.findall(r'F\d+P\d+', dm.group(1)))
            expect = set(re.findall(r'F\d+P\d+', r['dep']))
            if deps != expect:
                err(p, f"依赖与立项书不符：初稿 {deps} vs 立项书 {expect}")

# ───────── 6. 陈旧引用扫描 ─────────
STALE = [
    (r'F17P1', 'F17 已砍（2026-11-05）'),
    (r'D11 未批准|D11 待批|D11 未获批准|D11 未完成|D11 落地前|D11 必须已批准', 'D11 已于 2026-11-05 批准'),
    (r'31,520 行', '旧行数（已砍 F17 → 30,600）'),
    (r'32 个 Phase|32 Phase', '旧 Phase 数（→ 31）'),
    (r'192,000 元', '旧报价（→ 186,000）'),
    (r'96 人日', '旧人日（→ 93）'),
    (r'96 天', '旧工期（→ 94 天）'),
    (r'(?<!MUST NOT )提供「不挂 checkpointer 也能恢复」|不得静默降级为\s*$', '恢复必须挂 checkpointer（2026-11-05 决议）'),
    (r'待发起者拍板|⏳', '决策已全部落定'),
    (r'契约层是否物理拆成独立发行包待|是否改 Apache-2.0 待决', 'D1/D3 已决'),
]
for p in sorted(drafts) + [FEAT / 'README.md']:
    t = p.read_text(encoding='utf-8')
    for pat, why in STALE:
        for m in re.finditer(pat, t):
            line = t[:m.start()].count('\n') + 1
            ctx = t.splitlines()[line - 1].strip()[:90]
            warn(p, f"第 {line} 行含陈旧表述（{why}）：…{ctx}…")

# ───────── 7. 契约编号有效性（C1–C27） ─────────
q8 = Q8.read_text(encoding='utf-8')
valid_c = set(re.findall(r'\|\s*(C\d+)\s*\|', q8)) | {f"C{n}" for n in range(1, 28)}
for p in sorted(drafts):
    t = p.read_text(encoding='utf-8')
    for c in sorted(set(re.findall(r'\bC(\d{1,2})\b', t))):
        if f"C{c}" not in valid_c:
            err(p, f"引用了不存在的契约条目 C{c}")

# ───────── 8. 交叉引用的 Phase 是否存在 ─────────
all_pids = set(rows) | {'F26'}
for p in sorted(drafts) + [FEAT / 'README.md']:
    t = p.read_text(encoding='utf-8')
    for ref in sorted(set(re.findall(r'F\d+P\d+', t))):
        if ref not in all_pids:
            err(p, f"引用了不存在的 Phase：{ref}")

# ───────── 报告 ─────────
print(f"审计对象：{len(drafts)} 份初稿 + README；立项书 §5.2 权威行 {len(rows)} 条")
print(f"ERROR {len(errors)} · WARN {len(warns)}")
print()
for e in errors:
    print("  [ERROR]", e)
if errors:
    print()
for w in warns:
    print("  [WARN ]", w)
sys.exit(1 if errors else 0)
