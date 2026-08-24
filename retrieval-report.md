# 自动检索质检报告（2026-08-21）

> 测量仪表：右栏(人工复核)是诊断信号。逐类压降下面 reject 的分类，才能让它归零。

## 计数
- 可直接应用（左栏）：**0**
- 人工复核（右栏）：**7**
- 丢弃：**8**
- 状态切换：**0**

## 右栏「为什么被拒」分类（训练瞄准镜）
- 探活超时/被拦截（疑似误杀，可借国内SCF消除）：5
- 其它：2

## 丢弃「为什么被丢」分类
- 理由缺失/不自洽：5
- 系统已补正链接，内容待人工确认（分诊自救成功）：2
- 无来源且系统也解析不到（须落地 name_query/cfsa）：1

## 质量测量（Step⑤：推送后直接看这 4 个数是否下降）
- 伪废止·无依据直接丢弃（本应归零）：**0**
- 发布日期误填实施日期（本应归零）：**0**
- 重复重报早已做过的变更（本应归零）：**9**
- 跨文件废止命中（越多越好）：**0**

## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5｜内容待人工确认
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC｜内容待人工确认
- 《粉尘爆炸泄压规范（GB 15605-2024）》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11｜内容待人工确认
- 《生产安全事故分类与编码》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=39334B61DAD4CC7F9E412A868C567717｜内容待人工确认
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0B6F6A3B8C4D5E6F7A8B9C0D1E2F3A4B → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8D9D545E31B5D9912134BFFBA4409B7A｜内容待人工确认
- 《GB/T 4288-2025 家用和类似用途电动洗衣机》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1C7G7B4C9D5E6F7A8B9C0D1E2F3A4B5C → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=A6DD817E54CC5A9C5D231F1480876CAD｜内容待人工确认
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4F0J0F7G2F7A8B9C0D1E2F3A4B9C0A1B → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=E2BBC7015B075B8AE7C3F3AA4D6A7340｜内容待人工确认
- 《GB 21456-2024 家用和类似用途厨房电器能效限定值及能效等级》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=5G1K1G8H3F7A8B9C0D1E2F3A4C1B2C3D → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F966E2FC4C7AB718356847B0DB1045E4｜内容待人工确认

## 右栏条目明细
- 《中山市排水管理条例》[环境与职业健康]：官方页超时/无法读取，所称变更无法自动核实，请人工点开确认；想设：name=中山市排水管理条例，link=已有，domains=['环境']，category=环境与职业健康，source=中山市人大常委会，adopted=False，fromValues=effectiveDate=2025-04-11，status=现行有效
- 《职业病分类和目录》[环境与职业健康]：官方页超时/无法读取，所称变更无法自动核实，请人工点开确认；想设：name=职业病分类和目录，link=已有，domains=['环境']，category=环境与职业健康，source=国务院，adopted=False，fromValues=effectiveDate=2025-08-01，status=现行有效
- 《GB 14866-2023 眼面防护具通用技术规范》[环境与职业健康]：官方页超时/无法读取，所称变更无法自动核实，请人工点开确认；想设：name=GB 14866-2023 眼面防护具通用技术规范，stdNo=GB 14866-2023，link=已有，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2025-01-01，status=现行有效
- 《中华人民共和国网络安全法》[信息安全]：官方页超时/无法读取，所称变更无法自动核实，请人工点开确认；想设：name=中华人民共和国网络安全法，link=已有，domains=['信息安全']，category=信息安全，source=全国人大常委会，adopted=False，fromValues=effectiveDate=2026-01-01，status=现行有效
- 《网络数据安全管理条例》[信息安全]：官方页超时/无法读取，所称变更无法自动核实，请人工点开确认；想设：name=网络数据安全管理条例，link=已有，domains=['信息安全']，category=信息安全，source=国务院，adopted=False，fromValues=effectiveDate=2025-01-01，status=现行有效
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[产品标准]：官方页未标注实施日期，无法自动填写；想设：name=GB/T 4288-2018 家用和类似用途电动洗衣机，stdNo=GB/T 4288-2018，status=已废止，link=已有，remark=即将被 GB/T 4288-2025 替代（新标准实施日期 2026-05-01），domains=['质量']，category=质量，replacedBy=GB/T 4288-2025，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-10-01，status=已废止
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[产品标准]：官方页未标注实施日期，无法自动填写；想设：name=GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级，stdNo=GB 24849-2017，status=已废止，link=已有，remark=即将被 GB 21456-2024 替代（新标准实施日期 2025-09-01），domains=['环境']，category=环境与职业健康，replacedBy=GB 21456-2024，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-06-01，status=已废止

## 丢弃条目明细
- 《中华人民共和国突发事件应对法》：理由里说改实施日期，实际却没给出日期
- 《中华人民共和国传染病防治法（2025修订）》：理由里说改实施日期，实际却没给出日期
- 《中华人民共和国食品安全法》：理由里说改实施日期，实际却没给出日期
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》：官方页未标注实施日期，无法自动填写；理由里说改实施日期，实际却没给出日期
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》：官方页未标注实施日期，无法自动填写；理由里说改实施日期，实际却没给出日期
- 《粉尘爆炸泄压规范（GB 15605-2024）》：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；理由里说改实施日期，实际却没给出日期
- 《生产安全事故分类与编码》：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；理由里说改实施日期，实际却没给出日期
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2D8H8C5D0E6F7A8B9C0D1E2F3A4B6C7D；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）；声称原状态是「已废止」，清单里其实是「现行有效」；判定为废止，却给不出官方写明的废止日期