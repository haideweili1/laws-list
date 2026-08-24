# 自动检索质检报告（2026-08-24）

> 测量仪表：右栏(人工复核)是诊断信号。逐类压降下面 reject 的分类，才能让它归零。

## 计数
- 可直接应用（左栏）：**0**
- 人工复核（右栏）：**6**
- 丢弃：**3**
- 状态切换：**0**

## 右栏「为什么被拒」分类（训练瞄准镜）
- 其它：4
- 系统已补正链接，内容待人工确认（分诊自救成功）：2
- 旧值核对不符（未看清单）：1
- 状态/日期不自洽：1

## 丢弃「为什么被丢」分类
- 无来源且系统也解析不到（须落地 name_query/cfsa）：2
- 理由缺失/不自洽：1

## 质量测量（Step⑤：推送后直接看这 4 个数是否下降）
- 伪废止·无依据直接丢弃（本应归零）：**0**
- 发布日期误填实施日期（本应归零）：**0**
- 重复重报早已做过的变更（本应归零）：**12**
- 跨文件废止命中（越多越好）：**0**

## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）
- 《职业病分类和目录》[reuse_existing]：GLM 原本给的是 http://www.gov.cn/zhengce/zhengceku/202505/content_6978126.htm → 系统解析到 https://www.gov.cn/gongbao/2025/issue_11886/202502/content_7007111.html｜内容已核对一致，可直接应用
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5｜内容待人工确认
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC｜内容待人工确认
- 《GB 14866-2023 眼面防护具通用技术规范》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301｜内容待人工确认
- 《中华人民共和国网络安全法》[reuse_existing]：GLM 原本给的是 https://www.gov.cn/zhengce/2024-09/24/content_6947960.htm → 系统解析到 https://www.cac.gov.cn/2016-11/07/c_1119867116.htm｜内容待人工确认
- 《网络数据安全管理条例》[reuse_existing]：GLM 原本给的是 https://www.gov.cn/zhengce/2024-09/24/content_6947960.htm → 系统解析到 https://www.gov.cn/zhengce/content/202409/content_6977766.htm｜内容已核对一致，可直接应用
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0A6F6B3C8F8B4E4B9A4C4B4B4B4B4B4B → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8D9D545E31B5D9912134BFFBA4409B7A｜内容待人工确认
- 《GB/T 4288-2025 家用和类似用途电动洗衣机》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1B7F7C3D9G9C5F5C0B5D5D5D5D5D5D5D → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=A6DD817E54CC5A9C5D231F1480876CAD｜内容待人工确认
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2C8G8D4H0H0D6G6D1E6E6E6E6E6E6E6 → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=E2BBC7015B075B8AE7C3F3AA4D6A7340｜内容待人工确认
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4E0I0F6J2J2F8I8F3G8G8G8G8G8G8G8 → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F90B89DADC888F069B9993659D39BD4F｜内容待人工确认
- 《GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=5F1J1G7K3K3G9J9G4H9H9H9H9H9H9H9 → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4804719D7D206D7538788BE44F54DC64｜内容待人工确认

## 右栏条目明细
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[环境与职业健康]：官方页未标注实施日期，无法自动填写；想设：name=《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025，stdNo=GB/T 23723.5-2025，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5，remark=即将被 GB/T 23723.5-2030 替代（新标准实施日期 2030-08-01），domains=['环境']，category=质量，replacedBy=GB/T 23723.5-2030，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2025-08-01，status=现行有效
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[环境与职业健康]：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；想设：name=个体防护装备有毒有害及限量物质要求 GB 31420-2025，stdNo=GB 31420-2025，link=已有，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2026-07-01，status=现行有效
- 《GB 14866-2023 眼面防护具通用技术规范》[环境与职业健康]：官方页未标注实施日期，无法自动填写；想设：name=GB 14866-2023 眼面防护具通用技术规范，stdNo=GB 14866-2023，link=已有，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2025-01-01，status=现行有效
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[产品标准]：官方页未标注实施日期，无法自动填写；想设：name=GB/T 4288-2018 家用和类似用途电动洗衣机，stdNo=GB/T 4288-2018，status=已废止，link=已有，remark=即将被 GB/T 4288-2025 替代（新标准实施日期 2026-05-01），domains=['质量']，category=质量，replacedBy=GB/T 4288-2025，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-10-01，status=已废止
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[产品标准]：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；想设：name=GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级，stdNo=GB 24849-2017，status=已废止，link=已有，remark=即将被 GB 24849-202X 替代（新标准实施日期 待定），domains=['质量']，category=质量，replacedBy=GB 24849-202X，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-06-01，status=已废止
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[产品标准]：官方页未标注实施日期，无法自动填写；声称原状态是「已废止」，清单里其实是「现行有效」；判定为废止，却给不出官方写明的废止日期；想设：name=GB 12021.4-2013 电动洗衣机能效水效限定值及等级，stdNo=GB 12021.4-2013，status=已废止，link=已有，remark=即将被 GB 12021.4-2026 替代（新标准实施日期 2027-04-01），domains=['质量']，category=质量，replacedBy=GB 12021.4-2026，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2013-10-01，status=已废止

## 丢弃条目明细
- 《粉尘爆炸泄压规范（GB 15605-2024）》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）
- 《生产安全事故分类与编码》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）
- 《中华人民共和国网络安全法》：官方页未标注实施日期，无法自动填写；理由里说改实施日期，实际却没给出日期