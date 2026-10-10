#!/usr/bin/env bash
# parttime-job-collect 回归测试：dedup_keys.py + export_local.py
# 用法：bash scripts/test_dedup_keys.sh   （退出码非 0 = 有断言失败）
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ❌ $1"; }
check() { # check <描述> <python表达式>（在 $TMP 下求值，变量：new/merges/updates 已载入）
  local desc="$1" expr="$2"
  if python3 -c "
import json, os
os.chdir('$TMP')
new=json.load(open('runA.json',encoding='utf-8'))
merges=json.load(open('runA.merges.json',encoding='utf-8'))
updates=json.load(open('runA.updates.json',encoding='utf-8')).get('update_records',{})
ok = $expr
" 2>/dev/null; then ok "$desc"; else fail "$desc"; fi
}

echo "== 准备 fixture =="
cat > "$TMP/existing.ndjson" <<'EOF'
{"record_id":"recE1","岗位名称":"星巴克 · 兼职星级咖啡师","公司|门店|品牌":"星巴克咖啡（深圳）有限公司","来源平台":"BOSS直聘","招聘链接":"[查看岗位](https://www.zhipin.com/job_detail/e493f6b5a0594bb41H1-0tu6F1RT.html)","状态":["待投递"]}
{"record_id":"recE2","岗位名称":"瑞幸 · 兼职咖啡师","公司|门店|品牌":"瑞幸咖啡（深圳）有限公司","来源平台":"BOSS直聘","招聘链接":"[查看岗位](https://www.zhipin.com/job_detail/ffaa55fe2e79b3390nV62d2-E1VZ.html)","状态":["待投递"]}
{"record_id":"recE3","岗位名称":"麦当劳 · 晚班兼职","公司|门店|品牌":"深圳金拱门食品有限公司","来源平台":"智联招聘","招聘链接":"https://www.zhipin.com/job_detail/dup1.html?utm_source=weekly","状态":["待投递"]}
{"record_id":"recE5","岗位名称":"兼职日结骑手（龙华）","公司|门店|品牌":"宝安新安配送站点直招","来源平台":"58同城","招聘链接":"https://m.58.com/sz/peisongyuan/55165509574302x.shtml","状态":["待投递"]}
{"record_id":"recE6","岗位名称":"兼职日结骑手","公司|门店|品牌":"宝安新安配送站点直招","来源平台":"鱼泡直聘","招聘链接":"https://www.yupao.com/qiye/job/rid.html","状态":["待投递"]}
{"record_id":"recE7a","岗位名称":"茶饮店员兼职","公司|门店|品牌":"某饮品公司","来源平台":"兼职猫","招聘链接":"[查看岗位](https://a.com/job/x.html)","状态":["待投递"]}
{"record_id":"recE7b","岗位名称":"茶饮店员兼职","公司|门店|品牌":"某饮品公司","来源平台":"兼职猫","招聘链接":"https://a.com/job/x.html","状态":["待投递"]}
{"record_id":"recE8a","岗位名称":"促销员兼职","公司|门店|品牌":"公司A","来源平台":"青团社","招聘链接":"https://c.com/job/z.html","状态":["待投递"]}
{"record_id":"recE8b","岗位名称":"理货员兼职","公司|门店|品牌":"公司A","来源平台":"青团社","招聘链接":"https://c.com/job/z.html","状态":["待投递"]}
EOF

cat > "$TMP/candidatesA.json" <<'EOF'
[
 {"岗位名称":"星巴克 · 兼职星级咖啡师","公司|门店|品牌":"星巴克咖啡（深圳）有限公司","来源平台":"品牌官网（星巴克招聘门户）","招聘链接":"[查看岗位](https://www.zhipin.com/job_detail/e493f6b5a0594bb41H1-0tu6F1RT.html)","状态":["待投递"]},
 {"岗位名称":"瑞幸 · 兼职咖啡师","公司|门店|品牌":"瑞幸咖啡（深圳）有限公司","来源平台":"BOSS直聘","招聘链接":"https://m.zhipin.com/job_detail/ffaa55fe2e79b3390nV62d2-E1VZ.html","状态":["待投递"]},
 {"岗位名称":"麦当劳 · 晚班兼职","公司|门店|品牌":"深圳金拱门食品有限公司","来源平台":"58同城","招聘链接":"https://www.zhipin.com/job_detail/dup1.html","状态":["待投递"]},
 {"岗位名称":"兼职日结骑手（福田）","公司|门店|品牌":"宝安新安配送站点直招","来源平台":"兼职猫","招聘链接":"https://m.yupao.com/qiye/job/rid.html","状态":["待投递"]},
 {"岗位名称":"兼职日结骑手","公司|门店|品牌":"宝安新安配送站点直招","来源平台":"BOSS直聘","招聘链接":"https://www.boss.com/job/new1.html","状态":["待投递"]},
 {"岗位名称":"兼职日结骑手","公司|门店|品牌":"宝安新安配送站点直招","来源平台":"鱼泡直聘","招聘链接":"https://www.yupao.com/qiye/job/rid.html?utm_source=x","状态":["待投递"]},
 {"岗位名称":"海底捞钟点工","公司|门店|品牌":"海底捞餐饮（宝安万达店）","来源平台":"青团社","招聘链接":"https://haidilao.com/job/h1.html","状态":["待投递"]}
]
EOF

echo "== Run A：常规归并 / 同名待确认 / 同名不同限定 / 存量体检 =="
python3 "$DIR/dedup_keys.py" --existing "$TMP/existing.ndjson" --candidates "$TMP/candidatesA.json" --out "$TMP/runA" --today 2026-10-10 >/dev/null 2>&1

check "新岗入库（海底捞，无命中）" "len(new)==2 and any(j['岗位名称'].startswith('海底捞') for j in new)"
check "同名不同限定按新岗入库（福田 vs 龙华）" "any('兼职日结骑手（福田）'==j['岗位名称'] for j in new)"
check "归并：强键命中 recE1，渠道数=2（BOSS直聘+品牌官网）" "updates.get('recE1',{}).get('渠道数')==2"
check "归并：recE1 同岗来源含两个平台" "updates.get('recE1',{}).get('同岗来源')=='BOSS直聘；品牌官网（星巴克招聘门户）'"
check "同平台重复不涨渠道数（recE2 瑞幸 BOSS→BOSS）" "updates.get('recE2',{}).get('渠道数')==1"
check "m.域名与裸URL归一命中（recE2）" "len(updates)==5 and 'recE2' in updates"
check "追踪参数剥离后命中（recE3，渠道数=2 智联+58）" "updates.get('recE3',{}).get('渠道数')==2"
check "同名待确认归并（recE5，新链接不同）" "'recE5' in updates and updates['recE5'].get('渠道数')==2"
check "同名待确认标记出现在 merges" "any(m['type'].startswith('❓ 同名待确认') for m in merges)"
check "存量体检：同链接重复 1 组（茶饮店员）" "sum(1 for m in merges if m['type'].startswith('⚠️ 同链接重复'))==1"
check "存量体检：同链接岗位名不同 1 组（促销员/理货员）" "sum(1 for m in merges if m['type'].startswith('❗ 同链接但岗位名不同'))==1"

echo "== Run B：键冲突 =="
cat > "$TMP/existingB.ndjson" <<'EOF'
{"record_id":"recB1","岗位名称":"肯德基 · 服务员","公司|门店|品牌":"百胜餐饮","来源平台":"BOSS直聘","招聘链接":"https://www.zhipin.com/job_detail/kfc1.html","状态":["待投递"]}
{"record_id":"recB2","岗位名称":"肯德基 · 服务员","公司|门店|品牌":"百胜餐饮","来源平台":"智联招聘","招聘链接":"[查看岗位](https://www.zhipin.com/job_detail/kfc1.html)","状态":["已投递"]}
EOF
cat > "$TMP/candidatesB.json" <<'EOF'
[{"岗位名称":"肯德基 · 服务员","公司|门店|品牌":"百胜餐饮","来源平台":"58同城","招聘链接":"https://www.zhipin.com/job_detail/kfc1.html","状态":["待投递"]}]
EOF
python3 "$DIR/dedup_keys.py" --existing "$TMP/existingB.ndjson" --candidates "$TMP/candidatesB.json" --out "$TMP/runB" --today 2026-10-10 >/dev/null 2>&1
python3 -c "
import json
merges=json.load(open('$TMP/runB.merges.json',encoding='utf-8'))
updates=json.load(open('$TMP/runB.updates.json',encoding='utf-8')).get('update_records',{})
new=json.load(open('$TMP/runB.json',encoding='utf-8'))
assert any(m['type'].startswith('⚠️ 键冲突') for m in merges), '缺键冲突标记'
assert len(updates)==0, '键冲突不应产生写回体'
assert len(new)==0, '键冲突候选不应入库'
" && ok "键冲突：标记存在、无写回、候选不入库" || fail "键冲突断言失败"

echo "== Run C：空历史全新岗 + local 导出三件套 =="
cat > "$TMP/candidatesC.json" <<'EOF'
[{"岗位名称":"茶饮店员兼职","公司|门店|品牌":"某饮品公司","来源平台":"兼职猫","招聘链接":"[查看岗位](https://a.com/job/x.html)","状态":["待投递"]}]
EOF
python3 "$DIR/dedup_keys.py" --candidates "$TMP/candidatesC.json" --out "$TMP/runC" --today 2026-10-11 >/dev/null 2>&1
python3 -c "
import json
new=json.load(open('$TMP/runC.json',encoding='utf-8'))
assert len(new)==1, '空历史应全部为新岗'
" && ok "空历史：候选全按新岗入库" || fail "空历史断言失败"
python3 "$DIR/export_local.py" --jobs "$TMP/runC.json" --outdir "$TMP/out" --today 2026-10-11 >/dev/null 2>&1
python3 -c "
import csv, json, os
assert os.path.exists('$TMP/out/jobs-2026-10-11.md'), '缺 md'
assert os.path.exists('$TMP/out/jobs-2026-10-11.csv'), '缺 csv'
assert os.path.exists('$TMP/out/jobs-2026-10-11.ndjson'), '缺 ndjson'
rows=list(csv.reader(open('$TMP/out/jobs-2026-10-11.csv',encoding='utf-8-sig')))
assert rows[0]==['序号','抓取时间','备注','工作地点','渠道分组','结算方式','用工主体','岗位名称','公司|门店|品牌','来源平台','工作周期与时段','薪资（招聘方口径）','申请入口','状态','招聘链接'], 'csv 表头应为 15 列主表'
assert len(rows)==2, 'csv 应为 1 条数据+表头'
md=open('$TMP/out/jobs-2026-10-11.md',encoding='utf-8').read()
assert '[茶饮店员兼职](https://a.com/job/x.html)' in md, 'md 岗位名应为超链接'
nd=open('$TMP/out/jobs-2026-10-11.ndjson',encoding='utf-8').readline()
assert json.loads(nd)['岗位名称']=='茶饮店员兼职', 'ndjson 应可回读'
" && ok "local 三件套：md 超链接 / csv 15 列表头 / ndjson 可回读" || fail "local 导出断言失败"

echo
echo "结果：PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
