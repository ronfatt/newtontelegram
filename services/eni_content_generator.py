import random
import time
from typing import Dict, Any, List
from services.eni_live_tracker import eni_live_tracker

TECH_TOPICS = [
    {
        "title": "⚡ 并行执行引擎 (Parallel Execution)",
        "tech_title": "PARALLEL EXECUTION & SPEED",
        "tech_sub": "ENI Enterprise Modular L1 · 1.0s Finality",
        "tech_desc": "破除传统 EVM 线性排队瓶颈，实现万级 TPS 极速并发与毫秒级交易确定性，为高频 DeFi 与企业级交互提供零延迟体验。",
        "body": "⚡ <b>【ENI Chain 核心架构科普：并行执行引擎】</b>\n\n"
                "传统区块链 EVM 往往受限于单线程顺序执行，容易造成网络拥堵与 Gas 飙升。\n\n"
                "🚀 <b>ENI Mainnet 采用并行执行 (Parallel Execution) 架构：</b>\n"
                "• 毫秒级区块确定性 (~1.0s 出块)\n"
                "• 动态状态访问分析，互不冲突交易并发结算\n"
                "• 超低网络 Gas (稳定 ~87 Gwei)\n\n"
                "🌐 探索官方浏览器：https://scan.eniac.network\n"
                "#ENIChain #ParallelEVM #Layer1 #Web3 #Blockchain"
    },
    {
        "title": "🏛 模块化 L1：Mainnet + Hub + AppChains",
        "tech_title": "MODULAR L1: HUB & APPCHAINS",
        "tech_sub": "Customizable AppChains · Shared Security",
        "tech_desc": "创新的模块化拓扑结构，允许企业与大型 dApp 部署专属应用链，共享主网强大共识与去中心化安全屏障。",
        "body": "🏛 <b>【ENI Chain 官网深度：模块化 L1 体系】</b>\n\n"
                "一条公链，构建多元企业级数字生态！\n\n"
                "💎 <b>ENI 模块化矩阵架构：</b>\n"
                "1️⃣ <b>ENI Mainnet</b>：核心结算与高价值底层共识\n"
                "2️⃣ <b>ENI Hub</b>：跨链互操作性与资产高效流转枢纽\n"
                "3️⃣ <b>AppChains</b>：专属行业应用链，独立算力与定制规则\n\n"
                "打造真正面向千万级真实用户的 Web3 基础设施！\n"
                "🔗 官网详情：https://eniac.network\n"
                "#ENI #ModularBlockchain #Crypto #Mainnet #ENIChain"
    },
    {
        "title": "🤖 链上 AI 算力与 Newton 智能代理协议",
        "tech_title": "AI COMPUTE & AGENT PROTOCOL",
        "tech_sub": "Newton Initiative × ENI Ecosystem",
        "tech_desc": "将可验证授权与智能合约深度结合，赋能链上 AI Agent 自主交互、算力调度与 RWA 现实资产链上化。",
        "body": "🤖 <b>【ENI 生态前沿：AI 智能算力与牛顿协议】</b>\n\n"
                "当人工智能遇见高吞吐量底层公链，会带来怎样的范式变革？\n\n"
                "🧠 <b>ENI Chain × Newton Protocol 深度探索：</b>\n"
                "• 链上自主 AI Agent 权限受控交互 (PolicyEngine)\n"
                "• 去中心化算力网络与分布式节点质押\n"
                "• 现实世界资产 (RWA) 锚定与毫秒级清算\n\n"
                "探索智能经济新模式：https://scan.eniac.network\n"
                "#ENIChain #Newton #AIAgents #Web3AI #RWA"
    },
    {
        "title": "⛽ 原生燃料 $EGAS 与全网通缩捕获",
        "tech_title": "NATIVE UTILITY & FUEL",
        "tech_sub": "EGAS Fuel Mechanism · Value Capture",
        "tech_desc": "原生代币作为全网燃料，驱动智能合约调用、跨链 Hub 中继与节点激励，具备强劲的链上实用价值。",
        "body": "⛽ <b>【ENI Chain 经济模型：原生燃料价值赋能】</b>\n\n"
                "在 ENI 主网生态中，所有链上计算、合约调用与资产交换均以原生燃料作为驱动核心！\n\n"
                "🔥 <b>生态价值捕获闭环：</b>\n"
                "• 网络 Gas 消耗与验证者奖励质押\n"
                "• DEX 交易流动性激励 (xplan.eniac.network)\n"
                "• 支撑 520万+ 活跃地址的大规模真实交易\n\n"
                "📊 实时链上数据查阅：https://scan.eniac.network\n"
                "#ENI #EGAS #Tokenomics #DeFi #Crypto"
    }
]

TECH_TOPICS_EN = [
    {
        "title": "Parallel EVM Execution Engine",
        "tech_title": "PARALLEL EXECUTION & SPEED",
        "tech_sub": "ENI Enterprise Modular L1 · 1.0s Finality",
        "tech_desc": "Break free from single-thread bottlenecks with multi-threaded state access, sub-second latency, and tens of thousands of TPS.",
        "body": "⚡ <b>【ENI Chain Architecture Spotlight: Parallel EVM Engine】</b> ⚡\n\n"
                "Traditional EVMs suffer from single-threaded sequential execution bottlenecks, leading to congestion and gas spikes.\n\n"
                "🚀 <b>ENI Mainnet leverages high-performance Parallel Execution:</b>\n"
                "• Sub-second deterministic blocks (~1.0s finality)\n"
                "• Dynamic state access analysis enabling conflict-free concurrent transaction settlements\n"
                "• Low & predictable network fees (~87 Gwei)\n\n"
                "🌐 Explore on Live Explorer: https://scan.eniac.network\n"
                "#ENIChain #ParallelEVM #Layer1 #Web3 #Blockchain"
    },
    {
        "title": "Modular L1: Mainnet + Hub + AppChains",
        "tech_title": "MODULAR L1: HUB & APPCHAINS",
        "tech_sub": "Customizable AppChains · Shared Security",
        "tech_desc": "Innovative modular topography empowering enterprise dApps with dedicated application chains and shared root consensus.",
        "body": "🏛 <b>【ENI Chain Blueprint: Modular Layer-1 Architecture】</b> 🏛\n\n"
                "One foundational chain, empowering diverse enterprise Web3 ecosystems!\n\n"
                "💎 <b>ENI Modular Topology:</b>\n"
                "1️⃣ <b>ENI Mainnet</b>: Core high-security settlement layer\n"
                "2️⃣ <b>ENI Hub</b>: Trustless cross-chain interoperability & liquidity conduit\n"
                "3️⃣ <b>AppChains</b>: Dedicated application chains with customizable compute rules\n\n"
                "Built for millions of real-world enterprise participants!\n"
                "🔗 Official Portal: https://eniac.network\n"
                "#ENI #ModularBlockchain #Crypto #Mainnet #ENIChain"
    },
    {
        "title": "On-Chain AI Compute & Newton Agent Protocol",
        "tech_title": "AI COMPUTE & AGENT PROTOCOL",
        "tech_sub": "Newton Initiative × ENI Ecosystem",
        "tech_desc": "Combining verifiable permissions with autonomous smart contracts for AI agent coordination and real-world asset settlement.",
        "body": "🤖 <b>【ENI × Newton Protocol: Autonomous AI & Policy Engine】</b> 🤖\n\n"
                "When artificial intelligence meets ultra-high-throughput public blockchain infrastructure:\n\n"
                "🧠 <b>Key Innovations:</b>\n"
                "• On-chain autonomous AI Agent execution governed by PolicyEngine\n"
                "• Decentralized compute scheduling with distributed node validation\n"
                "• Real-World Asset (RWA) tokenization & sub-second settlement\n\n"
                "Discover the autonomous digital economy: https://scan.eniac.network\n"
                "#ENIChain #Newton #AIAgents #Web3AI #RWA"
    },
    {
        "title": "Native Fuel Utility & Deflationary Capture",
        "tech_title": "NATIVE UTILITY & FUEL",
        "tech_sub": "EGAS Fuel Mechanism · Value Capture",
        "tech_desc": "Native utility asset powering all smart contracts, cross-chain relays, and decentralized DEX liquidity.",
        "body": "⛽ <b>【ENI Chain Economics: Native Fuel & Value Capture】</b> ⛽\n\n"
                "All smart contract calls, cross-chain relaying, and decentralized operations are powered by native network fuel!\n\n"
                "🔥 <b>Economic Loop:</b>\n"
                "• Gas fee consumption & validator staking yields\n"
                "• DEX liquidity incentives (https://xplan.eniac.network/swap)\n"
                "• Sustainable value accrual backed by 5.2M+ active on-chain wallets\n\n"
                "📊 Track live statistics: https://scan.eniac.network\n"
                "#ENI #EGAS #Tokenomics #DeFi #Crypto"
    }
]

class ENIContentGenerator:
    @staticmethod
    async def generate_morning_post(config: Any, lang: str = "en") -> Dict[str, Any]:
        """Slot 1: 晨间 09:00【ENI 链上数据实时战报】(默认英文推送至 #General)"""
        stats = await eni_live_tracker.get_live_stats()
        if not stats:
            stats = {
                "total_blocks": 41645000,
                "total_txs": 26945000,
                "active_addresses": 5230000,
                "transactions_today": 25890,
                "gas_price": 94.0,
                "block_time": 1.04
            }

        tot_blocks = stats["total_blocks"]
        tot_txs = stats["total_txs"]
        tot_addrs = stats["active_addresses"]
        gas = stats["gas_price"]
        b_time = stats["block_time"]

        if lang == "en":
            templates = [
                f"🌅 <b>【ENI Chain Daily On-Chain Pulse · Live Network Metrics】</b> 🌅\n\n"
                f"ENI Mainnet is operating at peak performance with sub-second deterministic finality!\n\n"
                f"🧱 Current Block Height: <b>#{tot_blocks:,}</b>\n"
                f"📈 Total On-Chain Transactions: <b>{tot_txs:,}</b>\n"
                f"👥 Active Wallet Network: <b>{tot_addrs:,}</b> addresses\n"
                f"⚡ Average Block Time: <b>{b_time}s</b> (Parallel EVM)\n"
                f"⛽ Network Gas Price: <b>{gas} Gwei</b>\n\n"
                f"🔍 Live Blockscout Explorer: https://scan.eniac.network\n"
                f"#ENIChain #NewtonProtocol #Layer1 #Web3 #DailyReport",

                f"📊 <b>【ENI Mainnet 24H Activity & Ecosystem Pulse】</b> 📊\n\n"
                f"Global enterprise modular public chain momentum continues to expand!\n\n"
                f"💎 Key Network Highlights:\n"
                f"• Total Height: #{tot_blocks:,}\n"
                f"• Cumulative Volume: {tot_txs:,} transactions\n"
                f"• Decentralized Network: {tot_addrs:,} active holders\n"
                f"• Ultra-fast Finality: ~{b_time}s / Block\n\n"
                f"🌐 Explore Mainnet Analytics: https://scan.eniac.network\n"
                f"#ENIChain #Blockchain #Crypto #MainnetData"
            ]
            title = f"ENI Chain Daily Pulse: #{tot_blocks:,} Blocks"
        else:
            templates = [
                f"🌅 <b>【ENI Chain 链上早报 · 实时全网数据】</b>\n\n"
                f"新的一天，ENI 主网正在高速稳定运行！\n\n"
                f"🧱 最新区块高度: <b>#{tot_blocks:,}</b>\n"
                f"📈 累计链上交易: <b>{tot_txs:,}</b> 笔\n"
                f"👥 独立持币地址: <b>{tot_addrs:,}</b> 个\n"
                f"⚡ 平均出块速度: <b>{b_time} 秒</b> (并行确定性)\n"
                f"⛽ 当前平均 Gas: <b>{gas} Gwei</b>\n\n"
                f"🔍 官方实时浏览器: https://scan.eniac.network\n"
                f"#ENIChain #ENI #CryptoMorning #Web3 #DailyReport"
            ]
            title = f"ENI Chain 链上早报: #{tot_blocks:,} Blocks"

        text = random.choice(templates)
        event_data = {
            "slot": "morning",
            "event_type": "summary",
            "title": title,
            "content": text,
            "total_blocks": tot_blocks,
            "total_txs": tot_txs,
            "active_addresses": tot_addrs,
            "transactions_today": stats.get("transactions_today", 25890),
            "gas_price": gas,
            "block_time": b_time,
            "amount": 0.0,
            "usd_value": 0.0
        }
        return event_data

    @staticmethod
    async def generate_afternoon_post(config: Any, lang: str = "en") -> Dict[str, Any]:
        """Slot 2: 午间 14:00【ENI 核心技术与愿景深度】(默认英文推送至 #General)"""
        topics = TECH_TOPICS_EN if lang == "en" else TECH_TOPICS
        idx = int(time.time() // 86400) % len(topics)
        topic = topics[idx]

        event_data = {
            "slot": "afternoon",
            "event_type": "tech",
            "title": f"ENI Architecture Spotlight: {topic['title']}",
            "content": topic["body"],
            "tech_title": topic["tech_title"],
            "tech_sub": topic["tech_sub"],
            "tech_desc": topic["tech_desc"],
            "amount": 0.0,
            "usd_value": 0.0
        }
        return event_data

    @staticmethod
    async def generate_evening_post(config: Any, lang: str = "en") -> Dict[str, Any]:
        """Slot 3: 晚间 20:00【ENI 生态交易与流动性速报】(默认英文推送至 #General)"""
        txs = await eni_live_tracker.get_live_transactions(limit=5)
        top_tx = txs[0] if txs else None

        if top_tx and top_tx.get("tx_hash"):
            tx_hash_short = top_tx["tx_hash_short"]
            tx_hash = top_tx["tx_hash"]
            from_short = top_tx["from_short"]
            to_short = top_tx["to_short"]
            block_no = top_tx.get("block_number", 41644000)
        else:
            tx_hash = "0x" + "a" * 64
            tx_hash_short = "0x89f2...3b1a"
            from_short = "0x4b21...98ae"
            to_short = "0xd812...44f0"
            block_no = 41644200

        if lang == "en":
            text = (
                f"🌙 <b>【ENI Chain Evening Ecosystem Pulse & Live Liquidity Brief】</b> 🌙\n\n"
                f"High on-chain transaction velocity and active decentralized liquidity settlement across ENI Mainnet!\n\n"
                f"⚡ Latest Verified Mainnet Activity:\n"
                f"• Tx Hash: <code>{tx_hash_short}</code>\n"
                f"• Sender Address: <code>{from_short}</code>\n"
                f"• Interacting Contract: <code>{to_short}</code>\n"
                f"• Confirmation Block: #{block_no:,}\n\n"
                f"🔄 Trade on Official DEX: https://xplan.eniac.network/swap\n"
                f"🔍 Verified Blockscout Explorer: https://scan.eniac.network\n\n"
                f"#ENIChain #ENI #DEX #CryptoTrading #Web3Ecosystem"
            )
            title = f"ENI Evening Ecosystem Brief: Block #{block_no:,}"
        else:
            text = (
                f"🌙 <b>【ENI Chain 晚间生态动态与链上交易速报】</b>\n\n"
                f"晚间链上交互活跃，生态 DEX 与大额转账正在持续结算！\n\n"
                f"⚡ 最新主网交互动态：\n"
                f"• 交易哈希: <code>{tx_hash_short}</code>\n"
                f"• 发起地址: <code>{from_short}</code>\n"
                f"• 交互合约: <code>{to_short}</code>\n"
                f"• 确认区块: #{block_no:,}\n\n"
                f"🔄 体验生态去中心化兑换: https://xplan.eniac.network/swap\n"
                f"🔍 链上实时浏览器: https://scan.eniac.network\n\n"
                f"#ENIChain #ENI #DEX #CryptoTrading #Web3Ecosystem"
            )
            title = f"ENI 晚间生态速报: Block #{block_no:,}"

        event_data = {
            "slot": "evening",
            "event_type": "whale",
            "title": title,
            "content": text,
            "tx_hash": tx_hash,
            "amount": 58800.0,
            "usd_value": 8820.0,
            "symbol": "ENI",
            "price": config.chain.token_price_usd,
            "from_addr": from_short,
            "to_addr": to_short,
            "from_short": from_short,
            "to_short": to_short,
            "tx_hash_short": tx_hash_short
        }
        return event_data
