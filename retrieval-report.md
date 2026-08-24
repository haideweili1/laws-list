# 自动检索质检报告（2026-08-24）

> 测量仪表：左栏(可直接应用)应尽量多、右栏(自动丢弃)应只剩真垃圾。逐类压降下面 discard 的分类，可应用才会变多。

## 计数
- 可直接应用（左栏）：**2**
- 自动丢弃（右栏）：**1**
- 状态切换：**0**

## 自动丢弃「为什么被丢」分类（训练瞄准镜）
- 无来源且系统也解析不到（须落地 name_query/cfsa）：1

## 质量测量（Step⑤：推送后直接看这 4 个数是否下降）
- 伪废止·无依据直接丢弃（本应归零）：**0**
- 发布日期误填实施日期（本应归零）：**0**
- 重复重报早已做过的变更（本应归零）：**16**
- 跨文件废止命中（越多越好）：**0**

## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0A6F6D2A8C8F4E3B9C7D6E5F4A3B2C1D → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=8D9D545E31B5D9912134BFFBA4409B7A｜内容待人工确认
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2C8H8N4C0E0H6G5D1F9G8H6D4E3F2G1H → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=E2BBC7015B075B8AE7C3F3AA4D6A7340｜内容待人工确认

## 丢弃条目明细
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》：依据来源不是正文页（搜索页/列表页/伪造格式）：https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4E0J0P6E2G2J8I7F3B1I0J8F5G4H3I2J；系统按官方渠道自动解析也未取到真实链接（现有链接核验失败（死链/超时），建议重查）；声称原状态是「已废止」，清单里其实是「现行有效」；判定为废止，却给不出官方写明的废止日期