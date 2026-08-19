# 自动检索质检报告（2026-08-19）

> 测量仪表：右栏(人工复核)是诊断信号。逐类压降下面 reject 的分类，才能让它归零。

## 计数
- 可直接应用（左栏）：**0**
- 人工复核（右栏）：**16**
- 丢弃：**0**
- 状态切换：**9**

## 右栏「为什么被拒」分类（训练瞄准镜）
- 系统已补正链接，内容待人工确认（分诊自救成功）：12
- 旧值核对不符（未看清单）：11
- 状态/日期不自洽：9

## 丢弃「为什么被丢」分类
- （无）

## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）
- 《职业病分类和目录》[reuse_existing]：GLM 原本给的是 http://www.gov.cn/zhengce/zhengceku/2024-03/29/content_6943192.htm → 系统解析到 https://www.gov.cn/gongbao/2025/issue_11886/202502/content_7007111.html｜内容待人工确认
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5｜内容待人工确认
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC｜内容待人工确认
- 《GB 14866-2023 眼面防护具通用技术规范》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301｜内容待人工确认
- 《粉尘爆炸泄压规范（GB 15605-2024）》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11｜内容待人工确认
- 《生产安全事故分类与编码》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=39334B61DAD4CC7F9E412A868C567717｜内容待人工确认
- 《中华人民共和国网络安全法》[reuse_existing]：GLM 原本给的是 https://www.npc.gov.cn/npc/c30834/202407/75baf3b6b5f54e7a9e1e8e8e8e8e8e8e.shtml → 系统解析到 https://www.cac.gov.cn/2016-11/07/c_1119867116.htm｜内容待人工确认
- 《网络数据安全管理条例》[reuse_existing]：GLM 原本给的是 http://www.gov.cn/zhengce/content/2024-07/10/content_6948967.htm → 系统解析到 https://www.gov.cn/zhengce/content/202409/content_6977766.htm｜内容待人工确认
- 《《信息安全技术个人信息安全规范》GB/T 35273-2020》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0A3B5C6D7E8F9A0B1C2D3E4F5A6B7C8D → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4568B7A8C2D1E3F4A5B6C7D8E9F0A1B2｜内容待人工确认
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0B3E8F3C5D2A1B4C6E7F0A1B2C3D4E5F → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8D9D545E31B5D9912134BFFBA4409B7A｜内容待人工确认
- 《GB/T 4288-2025 家用和类似用途电动洗衣机》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=A6DD817E54CC5A9C5D231F1480876CAD｜内容待人工确认
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6 → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F90B89DADC888F069B9993659D39BD4F｜内容待人工确认
- 《GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4804719D7D206D7538788BE44F54DC64｜内容待人工确认
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7 → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=E2BBC7015B075B8AE7C3F3AA4D6A7340｜内容待人工确认
- 《GB 21456-2024 家用和类似用途厨房电器能效限定值及能效等级》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F966E2FC4C7AB718356847B0DB1045E4｜内容待人工确认

## 右栏条目明细
- 《中华人民共和国突发事件应对法》[环境与职业健康]：声称原日期是「」，清单里其实是「2024-11-01」；想设：name=中华人民共和国突发事件应对法，effectiveDate=2024-11-01，status=现行有效，link=已有，domains=['环境']，category=环境与职业健康，source=全国人大常委会，adopted=False，fromValues=effectiveDate=，status=现行有效
- 《中华人民共和国传染病防治法（2025修订）》[环境与职业健康]：声称原日期是「」，清单里其实是「2025-09-01」；标成「即将实施」，但实施日期 2025-09-01 早已过去；想设：name=中华人民共和国传染病防治法（2025修订），effectiveDate=2025-09-01，status=即将实施，link=已有，domains=['环境']，category=环境与职业健康，source=全国人大常委会，adopted=False，fromValues=effectiveDate=，status=现行有效
- 《中华人民共和国食品安全法》[环境与职业健康]：声称原日期是「」，清单里其实是「2025-12-01」；标成「即将实施」，但实施日期 2025-12-01 早已过去；想设：name=中华人民共和国食品安全法，effectiveDate=2025-12-01，status=即将实施，link=已有，domains=['环境']，category=环境与职业健康，source=全国人大常委会，adopted=False，fromValues=effectiveDate=，status=现行有效
- 《职业病分类和目录》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「」，清单里其实是「2025-08-01」；标成「即将实施」，但实施日期 2025-08-01 早已过去；想设：name=职业病分类和目录，effectiveDate=2025-08-01，status=即将实施，link=已有，domains=['环境']，category=环境与职业健康，source=国务院，adopted=False，fromValues=effectiveDate=，status=现行有效
- 《中山市排水管理条例》[环境与职业健康]：声称原日期是「」，清单里其实是「2025-04-11」；标成「即将实施」，但实施日期 2025-04-11 早已过去；想设：name=中山市排水管理条例，effectiveDate=2025-04-11，status=即将实施，link=已有，domains=['环境']，category=环境与职业健康，source=中山市人大常委会，adopted=False，fromValues=effectiveDate=，status=现行有效
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「」，清单里其实是「2025-08-01」；标成「即将实施」，但实施日期 2025-08-01 早已过去；想设：name=《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025，stdNo=GB/T 23723.5-2025，effectiveDate=2025-08-01，status=即将实施，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=，status=现行有效
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「」，清单里其实是「2026-07-01」；标成「即将实施」，但实施日期 2026-07-01 早已过去；想设：name=个体防护装备有毒有害及限量物质要求 GB 31420-2025，stdNo=GB 31420-2025，effectiveDate=2026-07-01，status=即将实施，link=已有，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=，status=现行有效
- 《GB 14866-2023 眼面防护具通用技术规范》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「」，清单里其实是「2025-01-01」；标成「即将实施」，但实施日期 2025-01-01 早已过去；想设：name=GB 14866-2023 眼面防护具通用技术规范，stdNo=GB 14866-2023，effectiveDate=2025-01-01，status=即将实施，link=已有，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=，status=现行有效
- 《粉尘爆炸泄压规范（GB 15605-2024）》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「」，清单里其实是「2026-01-01」；标成「即将实施」，但实施日期 2026-01-01 早已过去；想设：name=粉尘爆炸泄压规范（GB 15605-2024），stdNo=GB 15605-2024，effectiveDate=2026-01-01，status=即将实施，link=已有，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=，status=现行有效
- 《生产安全事故分类与编码》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原日期是「」，清单里其实是「2026-07-01」；标成「即将实施」，但实施日期 2026-07-01 早已过去；想设：name=生产安全事故分类与编码，effectiveDate=2026-07-01，status=即将实施，link=已有，domains=['环境']，category=质量，source=国家市场监督管理总局、国家标准化管理委员会，adopted=False，fromValues=effectiveDate=，status=现行有效
- 《中华人民共和国网络安全法》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=中华人民共和国网络安全法，effectiveDate=2026-01-01，status=现行有效，link=已有，domains=['信息安全']，category=信息安全，source=全国人大常委会，adopted=False，fromValues=effectiveDate=2026-01-01，status=现行有效
- 《网络数据安全管理条例》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=网络数据安全管理条例，effectiveDate=2025-01-01，status=现行有效，link=已有，domains=['信息安全']，category=信息安全，source=国务院，adopted=False，fromValues=effectiveDate=2025-01-01，status=现行有效
- 《《信息安全技术个人信息安全规范》GB/T 35273-2020》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=《信息安全技术个人信息安全规范》GB/T 35273-2020，stdNo=GB/T 35273-2020，effectiveDate=2020-03-06，status=现行有效，link=已有，remark=即将被 GB/T 35273-2024 替代（新标准实施日期 2024-09-01），domains=['信息安全']，category=信息安全，replacedBy=GB/T 35273-2024，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2020-03-06，status=现行有效
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[产品标准]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=GB/T 4288-2018 家用和类似用途电动洗衣机，stdNo=GB/T 4288-2018，effectiveDate=2018-10-01，abolishDate=2026-05-01，status=已废止，link=已有，remark=即将被 GB/T 4288-2025 替代（新标准实施日期 2026-05-01），domains=['质量']，category=质量，replacedBy=GB/T 4288-2025 家用和类似用途电动洗衣机，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-10-01，status=已废止
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[产品标准]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原状态是「已废止」，清单里其实是「现行有效」；想设：name=GB 12021.4-2013 电动洗衣机能效水效限定值及等级，stdNo=GB 12021.4-2013，effectiveDate=2013-10-01，abolishDate=2027-04-01，status=已废止，link=已有，remark=即将被 GB 12021.4-2026 替代（新标准实施日期 2027-04-01），domains=['环境']，category=环境与职业健康，replacedBy=GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2013-10-01，status=已废止
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[产品标准]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级，stdNo=GB 24849-2017，effectiveDate=2018-06-01，abolishDate=2025-09-01，status=已废止，link=已有，remark=即将被 GB 21456-2024 替代（新标准实施日期 2025-09-01），domains=['环境']，category=环境与职业健康，replacedBy=GB 21456-2024 家用和类似用途厨房电器能效限定值及能效等级，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-06-01，status=已废止