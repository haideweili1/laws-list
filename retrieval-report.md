# 自动检索质检报告（2026-08-14）

> 测量仪表：右栏(人工复核)是诊断信号。逐类压降下面 reject 的分类，才能让它归零。

## 计数
- 可直接应用（左栏）：**1**
- 人工复核（右栏）：**4**
- 丢弃：**17**
- 状态切换：**0**

## 右栏「为什么被拒」分类（训练瞄准镜）
- 日期与官方页不一致（GLM 报错日期）：4
- 旧值核对不符（未看清单）：1

## 丢弃「为什么被丢」分类
- 日期与官方页不一致（GLM 报错日期）：9
- 无来源且系统也解析不到（须落地 name_query/cfsa）：7
- 其它：1

## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）
- 《中华人民共和国传染病防治法（2025修订）》[reuse_existing]：GLM 原本给的是 http://www.npc.gov.cn/npc/c30834/202403/75baf2b6b5f84e7a9e1e8b3a7c9b3d0c.shtml → 系统解析到 http://www.npc.gov.cn/c2/c30834/202504/t20250430_445085.html｜内容待人工确认
- 《职业病分类和目录》[reuse_existing]：GLM 原本给的是 http://www.gov.cn/zhengce/zhengceku/202403/20240315_1234567.htm → 系统解析到 https://www.gov.cn/gongbao/2025/issue_11886/202502/content_7007111.html｜内容已核对一致，可直接应用
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5｜内容待人工确认
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC｜内容待人工确认
- 《生产安全事故分类与编码》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=39334B61DAD4CC7F9E412A868C567717｜内容待人工确认
- 《中华人民共和国反不正当竞争法(2025修订)》[reuse_existing]：GLM 原本给的是 http://www.npc.gov.cn/npc/c30834/202504/75b8f5b8a5f54e7a9b6b8f8b8b8b8b8b.shtml → 系统解析到 http://www.npc.gov.cn/c2/c30834/202506/t20250627_446247.html｜内容待人工确认
- 《网络安全技术 信息系统灾难恢复规范》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=ABE370E7DABA83CD71BCAC2042A95F70｜内容待人工确认
- 《GB/T 22080-2025 网络安全技术 信息安全管理体系 要求》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=abcdef1234567890abcdef1234567890 → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=886C4EE1A50A26626A7BAD8571301CEC｜内容待人工确认
- 《网络数据安全管理条例》[reuse_existing]：GLM 原本给的是 http://www.gov.cn/zhengce/content/2024-07/30/content_6948962.htm → 系统解析到 https://www.gov.cn/zhengce/content/202409/content_6977766.htm｜内容待人工确认
- 《关键信息基础设施安全保护条例》[reuse_existing]：GLM 原本给的是 http://www.gov.cn/zhengce/content/2021-08/17/content_5631682.htm → 系统解析到 https://www.gov.cn/zhengce/zhengceku/2021-08/17/content_5631671.htm｜内容待人工确认
- 《生成式人工智能服务安全管理暂行办法》[reuse_existing]：GLM 原本给的是 https://www.cac.gov.cn/2023-07/13/c_1129746029.htm → 系统解析到 https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm｜内容待人工确认
- 《生成式人工智能服务安全基本要求》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8A8B8C8D8E8F8G8H8I8J8K8L8M8N8O8P → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F67D3F376E0A0A0FF5317FB36B32A30A｜内容待人工确认
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0B3E8F3C5D2A1B4C6E7F8A9B0C1D2E3F → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8D9D545E31B5D9912134BFFBA4409B7A｜内容待人工确认
- 《GB/T 4288-2025 家用和类似用途电动洗衣机》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1C2D3E4F5A6B7C8D9E0F1A2B3C4D5E6F → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=A6DD817E54CC5A9C5D231F1480876CAD｜内容待人工确认
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F90B89DADC888F069B9993659D39BD4F｜内容待人工确认
- 《GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4804719D7D206D7538788BE44F54DC64｜内容待人工确认
- 《GB 21456-2024 家用和类似用途厨房电器能效限定值及能效等级》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F966E2FC4C7AB718356847B0DB1045E4｜内容待人工确认

## 右栏条目明细
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[环境与职业健康]：官方页面读到的实施日期是 2017-01-01，与本条声称的 2025-08-01 不一致，请人工确认；想设：name=《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025，stdNo=GB/T 23723.5-2025，effectiveDate=2025-08-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2025-08-01，status=现行有效
- 《GB/T 22080-2025 网络安全技术 信息安全管理体系 要求》[质量]：官方页面读到的实施日期是 2017-01-01，与本条声称的 2026-01-01 不一致，请人工确认；想设：name=GB/T 22080-2025 网络安全技术 信息安全管理体系 要求，stdNo=GB/T 22080-2025，effectiveDate=2026-01-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=886C4EE1A50A26626A7BAD8571301CEC，domains=['质量']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2026-01-01，status=现行有效
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[产品标准]：官方页面读到的实施日期是 2017-01-01，与本条声称的 2018-10-01 不一致，请人工确认；想设：name=GB/T 4288-2018 家用和类似用途电动洗衣机，stdNo=GB/T 4288-2018，effectiveDate=2018-10-01，abolishDate=2026-05-01，status=已废止，link=https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8D9D545E31B5D9912134BFFBA4409B7A，remark=即将被 GB/T 4288-2025 替代（新标准实施日期 2026-05-01），domains=['质量']，category=质量，replacedBy=GB/T 4288-2025 家用和类似用途电动洗衣机，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-10-01，status=已废止
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[产品标准]：官方页面读到的实施日期是 2017-01-01，与本条声称的 2013-10-01 不一致，请人工确认；声称原状态是「已废止」，清单里其实是「现行有效」；想设：name=GB 12021.4-2013 电动洗衣机能效水效限定值及等级，stdNo=GB 12021.4-2013，effectiveDate=2013-10-01，abolishDate=2027-04-01，status=已废止，link=https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F90B89DADC888F069B9993659D39BD4F，remark=即将被 GB 12021.4-2026 替代（新标准实施日期 2027-04-01），domains=['环境']，category=环境与职业健康，replacedBy=GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2013-10-01，status=已废止

## 丢弃条目明细
- 《中华人民共和国突发事件应对法》：依据来源链接形态疑似编造（非官方格式/含规律ID，必为照搬）：http://www.npc.gov.cn/npc/c30834/202403/75baf2b6b5f84e7a9e1e8b3a7c9b3d0c.shtml；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（npc.gov.cn），留空待补）
- 《中华人民共和国传染病防治法（2025修订）》：官方页面读到的实施日期是 1989-02-21，与本条声称的 2025-09-01 不一致，请人工确认；伪变更：声称的变更字段新值与清单现值完全一致（如「已废止→已废止」），无实际改动，已丢弃
- 《中华人民共和国食品安全法》：依据来源链接形态疑似编造（非官方格式/含规律ID，必为照搬）：http://www.npc.gov.cn/npc/c30834/202403/75baf2b6b5f84e7a9e1e8b3a7c9b3d0c.shtml；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）
- 《职业病分类和目录》：伪变更：声称的变更字段新值与清单现值完全一致（如「已废止→已废止」），无实际改动，已丢弃
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》：官方页面读到的实施日期是 2017-01-01，与本条声称的 2026-07-01 不一致，请人工确认；伪变更：声称的变更字段新值与清单现值完全一致（如「已废止→已废止」），无实际改动，已丢弃
- 《GB 14866-2023 眼面防护具通用技术规范》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）
- 《粉尘爆炸泄压规范（GB 15605-2024）》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）
- 《生产安全事故分类与编码》：官方页面读到的实施日期是 2017-01-01，与本条声称的 2026-07-01 不一致，请人工确认；伪变更：声称的变更字段新值与清单现值完全一致（如「已废止→已废止」），无实际改动，已丢弃
- 《中华人民共和国反不正当竞争法(2025修订)》：官方页面读到的实施日期是 1993-09-02，与本条声称的 2025-10-15 不一致，请人工确认；伪变更：声称的变更字段新值与清单现值完全一致（如「已废止→已废止」），无实际改动，已丢弃
- 《网络安全技术 信息系统灾难恢复规范》：官方页面读到的实施日期是 2017-01-01，与本条声称的 2026-01-01 不一致，请人工确认；伪变更：声称的变更字段新值与清单现值完全一致（如「已废止→已废止」），无实际改动，已丢弃
- 《中华人民共和国网络安全法》：依据来源链接形态疑似编造（非官方格式/含规律ID，必为照搬）：https://www.npc.gov.cn/npc/c30834/202407/75baf5b8b5f54e7a9b6b4f8b8b8b8b8b.shtml；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（npc.gov.cn），留空待补）
- 《网络数据安全管理条例》：官方页面读到的实施日期是 2024-08-30，与本条声称的 2025-01-01 不一致，请人工确认；伪变更：声称的变更字段新值与清单现值完全一致（如「已废止→已废止」），无实际改动，已丢弃
- 《关键信息基础设施安全保护条例》：官方页面读到的实施日期是 2021-04-27，与本条声称的 2021-09-01 不一致，请人工确认；伪变更：声称的变更字段新值与清单现值完全一致（如「已废止→已废止」），无实际改动，已丢弃
- 《生成式人工智能服务安全管理暂行办法》：官方页面读到的实施日期是 2023-07-13，与本条声称的 2023-08-15 不一致，请人工确认；伪变更：声称的变更字段新值与清单现值完全一致（如「已废止→已废止」），无实际改动，已丢弃
- 《生成式人工智能服务安全基本要求》：官方页面读到的实施日期是 2017-01-01，与本条声称的 2025-11-01 不一致，请人工确认；伪变更：声称的变更字段新值与清单现值完全一致（如「已废止→已废止」），无实际改动，已丢弃
- 《信息安全技术 网络安全等级保护基本要求》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）