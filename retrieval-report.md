# 自动检索质检报告（2026-08-24）

> 测量仪表：右栏(人工复核)是诊断信号。逐类压降下面 reject 的分类，才能让它归零。

## 计数
- 可直接应用（左栏）：**0**
- 人工复核（右栏）：**3**
- 丢弃：**10**
- 状态切换：**0**

## 右栏「为什么被拒」分类（训练瞄准镜）
- 其它：2
- 系统已补正链接，内容待人工确认（分诊自救成功）：1
- 旧值核对不符（未看清单）：1

## 丢弃「为什么被丢」分类
- 理由缺失/不自洽：6
- 无来源且系统也解析不到（须落地 name_query/cfsa）：3
- 系统已补正链接，内容待人工确认（分诊自救成功）：1

## 质量测量（Step⑤：推送后直接看这 4 个数是否下降）
- 伪废止·无依据直接丢弃（本应归零）：**0**
- 发布日期误填实施日期（本应归零）：**0**
- 重复重报早已做过的变更（本应归零）：**14**
- 跨文件废止命中（越多越好）：**0**

## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）
- 《职业病分类和目录》[reuse_existing]：GLM 原本给的是 http://www.gov.cn/zhengce/2024-03/15/content_6931236.htm → 系统解析到 https://www.gov.cn/gongbao/2025/issue_11886/202502/content_7007111.html｜内容已核对一致，可直接应用
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=54A5358F7925AEB1941F11D4A90F2AD5｜内容待人工确认
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=abcdef1234567890abcdef1234567890 → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC｜内容待人工确认
- 《粉尘爆炸泄压规范（GB 15605-2024）》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=abcdef1234567890abcdef1234567890 → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11｜内容待人工确认
- 《中华人民共和国网络安全法》[reuse_existing]：GLM 原本给的是 https://www.gov.cn/zhengce/2024-09/24/content_6947960.htm → 系统解析到 https://www.cac.gov.cn/2016-11/07/c_1119867116.htm｜内容待人工确认
- 《网络数据安全管理条例》[reuse_existing]：GLM 原本给的是 https://www.gov.cn/zhengce/2024-09/24/content_6947960.htm → 系统解析到 https://www.gov.cn/zhengce/content/202409/content_6977766.htm｜内容已核对一致，可直接应用
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0B3E8F3C5A2B4D6E7F8A9B0C1D2E3F4A → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8D9D545E31B5D9912134BFFBA4409B7A｜内容待人工确认
- 《GB/T 4288-2025 家用和类似用途电动洗衣机》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1C2D3E4F5A6B7C8D9E0F1A2B3C4D5E6F → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=A6DD817E54CC5A9C5D231F1480876CAD｜内容待人工确认
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F90B89DADC888F069B9993659D39BD4F｜内容待人工确认
- 《GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=4804719D7D206D7538788BE44F54DC64｜内容待人工确认
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=E2BBC7015B075B8AE7C3F3AA4D6A7340｜内容待人工确认
- 《GB 21456-2024 家用和类似用途厨房电器能效限定值及能效等级》[openstd]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B → 系统解析到 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F966E2FC4C7AB718356847B0DB1045E4｜内容待人工确认

## 右栏条目明细
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[产品标准]：官方页未标注实施日期，原填实施日期已清空待核；想设：name=GB/T 4288-2018 家用和类似用途电动洗衣机，stdNo=GB/T 4288-2018，abolishDate=2026-05-01，status=已废止，link=已有，remark=即将被 GB/T 4288-2025 替代（新标准实施日期 2026-05-01），domains=['质量']，category=质量，replacedBy=GB/T 4288-2025 家用和类似用途电动洗衣机，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-10-01，status=已废止
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[产品标准]：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；声称原状态是「已废止」，清单里其实是「现行有效」；想设：name=GB 12021.4-2013 电动洗衣机能效水效限定值及等级，stdNo=GB 12021.4-2013，effectiveDate=2013-10-01，abolishDate=2027-04-01，status=已废止，link=已有，remark=即将被 GB 12021.4-2026 替代（新标准实施日期 2027-04-01），domains=['环境']，category=环境，replacedBy=GB 12021.4-2026 电动洗衣机和洗干一体机能效水效限定值及等级，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2013-10-01，status=已废止
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[产品标准]：官方页未标注实施日期，原填实施日期已清空待核；想设：name=GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级，stdNo=GB 24849-2017，abolishDate=2025-09-01，status=已废止，link=已有，remark=即将被 GB 21456-2024 替代（新标准实施日期 2025-09-01），domains=['环境']，category=环境，replacedBy=GB 21456-2024 家用和类似用途厨房电器能效限定值及能效等级，source=国家标准化管理委员会，adopted=False，fromValues=effectiveDate=2018-06-01，status=已废止

## 丢弃条目明细
- 《中华人民共和国突发事件应对法》：理由里说改实施日期，实际却没给出日期
- 《中华人民共和国传染病防治法》：理由里说改实施日期，实际却没给出日期
- 《中华人民共和国食品安全法》：理由里说改实施日期，实际却没给出日期
- 《中山市排水管理条例》：依据来源确认失效（HTTP 502），多半是编造的链接：http://www.zsrd.gov.cn/zsgov/rdwh/202403/t20240315_1234567.htm；系统按官方渠道自动解析也未取到真实链接（无号法规按名称+部门查询待落地：留空待补）；理由里说改实施日期，实际却没给出日期
- 《《起重机 安全使用 第5部分-桥式和门式起重机》GB/T 23723.5-2025》：官方页未标注实施日期，无法自动填写；理由里说改实施日期，实际却没给出日期
- 《个体防护装备有毒有害及限量物质要求 GB 31420-2025》：官方页未标注实施日期，无法自动填写；理由里说改实施日期，实际却没给出日期
- 《GB 14866-2023 眼面防护具通用技术规范》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）；理由里说改实施日期，实际却没给出日期
- 《粉尘爆炸泄压规范（GB 15605-2024）》：系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认；理由里说改实施日期，实际却没给出日期
- 《生产安全事故分类与编码》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=1234567890abcdef1234567890abcdef；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）；理由里说改实施日期，实际却没给出日期
- 《中华人民共和国网络安全法》：官方页未标注实施日期，无法自动填写；理由里说改实施日期，实际却没给出日期