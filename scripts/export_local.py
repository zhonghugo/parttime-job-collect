#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parttime-job-collect · local 模式导出三件套
=============================================
输入：--jobs（new_jobs.json 数组）+ --outdir（输出目录）
输出：
  jobs-YYYY-MM-DD.md     人读表格，岗位名是超链接（点击直达招聘链接）
  jobs-YYYY-MM-DD.csv    15 列主表，可一键导入飞书多维表格 / Excel
  jobs-YYYY-MM-DD.ndjson 机器读，下一轮 --existing 去重用（别删）

字段顺序与 feishu 模式完全一致（主表 15 列）：
序号 | 抓取时间 | 备注 | 工作地点 | 渠道分组 | 结算方式 | 用工主体 |
岗位名称 | 公司|门店|品牌 | 来源平台 | 工作周期与时段 | 薪资（招聘方口径） |
申请入口 | 状态 | 招聘链接
"""

import argparse
import csv
import json
import os
import re
from datetime import date

COLUMNS = [
    '序号', '抓取时间', '备注', '工作地点', '渠道分组', '结算方式', '用工主体',
    '岗位名称', '公司|门店|品牌', '来源平台', '工作周期与时段', '薪资（招聘方口径）',
    '申请入口', '状态', '招聘链接',
]


def raw_url(value):
    """剥 [文本](url) markdown 壳 → 裸 URL；裸 URL 原样返回"""
    if not value:
        return ''
    value = value.strip()
    m = re.match(r'^\[[^\]]*\]\((https?://[^)\s]+)\)$', value)
    return m.group(1) if m else value


def md_link(rec):
    """招聘链接 → [岗位名](url)；先剥壳避免嵌套 markdown"""
    job = rec.get('岗位名称') or '岗位'
    url = raw_url(rec.get('招聘链接') or '')
    if not url:
        return job
    return f'[{job}]({url})'


def main():
    ap = argparse.ArgumentParser(description='兼职岗位 local 导出')
    ap.add_argument('--jobs', required=True, help='new_jobs.json 数组文件')
    ap.add_argument('--outdir', default='.', help='输出目录')
    ap.add_argument('--today', default=date.today().isoformat())
    args = ap.parse_args()

    with open(args.jobs, encoding='utf-8') as f:
        jobs = json.load(f)

    os.makedirs(args.outdir, exist_ok=True)
    prefix = os.path.join(args.outdir, f'jobs-{args.today}')

    # md 人读表格
    with open(prefix + '.md', 'w', encoding='utf-8') as f:
        f.write(f'# 兼职岗位 {args.today}\n\n')
        f.write(f'共 {len(jobs)} 条\n\n')
        f.write('| 岗位 | 公司 | 薪资 | 地点 | 平台 | 状态 |\n')
        f.write('|---|---|---|---|---|---|\n')
        for i, r in enumerate(jobs, 1):
            f.write('| %s | %s | %s | %s | %s | %s |\n' % (
                md_link(r),
                (r.get('公司|门店|品牌') or '').replace('|', '／'),
                r.get('薪资（招聘方口径）') or '',
                r.get('工作地点') or '',
                r.get('来源平台') or '',
                r.get('状态') or '待投递',
            ))
        f.write('\n> 投递入口见「招聘链接」，状态在表里自行跟踪；AI 不替人筛岗位。\n')

    # csv 15 列主表
    with open(prefix + '.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for i, r in enumerate(jobs, 1):
            w.writerow([
                i,
                r.get('抓取时间') or args.today,
                r.get('备注') or '',
                r.get('工作地点') or '',
                r.get('渠道分组') or '',
                r.get('结算方式') or '',
                r.get('用工主体') or '',
                r.get('岗位名称') or '',
                r.get('公司|门店|品牌') or '',
                r.get('来源平台') or '',
                r.get('工作周期与时段') or '',
                r.get('薪资（招聘方口径）') or '',
                r.get('申请入口') or '',
                r.get('状态') or '待投递',
                r.get('招聘链接') or '',
            ])

    # ndjson 下轮去重
    with open(prefix + '.ndjson', 'w', encoding='utf-8') as f:
        for r in jobs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    print(f'导出 {len(jobs)} 条 → {prefix}.md / {prefix}.csv / {prefix}.ndjson')


if __name__ == '__main__':
    main()
