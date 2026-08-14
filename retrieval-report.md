# 自动检索质检报告（2026-08-14）

> 测量仪表：右栏(人工复核)是诊断信号。逐类压降下面 reject 的分类，才能让它归零。

## 计数
- 可直接应用（左栏）：**0**
- 人工复核（右栏）：**16**
- 丢弃：**5**
- 状态切换：**0**

## 右栏「为什么被拒」分类（训练瞄准镜）
- 系统已补正链接，内容待人工确认（分诊自救成功）：16
- 旧值核对不符（未看清单）：1

## 丢弃「为什么被丢」分类
- 无来源且系统也解析不到（须落地 name_query/cfsa）：5

## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）
- 《中华人民共和国传染病防治法（2025修订）》[reuse_existing]：GLM 原本给的是 https://www.npc.gov.cn/npc/c30834/202403/75baf2b8b5f84e7a9b6b4f8b8b8b8b8b.shtml → 系统解析到 http://www.npc.gov.cn/c2/c30834/202504/t20250430_445085.html｜内容待人工确认
- 《职业病分类和目录》[reuse_existing]：GLM 原本给的是 https://www.gov.cn/zhengce/zhengceku/202403/content_6931236.htm → 系统解析到 https://www.gov.cn/gongbao/2025/issue_11886/202502/content_7007111.html｜内容待人工确认
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5｜内容待人工确认
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC｜内容待人工确认
- 《GB 14866-2023 眼面防护具通用技术规范》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301｜内容待人工确认
- 《粉尘爆炸泄压规范（GB 15605-2024）》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11｜内容待人工确认
- 《生产安全事故分类与编码》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=39334B61DAD4CC7F9E412A868C567717｜内容待人工确认
- 《网络数据安全管理条例》[reuse_existing]：GLM 原本给的是 (留空) → 系统解析到 https://www.gov.cn/zhengce/content/202409/content_6977766.htm｜内容待人工确认
- 《国家网络安全事件报告管理办法》[reuse_existing]：GLM 原本给的是 (留空) → 系统解析到 https://www.cac.gov.cn/2025-09/15/c_1759583017717009.htm｜内容待人工确认
- 《小型个人信息处理者个人信息保护简化措施规定》[reuse_existing]：GLM 原本给的是 (留空) → 系统解析到 https://www.cac.gov.cn/2026-07/24/c_1786638889443160.htm｜内容待人工确认
- 《生成式人工智能服务安全管理暂行办法》[reuse_existing]：GLM 原本给的是 (留空) → 系统解析到 https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm｜内容待人工确认
- 《生成式人工智能服务安全基本要求》[reuse_existing]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F67D3F376E0A0A0FF5317FB36B32A30A｜内容待人工确认
- 《《小型个人信息处理者个人信息保护简化措施规定》》[reuse_existing]：GLM 原本给的是 (留空) → 系统解析到 https://www.cac.gov.cn/2026-07/24/c_1786638889704872.htm｜内容待人工确认
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0B3E8F3C5A2B4D6E7F8A9B0C1D2E3F4A → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8D9D545E31B5D9912134BFFBA4409B7A｜内容待人工确认
- 《GB/T 4288-2025 家用和类似用途电动洗衣机》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=A6DD817E54CC5A9C5D231F1480876CAD｜内容待人工确认
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F90B89DADC888F069B9993659D39BD4F｜内容待人工确认
- 《GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4804719D7D206D7538788BE44F54DC64｜内容待人工确认
- 《GB 21456-2024 家用和类似用途厨房电器能效限定值及能效等级》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F966E2FC4C7AB718356847B0DB1045E4｜内容待人工确认
- 《GB/T 19606-2024 家用和类似用途电器噪声限值》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=9E694A86CF9AB7D112069910B37DD217｜内容待人工确认
- 《GB/T 1019 家用和类似用途电器包装通则》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8E22434C73AF364800DFDA8CCCDC09BA｜内容待人工确认
- 《GB/T 22939.1-2025 家用和类似用途电器包装 第1部分：通用要求》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=1A9CB0EB86F26BB6BDA2B7B57275CFE9｜内容待人工确认
- 《GB/T 22939.5-2025 家用和类似用途电器包装 电动洗衣机和干衣机的特殊要求》[openstd]：GLM 原本给的是 (留空) → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=7C5776EC046C3EA9A7A3E3C0F60BDAB4｜内容待人工确认

## 右栏条目明细
- 《中华人民共和国传染病防治法（2025修订）》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=中华人民共和国传染病防治法（2025修订），effectiveDate=2025-09-01，status=现行有效，link=http://www.npc.gov.cn/c2/c30834/202504/t20250430_445085.html，domains=['环境']，category=环境与职业健康，source=全国人大常委会，adopted=False，fromValues=effectiveDate=2025-09-01，status=现行有效
- 《职业病分类和目录》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=职业病分类和目录，effectiveDate=2025-08-01，status=现行有效，link=https://www.gov.cn/gongbao/2025/issue_11886/202502/content_7007111.html，domains=['环境']，category=环境与职业健康，source=国务院，adopted=False，fromValues=effectiveDate=2025-08-01，status=现行有效
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025，stdNo=GB/T 23723.5-2025，effectiveDate=2025-08-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2025-08-01，status=现行有效
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=个体防护装备有毒有害及限量物质要求 GB 31420-2025，stdNo=GB 31420-2025，effectiveDate=2026-07-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2026-07-01，status=现行有效
- 《GB 14866-2023 眼面防护具通用技术规范》[环境与职业健康]：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；想设：name=GB 14866-2023 眼面防护具通用技术规范，stdNo=GB 14866-2023，effectiveDate=2025-01-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2025-01-01，status=现行有效
- 《粉尘爆炸泄压规范（GB 15605-2024）》[环境与职业健康]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=粉尘爆炸泄压规范（GB 15605-2024），stdNo=GB 15605-2024，effectiveDate=2026-01-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11，domains=['环境']，category=质量，source=国家市场监督管理总局，adopted=False，fromValues=effectiveDate=2026-01-01，status=现行有效
- 《生产安全事故分类与编码》[环境与职业健康]：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；想设：name=生产安全事故分类与编码，effectiveDate=2026-07-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=39334B61DAD4CC7F9E412A868C567717，domains=['环境']，category=质量，source=国家市场监督管理总局、国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2026-07-01，status=现行有效
- 《网络数据安全管理条例》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=网络数据安全管理条例，effectiveDate=2025-01-01，status=现行有效，link=https://www.gov.cn/zhengce/content/202409/content_6977766.htm，domains=['信息安全']，category=信息安全，source=国务院，adopted=False，fromValues=effectiveDate=2025-01-01，status=现行有效
- 《国家网络安全事件报告管理办法》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=国家网络安全事件报告管理办法，effectiveDate=2025-11-01，status=现行有效，link=https://www.cac.gov.cn/2025-09/15/c_1759583017717009.htm，domains=['信息安全']，category=信息安全，source=国家互联网信息办公室，adopted=False，fromValues=effectiveDate=2025-11-01，status=现行有效
- 《小型个人信息处理者个人信息保护简化措施规定》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=小型个人信息处理者个人信息保护简化措施规定，effectiveDate=2026-09-01，status=现行有效，link=https://www.cac.gov.cn/2026-07/24/c_1786638889443160.htm，domains=['信息安全']，category=信息安全，source=国家互联网信息办公室，adopted=False，fromValues=effectiveDate=2026-09-01，status=现行有效
- 《生成式人工智能服务安全管理暂行办法》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=生成式人工智能服务安全管理暂行办法，effectiveDate=2023-08-15，status=现行有效，link=https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm，domains=['信息安全']，category=信息安全，source=国家互联网信息办公室，adopted=False，fromValues=effectiveDate=2023-08-15，status=现行有效
- 《生成式人工智能服务安全基本要求》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=生成式人工智能服务安全基本要求，effectiveDate=2025-11-01，status=现行有效，link=https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F67D3F376E0A0A0FF5317FB36B32A30A，domains=['信息安全']，category=信息安全，source=国家市场监督管理总局、国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2025-11-01，status=现行有效
- 《《小型个人信息处理者个人信息保护简化措施规定》》[信息安全]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=《小型个人信息处理者个人信息保护简化措施规定》，effectiveDate=2024-08-15，status=现行有效，link=https://www.cac.gov.cn/2026-07/24/c_1786638889704872.htm，domains=['信息安全']，category=信息安全，source=国家互联网信息办公室，adopted=False，fromValues=effectiveDate=2024-08-15，status=现行有效
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[产品标准]：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；想设：name=GB/T 4288-2018 家用和类似用途电动洗衣机，stdNo=GB/T 4288-2018，effectiveDate=2018-10-01，abolishDate=2026-05-01，status=已废止，link=https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8D9D545E31B5D9912134BFFBA4409B7A，remark=即将被 GB/T 4288-2025 替代（新标准实施日期 2026-05-01），domains=['质量']，category=质量，replacedBy=GB/T 4288-2025 家用和类似用途电动洗衣机，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-10-01，status=已废止
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[产品标准]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；声称原状态是「已废止」，清单里其实是「现行有效」；想设：name=GB 12021.4-2013 电动洗衣机能效水效限定值及等级，stdNo=GB 12021.4-2013，effectiveDate=2013-10-01，abolishDate=2027-04-01，status=已废止，link=https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F90B89DADC888F069B9993659D39BD4F，remark=即将被 GB 12021.4-2026 替代（新标准实施日期 2027-04-01），domains=['能源']，category=质量，replacedBy=GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2013-10-01，status=已废止
- 《GB/T 1019 家用和类似用途电器包装通则》[产品标准]：系统已解析出真实官方链接，但页面上未能自动读出实施日期，请人工点开确认；想设：name=GB/T 1019 家用和类似用途电器包装通则，stdNo=GB/T 1019，effectiveDate=2009-05-01，abolishDate=2025-11-01，status=已废止，link=https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8E22434C73AF364800DFDA8CCCDC09BA，remark=即将被 GB/T 22939.1-2025 替代（新标准实施日期 2025-11-01），domains=['包装']，category=质量，replacedBy=GB/T 22939.1-2025 家用和类似用途电器包装 第1部分：通用要求，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2009-05-01，status=已废止

## 丢弃条目明细
- 《中华人民共和国突发事件应对法》：依据来源链接形态疑似编造（非官方格式/含规律ID，必为照搬）：https://www.npc.gov.cn/npc/c30834/202403/75baf2b8b5f84e7a9b6b4f8b8b8b8b8b.shtml；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（npc.gov.cn），留空待补）
- 《中华人民共和国食品安全法》：依据来源链接形态疑似编造（非官方格式/含规律ID，必为照搬）：https://www.npc.gov.cn/npc/c30834/202403/75baf2b8b5f84e7a9b6b4f8b8b8b8b8b.shtml；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）
- 《中华人民共和国网络安全法》：没有提供依据来源网址（source_url）；系统按官方渠道自动解析也未取到真实链接（站内搜索未找到标题匹配的官方页（npc.gov.cn），留空待补）
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）
- 《GB/T 19606-2004 家用和类似用途电器噪声限值》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）；声称原状态是「已废止」，清单里其实是「现行有效」