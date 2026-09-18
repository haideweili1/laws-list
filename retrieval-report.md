# 自动检索质检报告（2026-09-18）

> 测量仪表：左栏(可直接应用)应尽量多、右栏(自动丢弃)应只剩真垃圾。逐类压降下面 discard 的分类，可应用才会变多。

## 计数
- 可直接应用（左栏）：**0**
- 自动丢弃（右栏）：**0**
- 状态切换：**0**

## 自动丢弃「为什么被丢」分类（训练瞄准镜）
- （无）

## 质量测量（Step⑤：推送后直接看这 4 个数是否下降）
- 伪废止·无依据直接丢弃（本应归零）：**0**
- 发布日期误填实施日期（本应归零）：**0**
- 重复重报早已做过的变更（本应归零）：**0**
- 跨文件废止命中（越多越好）：**0**

## 检索出错（异常/超时，导致该域 changes 为空；用于区分『真无变化』与『GLM 调用失败』）
- 《环境与职业健康》：检索出错: JSON 解析失败（Expecting ',' delimiter: line 87 column 6 (char 2735)）；原始返回长度=3020；原始片段：```json
{
  "changes": [
    {
      "action": "update",
      "name": "中华人民共和国安全生产法",
      "table": "laws",
      "domains": ["环境", "职业健康安全"],
      "category": "安全",
      "source": "中国政府网",
      "link": "https://www.gov.cn/zhengce/content/2021-06/01/content_5646986.htm",
      "effectiveDate": "2021-06-01",
      "status": "现行有效",
      "fromV ……[中略]…… /content_158698.htm",
      "note": "《中华人民共和国劳动合同法》自2007年6月29日起施行。"
    },
    {
      "action": "update",
      "name": "工伤保险条例",
      "table": "laws",
      "domains": ["职业健康安全"],
      "category": "安全",
      "source": "中国政府网",
      "link": "https://www.gov.cn/zhengce/content/2011-01/01/content_183798.htm",
      "effectiveDate": "2011-01-01",
- 《质量》：检索出错: JSON 解析失败（Expecting ',' delimiter: line 102 column 6 (char 2977)）；原始返回长度=3130；原始片段：```json
{
  "changes": [
    {
      "action": "update",
      "name": "中华人民共和国认证认可条例",
      "table": "laws",
      "stdNo": "",
      "docNumber": "",
      "domains": ["质量"],
      "category": "质量",
      "source": "国务院",
      "link": "https://www.gov.cn/zhengce/content/2023-07/20/content_5866484.htm",
      "effectiveDate": "2023-07-20",
      ……[中略]……      },
      "source_url": "https://www.gov.cn/zhengce/content/2021-03/01/content_5637950.htm",
      "source_hint": "",
      "replacedBy": "",
      "note": "根据国务院官网，排污许可管理条例于2021年3月1日发布，状态为现行有效。"
    },
    {
      "action": "update",
      "name": "中华人民共和国节约能源法",
      "table": "laws",
      "stdNo": "",
      "docNumber": "",
      "domains":
- 《信息安全》：检索出错: JSON 解析失败（Expecting ',' delimiter: line 117 column 6 (char 2903)）；原始返回长度=3226；原始片段：```json
{
  "changes": [
    {
      "action": "update",
      "name": "中华人民共和国网络安全法",
      "table": "laws",
      "domains": ["信息安全"],
      "category": "信息安全",
      "source": "全国人大常委会",
      "link": "空字符串",
      "effectiveDate": "2026-01-01",
      "status": "即将实施",
      "abolishDate": "",
      "adopted": false,
      "copyrightNote": "",
  ……[中略]…… 保护条例自2021年9月1日起施行，目前状态为现行有效。"
    },
    {
      "action": "update",
      "name": "网络数据安全管理条例",
      "table": "laws",
      "domains": ["信息安全"],
      "category": "信息安全",
      "source": "国务院",
      "link": "空字符串",
      "effectiveDate": "2025-01-01",
      "status": "现行有效",
      "abolishDate": "",
      "adopted": false,
      "copyrightNote":
- 《反恐》：检索出错: JSON 解析失败（Expecting ',' delimiter: line 152 column 6 (char 4493)）；原始返回长度=5013；原始片段：```json
{
  "changes": [
    {
      "action": "update",
      "name": "中华人民共和国进出口商品检验法",
      "table": "laws",
      "stdNo": "",
      "docNumber": "",
      "domains": ["反恐与供应链安全", "进出口相关"],
      "category": "反恐",
      "source": "全国人大常委会",
      "link": "https://www.gov.cn/zhengce/content/2022-12/30/content_5796484.htm",
      "effectiveDate" ……[中略]……  "进出口相关"],
      "category": "反恐",
      "source": "国务院",
      "link": "https://www.gov.cn/zhengce/content/2002-01/01/content_2826482.htm",
      "effectiveDate": "2002-01-01",
      "status": "现行有效",
      "abolishDate": "",
      "adopted": false,
      "copyrightNote": "",
      "remark": "",
      "fromValues": {
        "effectiveDate": "2002
- 《产品标准》：检索出错: JSON 解析失败（Expecting ',' delimiter: line 77 column 6 (char 2486)）；原始返回长度=2637；原始片段：```json
{
  "changes": [
    {
      "action": "update",
      "name": "GB/T 4706.32-2024家用和类似用途电器的安全 热泵、空调器和除湿机的特殊要求",
      "table": "standards",
      "stdNo": "GB/T 4706.32-2024",
      "docNumber": "",
      "domains": ["环境"],
      "category": "质量",
      "source": "国家标准化管理委员会",
      "link": "https://openstd.samr.gov.cn/newGbInfo?hcno=5F6C01 ……[中略]…… ce_url": "https://openstd.samr.gov.cn/newGbInfo?hcno=5F6C015E5F6C015E5F6C015E5F6C015E",
      "source_hint": "",
      "replacedBy": "",
      "note": "更新实施日期和状态，依据是国家标准化管理委员会发布的GB/T 4706.27-2024标准文本。"
    },
    {
      "action": "update",
      "name": "GB/T 4706.22-2024家用和类似用途电器的安全 驻立式电灶、灶台、烤箱及类似用途器具的特殊要求",
      "table": "standards",
      "std