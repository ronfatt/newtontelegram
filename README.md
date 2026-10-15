# 🚀 ENI Chain 自动化发帖管理平台 (Telegram & Twitter/X)

专为 **ENI Chain (Mainnet ChainID: 173)** 与 **Newton Protocol（牛顿计划）** 生态打造的全自动链上数据监测、国际加密要闻聚合与社交网络发布平台。

官方数据源已深度直连官方区块浏览器：**[https://scan.eniac.network/](https://scan.eniac.network/)** 及官方高性能 RPC 节点 **`https://rpc.eniac.network`**。

---

## 🌟 核心特性与模块

### 1. ⚡ ENI Mainnet 真实链上数据直连与监控 (`scan.eniac.network`)
- **真实链上高度与指标**：直连官方 Blockscout v2 API，实时获取 **41,500,000+** 块高、**26,900,000+** 笔链上交易、**5,220,000+** 独立持币地址以及实时动态 Gas 费用。
- **实时交易流监听**：直接接入主网实时出块与交易列表，秒级识别大额流转（Whale Alert）与代币交换。
- **EVM JSON-RPC 直连**：直连官方 Mainnet RPC (`https://rpc.eniac.network`，ChainID: 173)，毫秒级获取最新区块与合约日志。

### 2. 📅 ENI Chain 每日 3 篇自动发推引擎 (Daily 3 Posts Engine)
系统默认开启每日 3 篇自动调度计划，内容全方位锚定 ENI Chain，自动配图并推送到 Twitter/X：
- 🌅 **晨间 09:00【ENI 链上数据实时战报】**：抓取 `scan.eniac.network` 最真实的 41.5M+ 块高、26.9M+ 交易总量、5.2M+ 活跃地址与当前 Gas，自动生成金色【24H 链上数据大盘卡片】。
- ☀️ **午间 14:00【ENI 官网深度与核心技术愿景】**：深入解读企业级模块化公链架构（并行执行 Parallel EVM 突破单线程拥堵、Mainnet+Hub+AppChains 多链拓扑、AI 算力与智能代理 Newton 协议、原生 $EGAS 燃料价值），自动生成靛蓝【核心架构与愿景卡片】。
- 🌙 **晚间 20:00【ENI 实时交易、DEX 与生态速报】**：聚焦晚间链上活跃大额流转、DEX 去中心化兑换 (`xplan.eniac.network/swap`)、质押锁仓与合作伙伴动态，自动生成【交易预警与生态卡片】。
- **自定义与手动触发**：支持在后台调整时间点，并提供一键立即触发测试按钮。

### 3. 🌍 区块链国际重大事件与快讯引擎 (Global Crypto Intel)
- **权威国际信源聚合**：实时采集 Cointelegraph、Decrypt 等顶级国际 Web3 媒体的突发新闻与宏观事件。
- **自动排版与发帖**：提取核心摘要、原文链接与时间戳，支持定时自动巡检推送或在后台控制台一键点击即时派发。
- **社交标签强化**：自动附带 `#CryptoNews #Blockchain #Web3 #Bitcoin #ENIChain` 等国际热门话题。

### 4. 🖼 专属品牌视觉预警卡片引擎 (Auto Graphic Cards)
- 内置图像渲染中枢 [`image_generator.py`](file:///Users/rms/Desktop/Newton%20ENI/Telegram%20App/image_generator.py)，自动渲染 1200×675 高清社交图文卡片：
  - ⚡ **技术架构卡片**：靛蓝主题、展示并行执行、模块化 AppChains、EGAS 燃料与官方官网。
  - 📊 **主网数据卡片**：金色主题、直观展示 41M+ 区块高度、总交易数、钱包总数与实时 Gas。
  - 🌍 **国际快讯卡片**：电光蓝主题、标题自动折行换行、来源机构、分类标签与摘要卡片。
  - 🟢 **DEX 买单卡片** / 🔴 **DEX 卖单卡片** / 🐋 **巨鲸异动卡片** / 💎 **质押流动性卡片**。

### 4. 📢 双渠道自动化派发 (Telegram & Twitter/X)
- **Telegram**：通过 Telegram Bot API 发送图文消息（`sendPhoto`），集成可交互的 `【🔍 scan.eniac.network 查看】`、`【📰 阅读全文原文】` 等内联按钮；支持 Forum 论坛话题 (Thread ID)。
- **Twitter (X.com)**：接入 Twitter API v2，自动上传生成的卡片媒体并发布推文，适配 280 字符。

### 5. 🖥 可视化 Web 控制台 (Web Console Dashboard)
- **实时仪表盘**：直观展示 ENI 主网高度横幅、RPC 状态、Telegram / Twitter 连通性与累计发帖量。
- **【⚡ ENI 真实链上监控】Tab**：实时呈现来自 `scan.eniac.network` 的真实交易流，可对任意真实链上交易一键生成预警。
- **【🌍 国际区块链要闻】Tab**：瀑布流卡片展示全球最新区块链要闻，支持一键单独发布。
- **【📝 模板与卡片定制】Tab**：在线编辑 HTML 模板文案，实时预览。

---

## 🖥 快速访问

控制台服务已在本地运行：
👉 **http://127.0.0.1:8080**

### 常用命令
```bash
cd "/Users/rms/Desktop/Newton ENI/Telegram App"

# 启动服务
./start.sh
```

---

## 📋 核心配置说明

| 参数项 | 当前设定 / 推荐值 | 说明 |
| :--- | :--- | :--- |
| **RPC 节点地址** | `https://rpc.eniac.network` | ENI Mainnet 官方 EVM JSON-RPC |
| **Chain ID** | `173` | ENI Mainnet 链 ID |
| **区块浏览器** | `https://scan.eniac.network` | 官方 Blockscout 区块链浏览器 |
| **API 接口** | `https://scan.eniac.network/api/v2` | 主网实时统计与交易接口 |
| **代币符号** | `ENI` / `EGAS` | 主网原生资产与代币标识 |
| **国际要闻轮询** | 15 分钟 | 自动检测并推送国际加密突发新闻 |
| **Telegram 配置** | `@BotFather` 获取 Token | 填入 Bot Token 与 Chat ID 即可启用 |
| **Twitter 配置** | `developer.x.com` API 凭证 | 填入 API Key/Secret 与 Access Token 即可启用 |
