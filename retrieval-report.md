# 自动检索质检报告（2026-08-20）

> 测量仪表：右栏(人工复核)是诊断信号。逐类压降下面 reject 的分类，才能让它归零。

## 计数
- 可直接应用（左栏）：**0**
- 人工复核（右栏）：**6**
- 丢弃：**10**
- 状态切换：**0**

## 右栏「为什么被拒」分类（训练瞄准镜）
- 状态/日期不自洽：3
- 其它：2
- 旧值核对不符（未看清单）：1
- 系统已补正链接，内容待人工确认（分诊自救成功）：1

## 丢弃「为什么被丢」分类
- 状态/日期不自洽：5
- 无来源且系统也解析不到（须落地 name_query/cfsa）：4
- 理由缺失/不自洽：1

## 质量测量（Step⑤：推送后直接看这 4 个数是否下降）
- 伪废止·无依据直接丢弃（本应归零）：**0**
- 发布日期误填实施日期（本应归零）：**0**
- 重复重报早已做过的变更（本应归零）：**6**
- 跨文件废止命中（越多越好）：**0**

## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）
- 《中华人民共和国突发事件应对法》[reuse_existing]：GLM 原本给的是 https://www.npc.gov.cn/npc/c30834/202404/75baf3b6b5f84e7a9b6f8b4b9b6b4b9b.shtml → 系统解析到 https://www.gov.cn/yaowen/liebiao/202406/content_6960130.htm｜内容已核对一致，可直接应用
- 《中华人民共和国传染病防治法（2025修订）》[reuse_existing]：GLM 原本给的是 https://www.npc.gov.cn/npc/c30834/202404/75baf3b6b5f84e7a9b6f8b4b9b6b4b9b.shtml → 系统解析到 http://www.npc.gov.cn/c2/c30834/202504/t20250430_445085.html｜内容已核对一致，可直接应用
- 《职业病分类和目录》[reuse_existing]：GLM 原本给的是 http://www.gov.cn/zhengce/202404/20240415_1234567.htm → 系统解析到 https://www.gov.cn/gongbao/2025/issue_11886/202502/content_7007111.html｜内容已核对一致，可直接应用
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5｜内容待人工确认
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC｜内容待人工确认
- 《消防应急照明和疏散指示系统  GB 17945-2024》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=E419CF2378717C5B32EA924C0E4003C0｜内容待人工确认
- 《GB 30000.1-2024 化学品分类和标签规范 第1部分：通则》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=C008AEDBFD9A16F3C5BEB671C20618DD｜内容待人工确认
- 《粉尘爆炸泄压规范（GB 15605-2024）》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11｜内容待人工确认
- 《中华人民共和国网络安全法》[reuse_existing]：GLM 原本给的是 https://www.gov.cn/zhengce/2024-09/24/content_6947390.htm → 系统解析到 https://www.cac.gov.cn/2016-11/07/c_1119867116.htm｜内容待人工确认
- 《网络数据安全管理条例》[reuse_existing]：GLM 原本给的是 https://www.gov.cn/zhengce/2024-09/24/content_6947390.htm → 系统解析到 https://www.gov.cn/zhengce/content/202409/content_6977766.htm｜内容已核对一致，可直接应用
- 《关键信息基础设施安全保护条例》[reuse_existing]：GLM 原本给的是 https://www.gov.cn/zhengce/2024-09/24/content_6947390.htm → 系统解析到 https://www.gov.cn/zhengce/zhengceku/2021-08/17/content_5631671.htm｜内容已核对一致，可直接应用
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0B3E8F3A5C7D2E1F0A9B8C7D6E5F4A3B2 → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8D9D545E31B5D9912134BFFBA4409B7A｜内容待人工确认
- 《GB/T 4288-2025 家用和类似用途电动洗衣机》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=A6DD817E54CC5A9C5D231F1480876CAD｜内容待人工确认
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1F2E3D4C5B6A7D8E9F0A1B2C3D4E5F6A7 → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F90B89DADC888F069B9993659D39BD4F｜内容待人工确认
- 《GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4804719D7D206D7538788BE44F54DC64｜内容待人工确认
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2F3E4D5C6B7A8D9E0F1A2B3C4D5E6F7A8 → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=E2BBC7015B075B8AE7C3F3AA4D6A7340｜内容待人工确认
- 《GB 21456-2024 家用和类似用途厨房电器能效限定值及能效等级》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F966E2FC4C7AB718356847B0DB1045E4｜内容待人工确认

## 右栏条目明细
- 《中华人民共和国传染病防治法（2025修订）》[环境与职业健康]：标成「即将实施」，但实施日期 2025-09-01 早已过去；想设：name=中华人民共和国传染病防治法（2025修订），effectiveDate=2025-09-01，status=即将实施，link=已有，domains=['环境']，category=环境与职业健康，source=全国人大常委会，adopted=False，fromValues=effectiveDate=2025-09-01，status=现行有效
- 《中山市排水管理条例》[环境与职业健康]：标成「即将实施」，但实施日期 2025-04-11 早已过去；想设：name=中山市排水管理条例，effectiveDate=2025-04-11，status=即将实施，link=已有，domains=['环境']，category=环境与职业健康，source=中山市人大常委会，adopted=False，fromValues=effectiveDate=2025-04-11，status=现行有效
- 《职业病分类和目录》[环境与职业健康]：标成「即将实施」，但实施日期 2025-08-01 早已过去；想设：name=职业病分类和目录，effectiveDate=2025-08-01，status=即将实施，link=已有，domains=['环境']，category=环境与职业健康，source=国务院，adopted=False，fromValues=effectiveDate=2025-08-01，status=现行有效
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[产品标准]：官方页未标注实施日期，原填实施日期已清空待核；想设：name=GB/T 4288-2018 家用和类似用途电动洗衣机，stdNo=GB/T 4288-2018，abolishDate=2026-05-01，status=已废止，link=已有，remark=即将被 GB/T 4288-2025 替代（新标准实施日期 2026-05-01），domains=['质量']，category=质量，replacedBy=GB/T 4288-2025 家用和类似用途电动洗衣机，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-10-01，status=已废止
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[产品标准]：官方页未标注实施日期，原填实施日期已清空待核；声称原状态是「已废止」，清单里其实是「现行有效」；想设：name=GB 12021.4-2013 电动洗衣机能效水效限定值及等级，stdNo=GB 12021.4-2013，abolishDate=2027-04-01，status=已废止，link=已有，remark=即将被 GB 12021.4-2026 替代（新标准实施日期 2027-04-01），domains=['环境']，category=环境与职业健康，replacedBy=GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2013-10-01，status=已废止
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[产品标准]：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；想设：name=GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级，stdNo=GB 24849-2017，effectiveDate=2018-06-01，abolishDate=2025-09-01，status=已废止，link=已有，remark=即将被 GB 21456-2024 替代（新标准实施日期 2025-09-01），domains=['环境']，category=环境与职业健康，replacedBy=GB 21456-2024 家用和类似用途厨房电器能效限定值及能效等级，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-06-01，status=已废止

## 丢弃条目明细
- 《中华人民共和国食品安全法》：依据来源无法自动验证（超时 / 被拦截），请人工点开确认：https://www.npc.gov.cn/npc/c30834/202404/75baf3b6b5f84e7a9b6f8b4b9b6b4b9b.shtml；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）；标成「即将实施」，但实施日期 2025-12-01 早已过去
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》：官方页未标注实施日期，原填实施日期已清空待核；标成「即将实施」，但实施日期 2025-08-01 早已过去；理由里说改实施日期，实际却没给出日期
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》：官方页未标注实施日期，原填实施日期已清空待核；标成「即将实施」，但实施日期 2026-07-01 早已过去；理由里说改实施日期，实际却没给出日期
- 《GB 14866-2023 眼面防护具通用技术规范》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）；标成「即将实施」，但实施日期 2025-01-01 早已过去
- 《消防应急照明和疏散指示系统  GB 17945-2024》：官方页未标注实施日期，原填实施日期已清空待核；标成「即将实施」，但实施日期 2025-05-01 早已过去；理由里说改实施日期，实际却没给出日期
- 《手提式灭火器 GB4351-2023》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）；标成「即将实施」，但实施日期 2025-01-01 早已过去
- 《GB 30000.1-2024 化学品分类和标签规范 第1部分：通则》：官方页未标注实施日期，原填实施日期已清空待核；标成「即将实施」，但实施日期 2025-08-01 早已过去；理由里说改实施日期，实际却没给出日期
- 《粉尘爆炸泄压规范（GB 15605-2024）》：官方页未标注实施日期，原填实施日期已清空待核；标成「即将实施」，但实施日期 2026-01-01 早已过去；理由里说改实施日期，实际却没给出日期
- 《生产安全事故分类与编码》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）；标成「即将实施」，但实施日期 2026-07-01 早已过去
- 《中华人民共和国网络安全法》：官方页未标注实施日期，原填实施日期已清空待核；理由里说改实施日期，实际却没给出日期