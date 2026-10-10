# parttime-job-collect · 兼职/零工岗位搜集入库技能

把「兼职岗位搜集 → 清洗 → 表格管理」做成可复用的 Agent 技能：三路搜索（综合招聘平台 / 服务业兼职平台 / 微信小程序零工渠道）+ 连锁品牌官方直招，产出带可点击投递链接与投递状态跟踪的岗位清单，写入飞书多维表格（首选）或本地 Excel（保底）。

> 本技能沉淀自实际跑通的完整闭环：42 条深圳在招兼职岗位从搜集到入库全流程验证。

## 这是什么

| 能力 | 说明 |
|---|---|
| 搜索 | 三路并搜：①BOSS/智联/58/鱼泡 ②兼职猫/青团社/快马日结/灵活派/本地宝 ③小程序零工（灵工打卡、腾讯「附近的工作/找零工」、本地宝灵活用工、顺薪日结、猎职蜂等）+ 星巴克/肯德基/麦当劳/瑞幸等品牌官方直招（瑞幸固定收录微信公众号「瑞幸咖啡招聘」：附近门店 → 社会/学生兼职投递） |
| 清洗 | 官方直招/劳务派遣/中介标注、薪资标「招聘方口径」、疑似过期另表收集不误删 |
| 入库 | openpyxl 生成 5 表 Excel → `drive +import --type bitable` 导入飞书多维表格 → 清理空记录 |
| 投递闭环 | 「招聘链接」（url 样式可点击）+「状态」（单选，默认待投递，与全职表 10 选项一致） |
| 双模式 | 有飞书写多维表格；无飞书输出本地 Excel（搜索清洗逻辑完全一致） |

## 目录结构

```
parttime-job-collect/
├── SKILL.md              # 技能主文档（11 步主流程 + 字段规范 + 踩坑清单）
└── profile.example.json  # 画像配置模板（技能本体不含任何个人数据）
```

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
| 画像 | `~/.workbuddy/parttime-job-collect/profile.json` | `cities` / `job_types` / `channels` / `include_mini_program` |
| 目标表 | `~/.workbuddy/parttime-job-collect/target.json` | 飞书 base_token / table_url / 各表 table_id（仅 feishu 模式） |

## 主流程速览（详见 SKILL.md）

画像确认 → 生成关键词 → 三路搜索+品牌直招 → 清洗标注 → 生成 5 表 Excel → 导入多维表格 → 清理空记录 → 补投递字段（招聘链接/状态）→ 回读验证 → 交付摘要

## 主要字段（主表 15 列）

`序号 | 抓取时间 | 备注 | 工作地点 | 渠道分组 | 结算方式 | 用工主体 | 岗位名称 | 公司|门店|品牌 | 来源平台 | 工作周期与时段 | 薪资（招聘方口径） | 申请入口 | 状态 | 招聘链接`

投递入口统一走「招聘链接」一列（`[查看岗位](url)` 可点击），不设重复链接列。

## 相关项目

- [zhonghugo/daily-job-push](https://github.com/zhonghugo/daily-job-push) —— 全职岗位每日搜集推送技能（本技能的对照模板）
- [zhonghugo/Hugo-AI-Tools-Demos](https://github.com/zhonghugo/Hugo-AI-Tools-Demos) —— AI 小工具 demo 合集
