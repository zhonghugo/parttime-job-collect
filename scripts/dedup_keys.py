#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parttime-job-collect · 兼职岗位去重归并引擎
============================================
输入：--existing（历史记录 ndjson，可不存在）+ --candidates（本轮候选 json 数组）
输出：
  <out>.json         真新岗位（数组，直接进入库/导出步骤）
  <out>.merges.json  归并计划（给人看：键冲突 / 同名待确认 / 归并明细）
  <out>.updates.json 归并写回体（可直接作 lark-cli base +record-batch-update 的 --json）
  merges-<today>.ndjson  local 模式 append-only 更正日志（下一轮拼回 existing）

去重键：
  强键 = 归一化链接：剥 [文本](url) 壳 → 去追踪参数（utm/spm 等）→ 移动端域名 m.x → www.x
  退化键 = 岗位名去括号限定词 + 公司名去括号 + 去分隔符空白（小写）
归并口径：
  - 强键命中 1 条老记录 → 归并：同岗来源追加新平台（同平台重复只加来源行不加渠道数），
    渠道数 = 去重后的平台数
  - 强键命中多条 → ⚠️ 键冲突：本轮不动候选，报候选来源行 + 命中各行的记录 ID
  - 退化键命中但链接不同 → ❓ 同名待确认：按同岗归并，两链接都留在同岗来源，人工确认
  - 两侧括号限定词互斥（如 龙华 vs 福田）→ 视为不同岗位，候选按新岗入库
  - 存量体检（只读，不改记录）：同链接多行 → ⚠️ 同链接重复（岗位名一致）/ ❗ 同链接但岗位名不同
五类标记摘要必须原样带出，不许自己消化掉。

字段命名对齐兼职主表：岗位名称 / 公司|门店|品牌 / 来源平台 / 招聘链接 / 状态 / 抓取时间。
"""

import argparse
import json
import os
import re
import sys
from datetime import date

# ---------- 归一化 ----------

_TRACKING_RE = re.compile(r'[?&](?:utm_[a-z]+|spm|from|from_source|source|ref|refer|scene|channel)=[^&]*', re.I)
_MOBILE_HOSTS = ('m.', 'm2.', 'mobile.')


def strip_md_link(value):
    """[查看岗位](https://... ) -> https://...；裸 URL 原样返回"""
    if not value:
        return ''
    value = value.strip()
    m = re.match(r'^\[[^\]]*\]\((https?://[^)\s]+)\)$', value)
    if m:
        return m.group(1)
    return value


def norm_link(value):
    """强键：归一化链接。剥壳 → 去追踪参数 → 去尾斜杠 → 移动域名归一 → 小写"""
    url = strip_md_link(value)
    if not url:
        return ''
    url = url.split('#')[0]
    url = _TRACKING_RE.sub('', url)
    url = re.sub(r'[?&]$', '', url)
    url = url.rstrip('/')
    # m.zhipin.com -> www.zhipin.com（同岗移动/桌面页归一）
    m = re.match(r'^(https?://)(%s)([^/]+)' % '|'.join(_MOBILE_HOSTS), url, re.I)
    if m:
        url = m.group(1) + 'www.' + m.group(3) + url[m.end():]
    return url.lower()


def norm_bracket(value):
    """去掉括号及其内容，返回 (去括号文本, 括号内容集合)"""
    if not value:
        return '', set()
    quals = set(re.findall(r'[（(]([^）)]+)[）)]', value))
    cleaned = re.sub(r'[（(][^）)]*[）)]', '', value)
    return cleaned, quals


def norm_name(value):
    """岗位名归一（退化键用）：去括号、去分隔符空白、小写"""
    cleaned, _ = norm_bracket(value or '')
    cleaned = cleaned.replace('·', '').replace('•', '').replace(' ', '').replace('-', '').replace('—', '')
    return cleaned.lower()


def norm_company(value):
    """公司名归一（退化键用）：去括号内容、去空格、小写"""
    cleaned, _ = norm_bracket(value or '')
    cleaned = cleaned.replace(' ', '')
    return cleaned.lower()


def dedup_key(rec):
    return norm_link(rec.get('招聘链接') or '')


def soft_key(rec):
    return (norm_name(rec.get('岗位名称')) or '', norm_company(rec.get('公司|门店|品牌')) or '')


def qualifiers(rec):
    _, q1 = norm_bracket(rec.get('岗位名称') or '')
    _, q2 = norm_bracket(rec.get('公司|门店|品牌') or '')
    return q1 | q2


def platform_norm(p):
    p = (p or '').strip()
    return p


def unique_platforms(recs):
    """去重后的平台列表（同平台重复见只算一个）"""
    seen, out = set(), []
    for r in recs:
        p = platform_norm(r.get('来源平台'))
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


# ---------- 读入 ----------

def load_ndjson(path):
    recs = []
    if path and os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        recs.append(json.loads(line))
                    except json.JSONDecodeError:
                        sys.stderr.write(f'[warn] 跳过无法解析行: {line[:80]}\n')
    return recs


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser(description='兼职岗位去重归并')
    ap.add_argument('--existing', default='', help='历史记录 ndjson 路径（可不存在）')
    ap.add_argument('--candidates', required=True, help='本轮候选 json 数组文件')
    ap.add_argument('--out', required=True, help='输出前缀，如 out/parttime')
    ap.add_argument('--today', default=date.today().isoformat())
    args = ap.parse_args()

    existing = load_ndjson(args.existing)
    with open(args.candidates, encoding='utf-8') as f:
        candidates = json.load(f)

    # 存量索引
    existing_by_link = {}
    for i, r in enumerate(existing):
        existing_by_link.setdefault(dedup_key(r), []).append((i, r))

    new_jobs, merges = [], []
    updates = {}
    log_lines = []
    log_path = f'merges-{args.today}.ndjson'

    def log(entry):
        entry.setdefault('date', args.today)
        log_lines.append(entry)

    for cand in candidates:
        key = dedup_key(cand)
        hits = existing_by_link.get(key, [])
        if key == '':
            # 无链接候选：按退化键处理
            hits = []

        if len(hits) == 1:
            # ---- 强键命中 1 条 → 归并 ----
            idx, old = hits[0]
            rid = old.get('record_id', f'<existing#{idx}>')
            old_platforms = {platform_norm(old.get('来源平台'))} - {''}
            new_p = platform_norm(cand.get('来源平台'))
            same_platform = bool(new_p) and new_p in old_platforms
            combined = [old] + [cand]
            plats = unique_platforms(combined)
            count = len(plats)
            old_sources = (old.get('同岗来源') or '')
            new_src = cand.get('同岗来源') or cand.get('来源平台') or ''
            src = '；'.join(x for x in [old_sources, new_src] if x and x not in (old_sources or '').split('；'))
            if not src:
                src = new_src
            updates[rid] = {'渠道数': count, '同岗来源': src}
            merges.append({
                'type': '归并', 'rid': rid, '岗位名称': old.get('岗位名称'), '公司': old.get('公司|门店|品牌'),
                'detail': f"同链接命中，来源 {old.get('来源平台')} → {plats}；同平台重复={same_platform}"
            })
            log({'type': 'merge', 'rid': rid, 'job': old.get('岗位名称'),
                 'platforms': plats, 'same_platform': same_platform})
            continue

        if len(hits) > 1:
            # ---- ⚠️ 键冲突：本轮不动 ----
            hit_ids = [h[1].get('record_id', f'<existing#{h[0]}>') for h in hits]
            merges.append({
                'type': '⚠️ 键冲突（本轮未归并）', '岗位名称': cand.get('岗位名称'),
                '公司': cand.get('公司|门店|品牌'), '来源': cand.get('来源平台'),
                'detail': f"同时命中 {len(hits)} 条已有记录：{hit_ids}；本轮不猜不并，人工定完下一轮才归并"
            })
            log({'type': 'conflict', 'job': cand.get('岗位名称'), 'hit_ids': hit_ids})
            continue

        # ---- 无强键命中：退化键 ----
        sk = soft_key(cand)
        soft_hits = [(i, r) for i, r in enumerate(existing) if soft_key(r) == sk]
        cq = qualifiers(cand)

        if soft_hits:
            idx, old = soft_hits[0]
            oq = qualifiers(old)
            rid = old.get('record_id', f'<existing#{idx}>')
            # 两侧括号限定词互斥 → 不同岗位
            if cq and oq and cq != oq:
                new_jobs.append(cand)
                merges.append({
                    'type': '❓ 同名不同限定', '岗位名称': cand.get('岗位名称'),
                    '公司': cand.get('公司|门店|品牌'),
                    'detail': f"与已有「{old.get('岗位名称')}」同公司同基础岗位名，但限定词互斥（{oq} vs {cq}），已按新岗位入库"
                })
                log({'type': 'new_job_diff_qualifier', 'job': cand.get('岗位名称'),
                     'old': old.get('岗位名称')})
                continue
            # 否则 → ❓ 同名待确认：按同岗归并
            combined = [old] + [cand]
            plats = unique_platforms(combined)
            updates[rid] = {'渠道数': len(plats), '同岗来源': '；'.join(plats)}
            merges.append({
                'type': '❓ 同名待确认', 'rid': rid, '岗位名称': old.get('岗位名称'),
                '公司': old.get('公司|门店|品牌'),
                'detail': f"仅公司+岗位名相同、链接不同（老 {dedup_key(old)} vs 新 {dedup_key(cand)}）——可能同名不同岗，已归并但建议人工看一眼"
            })
            log({'type': 'same_name_confirm', 'rid': rid, 'job': cand.get('岗位名称'),
                 'old_link': dedup_key(old), 'new_link': dedup_key(cand)})
            continue

        # ---- 真新岗 ----
        new_jobs.append(cand)
        log({'type': 'new', 'job': cand.get('岗位名称'), 'company': cand.get('公司|门店|品牌')})

    # ---- 存量体检（只读，不改记录）----
    seen_groups = {}
    for i, r in enumerate(existing):
        seen_groups.setdefault(dedup_key(r), []).append((i, r))
    for key, group in seen_groups.items():
        if len(group) < 2 or key == '':
            continue
        names = {r.get('岗位名称') for _, r in group}
        if len(names) == 1:
            merges.append({
                'type': '⚠️ 同链接重复（存量体检）', '岗位名称': group[0][1].get('岗位名称'),
                'detail': f"同一条链接挂在 {len(group)} 行上、岗位名一致，多半是重复行，人工合并；"
                          f"状态不一致时先定保留哪份再合；URL={key}；行={[g[1].get('record_id', f'<existing#{g[0]}>') for g in group]}"
            })
        else:
            merges.append({
                'type': '❗ 同链接但岗位名不同（存量体检）', '岗位名称': ' / '.join(sorted(names)),
                'detail': f"同一链接下岗位名不一致，可能有行挂错链接，先核对再动；URL={key}；行={[g[1].get('record_id', f'<existing#{g[0]}>') for g in group]}"
            })

    # ---- 输出 ----
    out_json = args.out + '.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(new_jobs, f, ensure_ascii=False, indent=2)

    with open(args.out + '.merges.json', 'w', encoding='utf-8') as f:
        json.dump(merges, f, ensure_ascii=False, indent=2)

    with open(args.out + '.updates.json', 'w', encoding='utf-8') as f:
        json.dump({'update_records': updates}, f, ensure_ascii=False, indent=2)

    with open(log_path, 'a', encoding='utf-8') as f:
        for line in log_lines:
            f.write(json.dumps(line, ensure_ascii=False) + '\n')

    # ---- 摘要（供 SKILL.md 第 12 步原样带出）----
    n_new = len(new_jobs)
    n_merge = sum(1 for m in merges if m['type'] == '归并')
    n_confirm = sum(1 for m in merges if m['type'] == '❓ 同名待确认')
    n_conflict = sum(1 for m in merges if m['type'].startswith('⚠️ 键冲突'))
    n_qual = sum(1 for m in merges if m['type'] == '❓ 同名不同限定')
    n_dup = sum(1 for m in merges if m['type'].startswith('⚠️ 同链接重复'))
    n_mislink = sum(1 for m in merges if m['type'].startswith('❗ 同链接但岗位名不同'))
    print(f'新岗位 {n_new} 条｜归并老岗位 {n_merge} 条｜同名待确认 {n_confirm} 条｜'
          f'键冲突 {n_conflict} 条｜同名不同限定 {n_qual} 条｜存量体检：同链接重复 {n_dup} 组、同链接岗位名不同 {n_mislink} 组')
    print(f'产物: {out_json} / {args.out}.merges.json / {args.out}.updates.json / {log_path}')


if __name__ == '__main__':
    main()
