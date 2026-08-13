# 自动检索质检报告（2026-08-13）

> 测量仪表：右栏(人工复核)是诊断信号。逐类压降下面 reject 的分类，才能让它归零。

## 计数
- 可直接应用（左栏）：**1**
- 人工复核（右栏）：**11**
- 丢弃：**21**
- 状态切换：**0**

## 右栏「为什么被拒」分类（训练瞄准镜）
- 旧值核对不符（未看清单）：11
- 系统已补正链接，内容待人工确认（分诊自救成功）：9
- 状态/日期不自洽：3

## 丢弃「为什么被丢」分类
- 无来源且系统也解析不到（须落地 name_query/cfsa）：21

## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC｜内容待人工确认
- 《GB 14866-2023 眼面防护具通用技术规范》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301｜内容待人工确认
- 《粉尘爆炸泄压规范（GB 15605-2024）》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11｜内容待人工确认
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC｜内容待人工确认
- 《GB 14866-2023 眼面防护具通用技术规范》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301｜内容待人工确认
- 《粉尘爆炸泄压规范（GB 15605-2024）》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11｜内容待人工确认
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC｜内容待人工确认
- 《GB 14866-2023 眼面防护具通用技术规范》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301｜内容待人工确认
- 《粉尘爆炸泄压规范（GB 15605-2024）》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11｜内容待人工确认

## 右栏条目明细
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=个体防护装备有毒有害及限量物质要求 GB 31420-2025，stdNo=GB 31420-2025，effectiveDate=2026-07-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC，domains=['环境']，category=环境与职业健康，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2026-07-01，status=现行有效
- 《GB 14866-2023 眼面防护具通用技术规范》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=GB 14866-2023 眼面防护具通用技术规范，stdNo=GB 14866-2023，effectiveDate=2025-01-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301，domains=['环境']，category=环境与职业健康，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2025-01-01，status=现行有效
- 《粉尘爆炸泄压规范（GB 15605-2024）》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=粉尘爆炸泄压规范（GB 15605-2024），stdNo=GB 15605-2024，effectiveDate=2026-01-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11，domains=['环境']，category=环境与职业健康，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2026-01-01，status=现行有效
- 《中华人民共和国招标投标法》[质量]：声称原日期是「2017-03-01」，清单里其实是「2017-12-28」；想设：name=中华人民共和国招标投标法，effectiveDate=2017-03-01，status=现行有效，link=http://www.npc.gov.cn/npc/c30834/202405/75baf2b6b5f84e7a8f1d4b8c9e7d6b3a.shtml，category=质量，source=全国人大网，adopted=False，fromValues=effectiveDate=2017-03-01，status=现行有效
- 《中华人民共和国电子签名法》[质量]：声称原日期是「2017-09-01」，清单里其实是「2019-04-23」；想设：name=中华人民共和国电子签名法，effectiveDate=2017-09-01，status=现行有效，link=http://www.npc.gov.cn/npc/c30834/202405/75baf2b6b5f84e7a8f1d4b8c9e7d6b3a.shtml，category=质量，source=全国人大网，adopted=False，fromValues=effectiveDate=2017-09-01，status=现行有效
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[质量]：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；声称原日期是「2025-03-01」，清单里其实是「2026-07-01」；声称原状态是「即将实施」，清单里其实是「现行有效」；标成「即将实施」，但实施日期 2025-03-01 早已过去；想设：name=个体防护装备有毒有害及限量物质要求 GB 31420-2025，stdNo=GB 31420-2025，effectiveDate=2025-03-01，status=即将实施，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC，category=质量，source=国家标准全文公开系统，adopted=False，fromValues=effectiveDate=2025-03-01，status=即将实施
- 《GB 14866-2023 眼面防护具通用技术规范》[质量]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「2024-07-01」，清单里其实是「2025-01-01」；想设：name=GB 14866-2023 眼面防护具通用技术规范，stdNo=GB 14866-2023，effectiveDate=2024-07-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301，category=质量，source=国家标准全文公开系统，adopted=False，fromValues=effectiveDate=2024-07-01，status=现行有效
- 《粉尘爆炸泄压规范（GB 15605-2024）》[质量]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「2024-09-01」，清单里其实是「2026-01-01」；想设：name=粉尘爆炸泄压规范（GB 15605-2024），stdNo=GB 15605-2024，effectiveDate=2024-09-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11，category=质量，source=国家标准全文公开系统，adopted=False，fromValues=effectiveDate=2024-09-01，status=现行有效
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「2025-08-01」，清单里其实是「2026-07-01」；声称原状态是「即将实施」，清单里其实是「现行有效」；标成「即将实施」，但实施日期 2025-08-01 早已过去；想设：name=个体防护装备有毒有害及限量物质要求 GB 31420-2025，stdNo=GB 31420-2025，effectiveDate=2025-08-01，status=即将实施，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC，category=环境与职业健康，source=国家标准全文公开系统，adopted=False，fromValues=effectiveDate=2025-08-01，status=即将实施
- 《GB 14866-2023 眼面防护具通用技术规范》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「2024-07-01」，清单里其实是「2025-01-01」；想设：name=GB 14866-2023 眼面防护具通用技术规范，stdNo=GB 14866-2023，effectiveDate=2024-07-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301，category=环境与职业健康，source=国家标准全文公开系统，adopted=False，fromValues=effectiveDate=2024-07-01，status=现行有效
- 《粉尘爆炸泄压规范（GB 15605-2024）》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「2024-11-01」，清单里其实是「2026-01-01」；声称原状态是「即将实施」，清单里其实是「现行有效」；标成「即将实施」，但实施日期 2024-11-01 早已过去；想设：name=粉尘爆炸泄压规范（GB 15605-2024），stdNo=GB 15605-2024，effectiveDate=2024-11-01，status=即将实施，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11，category=环境与职业健康，source=国家标准全文公开系统，adopted=False，fromValues=effectiveDate=2024-11-01，status=即将实施

## 丢弃条目明细
- 《国务院关于职工工作时间的规定》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）
- 《化学品安全标签编写规定》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）
- 《建筑设计防火规范》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（详情页标准号与输入不符（hcno 取错或未在前6条内））
- 《企业职工伤亡事故分类标准(GB6441-86)》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（详情页标准号与输入不符（hcno 取错或未在前6条内））
- 《关于公开征求《生产设备安全防护设计总则（征求意见稿）》意见的通知》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）
- 《GB55036-2022《消防设施通用规范》》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（详情页标准号与输入不符（hcno 取错或未在前6条内））
- 《国务院关于职工工作时间的规定》：依据来源确认失效（HTTP 404），多半是编造的链接：http://www.gov.cn/zhengce/content/2017-03/01/content_5170622.htm；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）
- 《化学品安全标签编写规定》：依据来源确认失效（HTTP 404），多半是编造的链接：https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/202405/t20240520_456547.shtml；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）；声称原日期是「1992-01-01」，清单里其实是「2010-05-01」
- 《建筑设计防火规范》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（详情页标准号与输入不符（hcno 取错或未在前6条内））；声称原日期是「2015-05-01」，清单里其实是「2018-10-01」
- 《企业职工伤亡事故分类标准(GB6441-86)》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（详情页标准号与输入不符（hcno 取错或未在前6条内））
- 《关于公开征求《生产设备安全防护设计总则（征求意见稿）》意见的通知》：依据来源确认失效（HTTP 404），多半是编造的链接：https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/202405/t20240520_456547.shtml；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）；声称原日期是「」，清单里其实是「2022-04-27」
- 《GB55036-2022《消防设施通用规范》》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（详情页标准号与输入不符（hcno 取错或未在前6条内））
- 《中华人民共和国招标投标法》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）
- 《中华人民共和国电子签名法》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）
- 《中华人民共和国宪法》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）
- 《国务院关于职工工作时间的规定》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）
- 《化学品安全标签编写规定》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）；声称原日期是「2009-06-21」，清单里其实是「2010-05-01」
- 《建筑设计防火规范》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（详情页标准号与输入不符（hcno 取错或未在前6条内））；声称原日期是「2015-05-01」，清单里其实是「2018-10-01」
- 《企业职工伤亡事故分类标准(GB6441-86)》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（详情页标准号与输入不符（hcno 取错或未在前6条内））
- 《关于公开征求《生产设备安全防护设计总则（征求意见稿）》意见的通知》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（samr.gov.cn），留空待补）；声称原日期是「」，清单里其实是「2022-04-27」
- 《GB55036-2022《消防设施通用规范》》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（详情页标准号与输入不符（hcno 取错或未在前6条内））