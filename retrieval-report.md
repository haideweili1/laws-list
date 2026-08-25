# 自动检索质检报告（2026-08-25）

> 测量仪表：左栏(可直接应用)应尽量多、右栏(自动丢弃)应只剩真垃圾。逐类压降下面 discard 的分类，可应用才会变多。

## 计数
- 可直接应用（左栏）：**3**
- 自动丢弃（右栏）：**2**
- 状态切换：**0**

## 自动丢弃「为什么被丢」分类（训练瞄准镜）
- 其它：2

## 质量测量（Step⑤：推送后直接看这 4 个数是否下降）
- 伪废止·无依据直接丢弃（本应归零）：**0**
- 发布日期误填实施日期（本应归零）：**0**
- 重复重报早已做过的变更（本应归零）：**16**
- 跨文件废止命中（越多越好）：**0**

## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）
- 《信息安全技术 网络安全等级保护基本要求》[reuse_existing]：GLM 原本给的是 https://www.gov.cn/zhengce/2024-09/24/content_6947964.htm → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=BAFB47E8874764186BDB7865E8344DAF｜内容待人工确认
- 《GB 12021.4-2013 电动洗衣机能效水效限定值及等级》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F90B89DADC888F069B9993659D39BD4F｜内容待人工确认
- 《GB/T 19606-2004 家用和类似用途电器噪声限值》[reuse_existing]：GLM 原本给的是 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=5F6A7B8C9D0E1F2A3B4C5D6E7F8G9H0I → 系统解析到 https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=A7F4223722F84EFC3421AE7E2B6E074C｜内容待人工确认

## 丢弃条目明细
- 《GB/T 4288-2018 家用和类似用途电动洗衣机》：理由声称『由已废止改为已废止』但二者相同且清单并无此字段变化，GLM 表述与事实不符
- 《GB 24849-2017 家用和类似用途微波炉能效限定值及能效等级》：理由声称『由已废止改为已废止』但二者相同且清单并无此字段变化，GLM 表述与事实不符