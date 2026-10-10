# parttime-job-collect · 兼职/零工岗位搜集入库技能

把「兼职岗位搜集 → 清洗 → 去重 → 表格管理」做成可复用的 Agent 技能：三路搜索（综合招聘平台 / 服务业兼职平台 / 微信小程序零工渠道）+ 连锁品牌官方直招，产出带可点击投递链接与投递状态跟踪的岗位清单，写入飞书多维表格（首选）或本地 Markdown/CSV（local 保底）。

> 本技能沉淀自实际跑通的完整闭环：42 条深圳在招兼职岗位从搜集到入库全流程验证。

## 这是什么

| 能力 | 说明 |
|---|---|
| 搜索 | 三路并搜：①BOSS/智联/58/鱼泡 ②兼职猫/青团社/快马日结/灵活派/本地宝 ③小程序零工（灵工打卡、腾讯「附近的工作/找零工」、本地宝灵活用工、顺薪日结、猎职蜂等）+ 星巴克/肯德基/麦当劳/瑞幸等品牌官方直招（瑞幸固定收录微信公众号「瑞幸咖啡招聘」：附近门店 → 社会/学生兼职投递） |
| 登录墙 | BOSS/智联明细页需登录 → 授权走浏览器通道抓 JD；未授权换渠道找同岗 → 定位链接兜底；岗位不降级 |
| 清洗 | 官方直招/劳务派遣/中介标注、薪资标「招聘方口径」、疑似过期另表收集不误删 |
| 去重归并 | `dedup_keys.py` 跨天去重：强键=归一化链接（剥壳/去追踪参数/m.域名归一）、退化键=岗位名+公司；命中老岗位归并（渠道数=去重后平台数、同岗来源追加）、五类标记 + 存量体检 |
| 入库 | feishu：openpyxl 5 表 Excel → `drive +import --type bitable` → 清理空记录 → 补字段；local：`export_local.py` 三件套（md/csv/ndjson） |
| 投递闭环 | 「招聘链接」（url 样式可点击）+「状态」（单选，默认待投递，与全职表 10 选项一致）+「渠道数/同岗来源」跨渠道信号 |
| 双模式 | 有飞书写多维表格；无飞书输出本地三件套（搜索/清洗/去重逻辑完全一致） |

## 目录结构

```
parttime-job-collect/
├── SKILL.md              # 技能主文档（12 步主流程 + 字段规范 + 登录墙降级链 + 踩坑清单）
├── profile.example.json  # 画像配置模板（技能本体不含任何个人数据）
└── scripts/
    ├── dedup_keys.py     # 兼职去重归并引擎（强/软键 + 五类标记 + 存量体检 + 渠道数）
    ├── export_local.py   # local 三件套导出（md 人读 / csv 可导入 / ndjson 下轮去重）
    └── test_dedup_keys.sh# 回归测试（14 条断言，改了 scripts/ 必须先跑）
```

## 回归测试

```bash
bash scripts/test_dedup_keys.sh
```

覆盖：新岗入库、强键归并、同平台不涨渠道数、m.域名与裸 URL 归一、追踪参数剥离、同名待确认、同名不同限定分岗、键冲突不写回不入库、存量体检（同链接重复/同链接岗位名不同）、空历史全新岗、local 三件套（md 超链接/csv 15 列表头/ndjson 可回读）。**不跑回归 = 拿用户的表当试验场。**

## 安装

- **WorkBuddy**：目录放到 `~/.workbuddy/skills/parttime-job-collect/`
- **其他 Agent**：放到该 Agent 的 skills 目录

装完确认 `~/.workbuddy/parttime-job-collect/` 下没有 `profile.json`（有就是前任的，删掉）。技能更新/分享不会串个人数据——画像与表格 token 一律放用户级目录。

## 使用

对 AI 说一句触发词即可：

- 「帮我搜兼职」
- 「找兼职岗位」
- 「兼职岗位清单」
- 「搜零工 / 日结 / 灵活用工」

首次使用会逐题引导（城市 / 兼职类型 / 渠道偏好 / 目标表），之后按画像默认跑；定时自动化可挂每日/每周自动搜集。

## 配置

| 文件 | 位置 | 说明 |
|---|---|---|
| 画像 | `~/.workbuddy/parttime-job-collect/profile.json` | `cities` / `job_types` / `channels` / `include_mini_program` / `allow_login_fetch`（可选） |
| 目标表 | `~/.workbuddy/parttime-job-collect/target.json` | 飞书 base_token / table_url / 各表 table_id（仅 feishu 模式） |

## 主流程速览（详见 SKILL.md）

画像确认 → 读已有记录 → 生成关键词 → 三路搜索+品牌直招（含登录墙处置）→ 清洗标注 → **去重归并**（五类标记+存量体检）→ 生成产物（feishu 5 表 Excel / local 三件套）→ 导入多维表格 → 清理空记录 → 补投递字段+去重字段 → 回读验证 → 交付摘要（跨渠道在招信号单列）

## 主要字段（主表基础 15 列）

`序号 | 抓取时间 | 备注 | 工作地点 | 渠道分组 | 结算方式 | 用工主体 | 岗位名称 | 公司|门店|品牌 | 来源平台 | 工作周期与时段 | 薪资（招聘方口径） | 申请入口 | 状态 | 招聘链接`

投递入口统一走「招聘链接」一列（`[查看岗位](url)` 可点击），不设重复链接列。去重功能字段（导入后补）：`渠道数`（number，去重后平台数）、`同岗来源`（text，平台列表以「；」连接）。

## 相关项目

- [zhonghugo/daily-job-push](https://github.com/zhonghugo/daily-job-push) —— 全职岗位每日搜集推送技能（本技能的对照模板：去重归并/登录墙/回归测试/local ndjson 闭环同构移植）
- [zhonghugo/Hugo-AI-Tools-Demos](https://github.com/zhonghugo/Hugo-AI-Tools-Demos) —— AI 小工具 demo 合集
