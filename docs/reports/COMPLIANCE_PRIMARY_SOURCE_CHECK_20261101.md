# 合规引用一手核验（2026-11-01）

> 对象：NotebookLM「ClawsJoy」中提到的 UL 588／FCC ID／CE／GPSR／EU AI Act／TRO。
> 性质：链接与出处核验，不是法律意见；EU/FCC 官方页有 WAF，未能全文抓取。

## 核验结果

| 主题 | 一手/权威出处 | 本次核验 |
|---|---|---|
| UL 588 | UL Solutions：String Lights for All-Year Use — UL 588 Supplement SD（https://www.ul.com/thecodeauthority/news/string-lights-all-year-useul-588-supplement-sd） | 找到 UL 官方说明；UL 588 是安全标准，不是法规；是否强制取决于平台/市场要求 |
| FCC ID | FCC Equipment Authorization（https://www.fcc.gov/wireless/bureau-divisions/technologies-systems-and-innovation-division/equipment-authorization） | 官方页存在但本次抓取被 403；FCC ID 针对射频设备，不是所有灯串都需要 |
| CE / LVD | Directive 2014/35/EU（https://eur-lex.europa.eu/eli/dir/2014/35/oj） | 官方 ELI 链接；页面返回 202 WAF，未全文核验 |
| CE / EMC | Directive 2014/30/EU（https://eur-lex.europa.eu/eli/dir/2014/30/oj） | 官方 ELI 链接；页面返回 202 WAF，未全文核验 |
| CE / RoHS | Directive 2011/65/EU（https://eur-lex.europa.eu/eli/dir/2011/65/oj） | 官方 ELI 链接；页面返回 202 WAF，未全文核验 |
| CE / RED | Directive 2014/53/EU（https://eur-lex.europa.eu/eli/dir/2014/53/oj） | 官方 ELI 链接；无线/蓝牙款才涉及；页面未全文核验 |
| GPSR | Regulation (EU) 2023/988（https://eur-lex.europa.eu/eli/reg/2023/988/oj） | 官方 ELI 链接；页面返回 202 WAF，未全文核验 |
| EU AI Act | Regulation (EU) 2024/1689（https://eur-lex.europa.eu/eli/reg/2024/1689/oj） | 官方 ELI 链接；页面返回 202 WAF，未全文核验 |
| TRO | USITC Section 337 说明（https://www.usitc.gov/intellectual_property/about_section_337.htm） | 可访问；TRO 是法院临时禁令，不是 ITC Section 337 的同义词；不能混用 |

## 三个不能混用的概念

1. **平台政策**：Meta／TikTok 的「Made with AI」标签要求。
2. **内容溯源标准**：C2PA／Content Credentials，属于技术元数据。
3. **EU AI Act**：欧盟对 AI 系统的透明度/风险管理义务。

三者可能同时相关，但不能互相替代；具体适用要看市场、平台、内容类型。

## 需要人工补的核验

- 用浏览器打开 ELI 链接，确认最新 consolidated 版本与生效日期。
- 用 FCC 设备授权数据库确认具体产品是否需要 FCC ID。
- 用 UL Product iQ 查具体灯串型号的 UL 588 认证范围。
- TRO 没有统一公开清单；必须按案件/法院/专利检索，不能只看一个官网页面。
- 欧盟责任人、WEEE、包装 EPR 等成员国差异，需要按销售国分别确认。

## 结论

NotebookLM 的合规清单方向是对的，但本次只完成**出处级核验**，没有完成**法规全文级核验**。

不能把这份清单直接当合规结论；它适合做待核验清单。
