# geo-name-cn

本地项目 skill，用于调用民政部“中国·国家地名信息库”公开接口，支持行政区划树、地名检索、详情、同名/同音统计，以及按区划和类别分页批量获取。

## 可实现的任务

- 获取省、地、县三级行政区划并导出完整 JSON 与主要字段 CSV。
- 由县级标准名称定位地名 `id`，再获取地名详情。
- 按县检索乡级行政区，按乡镇检索行政村和社区，并保存分页、去重与断点信息。
- 查询同名、同音地名在区划或类别上的统计。
- 探测某个年份是否真正可用，避免把“当前版”错误标成指定年份。

## Prompt 示例

```text
使用 $geo-name-cn 获取国家地名信息库当前版的全国省、地、县三级行政区划；保存完整 JSON 和主要字段 CSV；按省分批、去重，并用全国根树交叉核验。
```

```text
使用 $geo-name-cn 搜索北京市下辖全部乡级行政区。按县逐个检索 乡、镇、街道、地区、苏木，类别限定为 215；完整分页、按 id 去重、保存原始响应和断点清单，再获取唯一匹配项的详情。
```

```text
使用 $geo-name-cn 探测 1999—2025 各年份是否受地名搜索与详情接口支持。把 HTTP 500、JSON null、回退到当前版分别记录，不要把失败当作零条记录。
```

## 命令示例

在 skill 目录运行：

```bash
python -m pip install -r requirements.txt
python scripts/geo_name_cn.py --dry-run search --name 东华门街道 --place-type-code 215 --code 110101 --search-type exact
python scripts/geo_name_cn.py three-levels --json divisions.json --csv divisions.csv
python scripts/geo_name_cn.py search --name 社区 --place-type-code 2162 --code 110101001 --all-pages --json communities.json
python scripts/geo_name_cn.py details --id RECORD_ID --year 2018 --json detail.json
python scripts/test_geo_name_cn.py
```

skill 自包含运行脚本、离线测试、依赖清单和接口文档，不导入或调用项目外脚本。脚本依赖 Python 3.10+；第三方依赖写在同目录的 `requirements.txt`。默认限速为每次请求至少间隔 0.4 秒；大规模任务应按服务响应继续调低频率。

## 关键限制

- `/9095/xzqh/getList` 的官方文档没有公布年份范围，官网前端固定使用 `year=0`。1949—2025 的 77 次全国树请求仅得到 10 种响应：1949—2011、2012、2013—2017、2018—2019 各形成一版，2020—2025 才逐年不同。早期响应含近年地名且显著更接近 2021/2022 民政部代码—名称集合，不能当作文件名年份的历史区划。完整映射、边界 A/B 和定量证据见 `references/year-semantics.md`。
- 省略、`0`、`-1`、`2026`、`9999` 实测返回当前版；空串、`abc`、`2012.0` 返回 HTTP 400；极低正整数不稳定。经验上只能把 2012—2025 称为“会选择服务端版本的区间”，仍不能称为逐年真实年版。官网当前行政区划页注明数据截至 2025-12-31。
- 地名搜索的空 `stName` 在缺少或使用宽区划时可能返回 HTTP 500；但在狭窄的六位县码并指定 `placeTypeCode` 时可作为类别全量锚点。必须完整翻页并以 `total` 核验，失败或不一致时再按关键词或标准名称回退。
- `year=2025` 在地名搜索中实测为 HTTP 500；省略年份或用 `0` 得到的是未标注具体年份的当前快照。
- 地名搜索/详情与行政区划树使用不同的年份语义；历史年份必须按 `215`、`2161`、`2162` 分类别探测，并区分非空响应、结构化空响应和无法判定，不能套用行政区划的 10 桶映射。
- 1999—2024 年、北京/某地级市、`215`/`2161`/`2162` 共 156 个组合的完整探针表明：2014、2018、2020、2021、2022 在两地三类均非空；2016 的乡级类非空，但两个自治类在两地均为结构化空响应，且某地级市探针县的乡级锚点仅 3 条，属于异常响应快照。其余组合经四次尝试仍不可用或无法判定。响应存在不等于历史内容真实、完整。
- 完整采集后的跨年指纹进一步表明：在乡级和群众自治两类、北京和某地级市两个测试范围内，2020 与 2021、显式 2022 与 `year=0` 当前快照的地名 ID、语义核心和详情全文均完全相同。北京群众自治的 2014/2018 地名记录也完全相同，但详情全文不同。故相同数量、相同搜索记录甚至相同 ID 都不足以证明详情快照相同；这些观察也不得推广到未测试地区或类别。
- 搜索结果 `id` 与快照绑定；详情请求年份不一致可能返回 JSON `null`。
- 详情接口必须使用表单 POST；开源 MCP 示例中的 JSON POST 实测为 HTTP 400。

详见 `references/api-reference.md`、`references/year-semantics.md` 与 `references/sources.md`。

## 参考来源

* [中国国家地名信息库 接口服务](https://dmfw.mca.gov.cn/interface.html)
  * API文档，本skill积累了探查该系列接口的经验
* [linyshdhhcb/china-geonames-skill: 本项目是中国·国家地名信息库的 API 技能规范文档的 Claude Code Skill。](https://github.com/linyshdhhcb/china-geonames-skill)
  * 借鉴启发，本skill结合综合性更强的实战经验进一步完善
