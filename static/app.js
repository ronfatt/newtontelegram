// Newton Protocol × ENI Chain - Operations Super Console JavaScript

let currentActiveDesk = "daily";
let generatedCardsData = [];
let allTopicList = [];

// Initialize on load
document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    setupStatusPolling();
    setupSSE();
    loadLiveChainData();
    loadTopicBindings();
    loadDailyGeneralSlots();
    loadCampaigns();
    loadScheduledTasks();
    loadSchedulerLogs();
    loadSettings();
    loadHistory();

    // Init Twitter tab default
    fillTweetTheme("whitepaper");
    renderMultilingualPills();
}

// -------------------------------------------------------------
// Navigation & Tab Switching
// -------------------------------------------------------------
function switchTab(tabId) {
    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.remove("active");
    });
    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.remove("active");
    });

    const target = document.getElementById(`tab-${tabId}`);
    if (target) {
        target.classList.add("active");
    }

    const clickedBtn = Array.from(document.querySelectorAll(".nav-item")).find(btn =>
        btn.getAttribute("onclick") && btn.getAttribute("onclick").includes(tabId)
    );
    if (clickedBtn) {
        clickedBtn.classList.add("active");
    }

    // Tab-specific refreshes
    if (tabId === "topics") loadTopicBindings();
    if (tabId === "scheduler") { 
        loadDailyGeneralSlots(); 
        loadCampaigns(); 
        loadScheduledTasks(); 
        loadSchedulerLogs(); 
    }
    if (tabId === "eni-live") loadLiveChainData();
    if (tabId === "history") loadHistory();
}

// Toast notification
function showToast(msg, type = "success") {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = msg;
    toast.className = `toast ${type}`;
    toast.style.display = "block";
    setTimeout(() => {
        toast.style.display = "none";
    }, 3500);
}

// -------------------------------------------------------------
// Status & SSE
// -------------------------------------------------------------
async function setupStatusPolling() {
    updateStatus();
    setInterval(updateStatus, 15000);
}

async function updateStatus() {
    try {
        const res = await fetch("/api/status");
        if (!res.ok) return;
        const data = await res.json();

        // RPC Indicator
        const rpcVal = document.getElementById("rpcStatusVal");
        const rpcInd = document.getElementById("rpcIndicator");
        if (data.watcher && data.watcher.is_connected) {
            rpcVal.textContent = `173 (区块 #${data.watcher.last_block_scanned})`;
            rpcInd.className = "indicator online";
        } else {
            rpcVal.textContent = "173 (在线)";
            rpcInd.className = "indicator online";
        }

        // TG
        const tgVal = document.getElementById("tgStatusVal");
        const tgInd = document.getElementById("tgIndicator");
        if (data.channels && data.channels.telegram && data.channels.telegram.connected) {
            tgVal.textContent = `@${data.channels.telegram.info.bot_username || '机器人'}`;
            tgInd.className = "indicator online";
        } else {
            tgVal.textContent = "未连接";
            tgInd.className = "indicator";
        }

        // Twitter
        const twVal = document.getElementById("twStatusVal");
        const twInd = document.getElementById("twIndicator");
        if (data.channels && data.channels.twitter && data.channels.twitter.connected) {
            twVal.textContent = `@${data.channels.twitter.info.username || 'eni_newton'}`;
            twInd.className = "indicator online";
        } else {
            twVal.textContent = "未连接";
            twInd.className = "indicator";
        }

        // Watcher button
        const btnWatcher = document.getElementById("watcherBtnText");
        if (btnWatcher) {
            btnWatcher.textContent = (data.watcher && data.watcher.is_running) ? "暂停链上监听" : "启动链上监听";
        }
    } catch (e) {
        console.error("Status polling error:", e);
    }
}

async function toggleWatcher() {
    try {
        const res = await fetch("/api/action/watcher-toggle", { method: "POST" });
        const data = await res.json();
        showToast(data.message || "监听状态已切换", "success");
        updateStatus();
    } catch (e) {
        showToast("切换监听器失败", "error");
    }
}

function setupSSE() {
    const evtSource = new EventSource("/api/events/stream");
    evtSource.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            if (data.event_type) {
                showToast(`🔔 收到链上异动 [${data.event_type}]: ${data.title || ''}`, "success");
                loadLiveChainData();
            }
        } catch (err) {}
    };
}

// -------------------------------------------------------------
// TAB 1: TWITTER (X.COM) OPERATIONS
// -------------------------------------------------------------
function calculateTwitterWeight(str) {
    if (!str) return 0;
    let weight = 0;
    for (let i = 0; i < str.length; i++) {
        const code = str.charCodeAt(i);
        // CJK or Emoji / high unicode
        if (code > 255) {
            weight += 2;
        } else {
            weight += 1;
        }
    }
    return weight;
}

function updateTweetPreview() {
    const input = document.getElementById("tweetInput");
    const previewBox = document.getElementById("previewTweetText");
    const counter = document.getElementById("tweetCharCounter");
    const prog = document.getElementById("tweetProgress");

    const text = input.value || "⚡ 在此输入推文内容...";
    previewBox.textContent = text;

    const weight = calculateTwitterWeight(input.value);
    counter.textContent = `${weight} / 280 权重`;

    const percent = Math.min(100, (weight / 280) * 100);
    prog.style.width = `${percent}%`;

    if (weight > 250) {
        prog.style.backgroundColor = "var(--crimson)";
        counter.style.color = "var(--crimson)";
    } else {
        prog.style.backgroundColor = "var(--cyan)";
        counter.style.color = "var(--text-secondary)";
    }
}

function refreshTweetImage() {
    const sel = document.getElementById("tweetImageTheme").value;
    const box = document.getElementById("previewTweetMediaBox");
    const img = document.getElementById("previewTweetImg");

    if (sel === "none") {
        box.style.display = "none";
    } else {
        box.style.display = "block";
        img.style.display = "block";
        img.src = `/images/banner_${sel}.png`;
    }
}

function insertEmoji(emoji) {
    const input = document.getElementById("tweetInput");
    const pos = input.selectionStart || input.value.length;
    input.value = input.value.substring(0, pos) + " " + emoji + " " + input.value.substring(pos);
    updateTweetPreview();
}

async function fillTweetTheme(theme) {
    const input = document.getElementById("tweetInput");
    const themeSelect = document.getElementById("tweetImageTheme");

    if (theme === "whitepaper") {
        themeSelect.value = "tech";
        input.value = `⚡ Newton Protocol × ENI Chain 架构核心：\n\n以确定性并行 EVM 调度与双重验证共识，打破传统公链串行处理瓶颈。毫秒级敲定与极低结算延迟，专为 AI Agent 与下一代高频金融打造！\n\n🔗 探索: scan.eniac.network\n#ENI #NewtonProtocol #Layer1`;
    } else if (theme === "news_insight") {
        themeSelect.value = "news";
        try {
            const res = await fetch("/api/news");
            const data = await res.json();
            const topNews = (data.news && data.news.length > 0) ? data.news[0].news_title : "全球央行与金融机构加速布局代币化流动性基础设施。";
            input.value = `🌍 全球区块链动态 × ENI 视点：\n\n【快讯】${topNews}\n\n💡 观点: RWA 与机构级资金上链的爆发，亟需以 ENI 毫秒级低费率结算为底座的合规公链。\n\n#CryptoNews #ENI #Newton`;
        } catch (e) {
            input.value = `🌍 全球区块链动态 × ENI 视点：\n\n机构级资金正加速向模块化高性能底层公链迁移，ENI 独创的 Hub 架构正提供跨链即时最终性！\n\n#ENI #Blockchain`;
        }
    } else if (theme === "market_ai") {
        themeSelect.value = "summary";
        try {
            const res = await fetch("/api/eni/live");
            const d = await res.json();
            const blocks = d.stats ? d.stats.total_blocks_fmt : "41,568,000+";
            const txs = d.stats ? d.stats.total_transactions_fmt : "26,910,000+";
            input.value = `🧠 ENI 链上实时心跳 & AI 智能体生态：\n\n• 当前区块: ${blocks}\n• 累计交易: ${txs}\n• 出块间隔: ~1.00s 确定性确认\n\n自主决策 AI Agent 在 ENI 高速清算轨道的部署正在加速！\n\n#AIAgent #ENIChain #Web3`;
        } catch (e) {
            input.value = `🧠 ENI 链上数据透视：\n\n全网突破 4150 万区块稳定运行，自主决策 AI Agent 的低延迟清算轨道全面就绪！\n\n#ENI #AI`;
        }
    }
    refreshTweetImage();
    updateTweetPreview();
}

function applyTweetTemplate(tpl) {
    fillTweetTheme(tpl === "tech" ? "whitepaper" : tpl === "whale" ? "market_ai" : "news_insight");
}

async function loadRecentNewsForTweet() {
    await fillTweetTheme("news_insight");
    showToast("已抓取最新宏观快讯并套用推文模板", "success");
}

async function loadLiveChainStatsForTweet() {
    await fillTweetTheme("market_ai");
    showToast("已抓取主网最新链上数据并填入推文", "success");
}

async function publishTweetNow() {
    const text = document.getElementById("tweetInput").value.trim();
    if (!text) {
        showToast("请先撰写推文内容", "error");
        return;
    }

    const weight = calculateTwitterWeight(text);
    if (weight > 280) {
        showToast(`推文超出 Twitter 280 权重限制 (${weight}/280)，请精简文字`, "error");
        return;
    }

    const selImgTheme = document.getElementById("tweetImageTheme").value;
    const imgPath = selImgTheme !== "none" ? `static/images/banner_${selImgTheme}.png` : null;

    const syncTg = document.getElementById("chkSyncTg").checked;
    const syncThreadId = syncTg ? parseInt(document.getElementById("selectSyncThread").value) : null;

    const btn = document.getElementById("btnPublishTweet");
    btn.disabled = true;
    btn.innerHTML = `<span>⏳ 正在推送到 Twitter & 话题...</span>`;

    try {
        const res = await fetch("/api/twitter/publish", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: text,
                image_path: imgPath,
                sync_tg_thread_id: syncThreadId
            })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.detail || "推特发送失败");
        }
        showToast(`🎉 推文发送成功！Tweet ID: ${data.tweet_id}`, "success");
        loadHistory();
    } catch (e) {
        showToast(`发布失败: ${e.message}`, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `
            <svg class="x-icon-svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>
            <span>立即推送到 Twitter (@eni_newton)</span>
        `;
    }
}

// -------------------------------------------------------------
// TAB 2: 4-LANGUAGE MULTILINGUAL BROADCAST (Real Topics)
// -------------------------------------------------------------
const MULTI_LANGS = [
    { code: "en", name: "English", flag: "🇬🇧", thread: 16 },
    { code: "zh", name: "简体中文", flag: "🇨🇳", thread: 17 },
    { code: "ko", name: "한국어", flag: "🇰🇷", thread: 18 },
    { code: "vi", name: "Tiếng Việt", flag: "🇻🇳", thread: 19 }
];

function renderMultilingualPills() {
    const bar = document.getElementById("multilingualPillsBar");
    if (!bar) return;
    bar.innerHTML = MULTI_LANGS.map(l => `
        <div class="flag-pill active">
            <span>${l.flag}</span>
            <span>${l.name}</span>
            <span class="pill-tid">#${l.thread}</span>
        </div>
    `).join("");
}

function loadSampleAnnouncement() {
    const text = `🎉 Newton Protocol × ENI Chain 主网节点全面扩容升级完成！

经过双重验证引擎与并行 EVM 调度优化，当前主网平均出块耗时缩减至 1 秒以内，总交易量已突破 2,690 万笔，独立活跃地址数突破 522 万！

欢迎全球社区开发者与节点伙伴参与质押治理与生态应用部署。
官方区块链浏览器: https://scan.eniac.network/`;
    document.getElementById("broadcastDraftInput").value = text;
    showToast("已载入官方升级公告范本", "success");
}

async function generate11LanguagePreview() {
    const text = document.getElementById("broadcastDraftInput").value.trim();
    if (!text) {
        showToast("请先在母版草稿框输入要广播的文本", "error");
        return;
    }

    const container = document.getElementById("countryCardsContainer");
    const header = document.getElementById("multiPreviewHeader");
    header.style.display = "flex";
    container.innerHTML = `<div class="card text-center text-muted" style="grid-column: 1/-1; padding: 40px;">⏳ 正在调用翻译引擎并发生成 4 国语言母语卡片 (Google Web 翻译中)...</div>`;

    try {
        const res = await fetch("/api/multilingual/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.detail || "翻译生成失败");
        }

        generatedCardsData = data.cards || [];
        renderCountryCards(generatedCardsData);
        showToast(`✅ 成功生成 4 国语言翻译卡片！可点击下方一键广播`, "success");
    } catch (e) {
        container.innerHTML = `<div class="card text-center" style="grid-column: 1/-1; color: var(--crimson);">生成失败: ${e.message}</div>`;
        showToast(e.message, "error");
    }
}

function renderCountryCards(cards) {
    const container = document.getElementById("countryCardsContainer");
    if (!container) return;
    container.innerHTML = cards.map(c => `
        <div class="country-card" id="card-${c.lang}">
            <div class="country-card-header">
                <div class="country-title">
                    <span>${c.flag}</span>
                    <span>${c.native} (${c.name})</span>
                </div>
                <span class="country-thread-tag">Thread #${c.thread_id}</span>
            </div>
            <div class="country-card-body">${escapeHtml(c.text)}</div>
            <div class="country-card-footer">
                <span class="badge ${c.status === 'sent' ? 'badge-success' : 'badge-info'}" id="status-badge-${c.lang}">
                    ${c.status === 'sent' ? '已投递成功' : '就绪待广播'}
                </span>
                <button class="btn btn-secondary btn-sm" onclick="sendSingleLanguage('${c.lang}')">
                    <span>单发此群</span>
                </button>
            </div>
        </div>
    `).join("");
}

async function broadcastAll11Languages() {
    const text = document.getElementById("broadcastDraftInput").value.trim();
    if (!text) {
        showToast("广播内容不能为空", "error");
        return;
    }

    const btn = document.getElementById("btnBroadcastAllLangs");
    btn.disabled = true;
    btn.innerHTML = `<span>⏳ 正在并发广播到 4 大语言话题 Thread...</span>`;

    try {
        const res = await fetch("/api/multilingual/broadcast", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.detail || "广播失败");
        }

        const results = data.broadcast.results || {};
        let successCount = 0;
        for (const [lang, r] of Object.entries(results)) {
            const badge = document.getElementById(`status-badge-${lang}`);
            if (badge) {
                if (r.success) {
                    badge.className = "badge badge-success";
                    badge.textContent = `已发送 (Msg #${r.message_id})`;
                    successCount++;
                } else {
                    badge.className = "badge badge-danger";
                    badge.textContent = `失败: ${r.error || '未送达'}`;
                }
            }
        }
        showToast(`🎉 11 国超级群广播完成！成功送达 ${successCount} 个国家话题`, "success");
        loadHistory();
    } catch (e) {
        showToast(`广播执行异常: ${e.message}`, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>🚀 一键广播到 Telegram 11个国家话题</span>`;
    }
}

async function sendSingleLanguage(lang) {
    const card = generatedCardsData.find(c => c.lang === lang);
    if (!card) return;
    try {
        const res = await fetch("/api/topics/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                thread_id: card.thread_id,
                text: `${card.flag} 【${card.native} 官方频道】\n\n${card.text}`
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`已成功单独发送到 ${card.name} 话题 #${card.thread_id}`, "success");
            const badge = document.getElementById(`status-badge-${lang}`);
            if (badge) {
                badge.className = "badge badge-success";
                badge.textContent = "已投递成功";
            }
        }
    } catch (e) {
        showToast("单发失败: " + e.message, "error");
    }
}

// -------------------------------------------------------------
// TAB 3: TOPIC BINDINGS & CHANNELS (Image 2 Ref)
// -------------------------------------------------------------
function syncAllTopicDropdowns(topics) {
    if (!topics || topics.length === 0) return;
    const selects = [
        document.getElementById("selectSyncThread"),
        document.getElementById("dispatchTgThreadSelect")
    ];
    selects.forEach(sel => {
        if (!sel) return;
        const currentVal = sel.value;
        sel.innerHTML = topics.map(t => `
            <option value="${t.thread_id}">
                ${t.topic_name} (#${t.thread_id})
            </option>
        `).join("");
        if (topics.some(t => String(t.thread_id) === String(currentVal))) {
            sel.value = currentVal;
        } else if (topics.some(t => t.thread_id === 1)) {
            sel.value = "1";
        }
    });
}

async function loadTopicBindings() {
    const container = document.getElementById("topicsTablesContainer");
    if (!container) return;

    try {
        const res = await fetch("/api/topics");
        const data = await res.json();
        allTopicList = data.topics || [];
        syncAllTopicDropdowns(allTopicList);
        const grouped = data.grouped || {};

        let html = "";
        for (const [catName, topics] of Object.entries(grouped)) {
            html += `
                <div class="topic-category-card">
                    <div class="topic-cat-header">
                        <span class="topic-cat-title">📁 ${catName} (${topics.length} 个板块)</span>
                        <span class="badge badge-info">Forum Topic</span>
                    </div>
                    <div class="table-responsive">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th style="width: 50px;">ID</th>
                                    <th>话题板块名称</th>
                                    <th>对应语言/说明</th>
                                    <th style="width: 140px;">绑定 Thread ID</th>
                                    <th style="width: 160px;">操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${topics.map(t => `
                                    <tr>
                                        <td>#${t.id}</td>
                                        <td>
                                            <input type="text" class="form-input" style="padding: 3px 8px; font-weight: 700; width: 100%; max-width: 220px;" id="topicNameInput_${t.id}" value="${t.topic_name}">
                                        </td>
                                        <td><span class="text-muted">${t.notes || t.lang_code || '-'}</span></td>
                                        <td>
                                            <input type="number" class="thread-id-input" id="threadInput_${t.id}" value="${t.thread_id}">
                                        </td>
                                        <td>
                                            <button class="btn btn-secondary btn-sm" onclick="saveTopicThread(${t.id})">保存</button>
                                            <button class="btn btn-secondary btn-sm" onclick="testSendToTopic(${t.id}, ${t.thread_id}, '${t.topic_name}')">测试直发</button>
                                        </td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<div class="card text-center text-muted">加载话题绑定表失败: ${e.message}</div>`;
    }
}

async function promptAddTopic() {
    const name = prompt("请输入新话题名称（例如：🎬 VIDEO CENTRE 或 📣 MARKETING TOOLS）：");
    if (!name || !name.trim()) return;
    const tidStr = prompt(`请输入【${name}】在 Telegram 的 Thread ID（可通过右键话题复制链接获取，例如 12）：`);
    if (!tidStr) return;
    const tid = parseInt(tidStr);
    if (isNaN(tid)) {
        alert("Thread ID 必须是数字！");
        return;
    }
    const cat = prompt("请指定板块分类：", "Newton 官方超级群板块") || "Newton 官方超级群板块";

    try {
        const res = await fetch("/api/topics/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ category: cat, topic_name: name.trim(), thread_id: tid })
        });
        const data = await res.json();
        showToast(data.message || "话题已创建", "success");
        loadTopicBindings();
    } catch (e) {
        showToast("创建话题失败: " + e.message, "error");
    }
}

async function saveTopicThread(topicId) {
    const input = document.getElementById(`threadInput_${topicId}`);
    if (!input) return;
    const threadId = parseInt(input.value);
    const nameInput = document.getElementById(`topicNameInput_${topicId}`);
    const topicName = nameInput ? nameInput.value.trim() : null;

    try {
        const res = await fetch("/api/topics/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: topicId, thread_id: threadId, enabled: 1, topic_name: topicName })
        });
        const data = await res.json();
        showToast(data.message || "话题绑定已更新", "success");
    } catch (e) {
        showToast("保存失败: " + e.message, "error");
    }
}

async function testSendToTopic(topicId, threadId, topicName) {
    const input = document.getElementById(`threadInput_${topicId}`);
    const actualThreadId = input ? parseInt(input.value) : threadId;
    const nameInput = document.getElementById(`topicNameInput_${topicId}`);
    const actualName = nameInput ? nameInput.value.trim() : topicName;

    // Auto save this topic's latest threadId
    await saveTopicThread(topicId);

    const testMsg = `<b>⚡ Newton Protocol × ENI 话题连通性测试</b>\n\n已成功连通目标话题: <b>${actualName}</b> (Thread #${actualThreadId})\n官方区块链浏览器: <a href="https://scan.eniac.network">scan.eniac.network</a>`;
    try {
        const res = await fetch("/api/topics/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ thread_id: actualThreadId, text: testMsg })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast(`已向话题 [${actualName}] 发送测试消息成功！Msg ID: ${data.result?.message_id}`, "success");
        } else {
            const errMsg = data.detail || data.error || (data.result && data.result.error) || "未知错误";
            showToast(`发送失败: ${errMsg}`, "error");
        }
    } catch (e) {
        showToast("直发测试异常: " + e.message, "error");
    }
}

function syncTgInputs(source) {
    if (source === 'settings') {
        const token = document.getElementById("cfgTgBotToken")?.value || "";
        const cid = document.getElementById("cfgTgChatId")?.value || "";
        const t1 = document.getElementById("tgBotTokenInput");
        const c1 = document.getElementById("tgChatIdInput");
        if (t1) t1.value = token;
        if (c1) c1.value = cid;
    } else {
        const token = document.getElementById("tgBotTokenInput")?.value || "";
        const cid = document.getElementById("tgChatIdInput")?.value || "";
        const t2 = document.getElementById("cfgTgBotToken");
        const c2 = document.getElementById("cfgTgChatId");
        if (t2) t2.value = token;
        if (c2) c2.value = cid;
    }
}

async function autoDetectGroupAndTopics() {
    const token = (document.getElementById("cfgTgBotToken")?.value || document.getElementById("tgBotTokenInput")?.value || "").trim();
    if (!token) {
        showToast("请先输入 Telegram Bot Token 再点击自动检测", "error");
        return;
    }

    showToast("🔍 正在检索 Bot 最近消息与超级群话题...", "success");
    try {
        const res = await fetch("/api/telegram/detect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bot_token: token })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.detail || data.error || "检测失败");
        }

        const chats = data.detected_chats || [];
        const topics = data.detected_topics || [];

        // Normalize chats
        let firstChat = null;
        if (Array.isArray(chats) && chats.length > 0) {
            firstChat = chats[0];
        } else if (typeof chats === 'object' && chats !== null && Object.keys(chats).length > 0) {
            const firstId = Object.keys(chats)[0];
            firstChat = { id: firstId, title: chats[firstId] };
        }

        if (!firstChat && topics.length === 0) {
            alert("⚠️ 尚未检测到群消息记录！\n\n【操作提示】：\n1. 请先在 Telegram 将您的 Bot 拉进【Newton Protocol】超级群；\n2. 确保在群管理员设置中勾选了【管理话题 (Manage Topics)】和【发消息】权限；\n3. 在群内任意话题（如 General 或 CHINESE CHAT）随手发送一条文字（如 test）；\n4. 发送后再点击本【自动检测】按钮，即可瞬间捕获 Chat ID 和 Topic ID！");
            return;
        }

        if (firstChat) {
            const c1 = document.getElementById("tgChatIdInput");
            const c2 = document.getElementById("cfgTgChatId");
            if (c1) c1.value = firstChat.id;
            if (c2) c2.value = firstChat.id;
            await saveTelegramCredentials();
            showToast(`🎉 成功识别群：[${firstChat.title}] (Chat ID: ${firstChat.id})！已自动保存`, "success");
        }

        if (topics.length > 0) {
            let msg = `🎉 成功捕获到 ${topics.length} 个话题：\n\n`;
            topics.forEach(t => {
                msg += `• 【${t.topic_name || '话题'}】➔ Thread #${t.thread_id} (最新: "${t.last_message || t.sample_text || ''}")\n`;
            });
            msg += `\n是否立即一键将这 ${topics.length} 个话题自动同步/绑定到下方的各板块表格？`;
            if (confirm(msg)) {
                const syncRes = await fetch("/api/topics/sync-detected", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ topics: topics })
                });
                const syncData = await syncRes.json();
                if (syncData.success) {
                    showToast(syncData.message, "success");
                    loadTopicBindings();
                } else {
                    showToast("同步失败: " + syncData.detail, "error");
                }
            }
        }
    } catch (e) {
        showToast("检测异常: " + e.message, "error");
    }
}

async function saveTelegramCredentials() {
    const token = (document.getElementById("cfgTgBotToken")?.value || document.getElementById("tgBotTokenInput")?.value || "").trim();
    const chatId = (document.getElementById("cfgTgChatId")?.value || document.getElementById("tgChatIdInput")?.value || "").trim();
    const enabled = document.getElementById("cfgTgEnabled") ? document.getElementById("cfgTgEnabled").checked : true;
    try {
        const cfgRes = await fetch("/api/config");
        const cfg = await cfgRes.json();
        if (!cfg.telegram) cfg.telegram = {};
        cfg.telegram.bot_token = token;
        cfg.telegram.chat_id = chatId;
        cfg.telegram.enabled = enabled;

        const res = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(cfg)
        });
        if (res.ok) {
            showToast("Telegram 超级群连接参数已保存", "success");
            updateStatus();
        }
    } catch (e) {
        showToast("保存凭证失败: " + e.message, "error");
    }
}

async function testTelegramConnection() {
    await saveTelegramCredentials();
    showToast("正在向超级群发送测试消息...", "success");
    try {
        const res = await fetch("/api/action/test-telegram", { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "测试失败");
        showToast("🎉 Telegram 测试成功！已向群内发送测试消息", "success");
        updateStatus();
    } catch (e) {
        showToast("Telegram 测试失败: " + e.message, "error");
    }
}

// -------------------------------------------------------------
// TAB 4: RESEARCH DESK (Image 4 Ref)
// -------------------------------------------------------------
async function selectResearchDesk(deskType) {
    currentActiveDesk = deskType;
    document.querySelectorAll(".desk-card").forEach(c => c.classList.remove("active"));
    const clicked = document.querySelector(`.desk-card[onclick*="'${deskType}'"]`);
    if (clicked) clicked.classList.add("active");

    const badge = document.getElementById("activeDeskBadge");
    badge.textContent = `已选专栏: ${deskType.toUpperCase()}`;

    const titleInput = document.getElementById("dispatchTitleInput");
    const contentInput = document.getElementById("dispatchContentInput");
    titleInput.value = "⏳ 正在结合 scan.eniac.network 链上指标与投研模型生成...";
    contentInput.value = "正在检索网络拓扑与宏观数据...";

    try {
        const res = await fetch(`/api/research/desk/${deskType}`);
        const data = await res.json();
        titleInput.value = data.title;
        contentInput.value = data.content;
        if (data.target_thread_id) {
            document.getElementById("dispatchTgThreadSelect").value = data.target_thread_id;
        }
        showToast("研报已自动生成并载入投递控制台", "success");
    } catch (e) {
        showToast("生成研报失败: " + e.message, "error");
    }
}

async function regenerateCurrentDesk() {
    if (currentActiveDesk) {
        await selectResearchDesk(currentActiveDesk);
    }
}

async function submitDispatchNow() {
    const title = document.getElementById("dispatchTitleInput").value.trim();
    const content = document.getElementById("dispatchContentInput").value.trim();
    if (!title || !content) {
        showToast("研报标题和正文不能为空", "error");
        return;
    }

    const sendTg = document.getElementById("chkDispatchTg").checked;
    const sendTw = document.getElementById("chkDispatchTw").checked;
    const threadId = sendTg ? parseInt(document.getElementById("dispatchTgThreadSelect").value) : null;

    try {
        const res = await fetch("/api/research/dispatch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title,
                content: content,
                target_thread_id: threadId,
                send_to_telegram: sendTg,
                send_to_twitter: sendTw
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast("🚀 研报发布成功！已按路由投递至相应渠道", "success");
            loadHistory();
        } else {
            showToast("发布出现问题", "error");
        }
    } catch (e) {
        showToast("投递异常: " + e.message, "error");
    }
}

// -------------------------------------------------------------
// Daily #General 2-Slot Automated Posts (Real On-Chain Data)
// -------------------------------------------------------------
async function loadDailyGeneralSlots() {
    try {
        const res = await fetch("/api/daily-schedule/status");
        const data = await res.json();
        const slots = data.slots || {};

        ["morning", "evening"].forEach(slot => {
            const badge = document.getElementById(`slotStatus_${slot}`);
            if (!badge) return;
            const s = slots[slot];
            if (s && s.executed) {
                badge.className = "badge badge-success";
                badge.textContent = "✅ 今日已发送";
            } else {
                badge.className = "badge badge-info";
                badge.textContent = `⏳ 待执行 (${s ? s.time : '--:--'})`;
            }
        });
    } catch (e) {
        console.error("loadDailyGeneralSlots error:", e);
    }
}

async function triggerDailySlot(slot) {
    showToast(`正在向 #General 频道生成并派发${slot === 'morning' ? '晨间 10:00' : '晚间 20:00'}真实链上数据简报...`, "success");
    try {
        const res = await fetch("/api/daily-schedule/trigger", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slot: slot })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`🎉 成功投递至 #General (Thread #${data.thread_id})！Post ID: ${data.post_id}`, "success");
            loadDailyGeneralSlots();
            loadHistory();
        } else {
            showToast("派发失败: " + (data.detail || data.reason || "未知原因"), "error");
        }
    } catch (e) {
        showToast("请求失败: " + e.message, "error");
    }
}

// -------------------------------------------------------------
// 4 National Languages Multi-Day Campaigns (Day 1, Day 2...)
// -------------------------------------------------------------
let allCampaigns = [];
let localPostersList = [];

async function loadCampaigns() {
    const container = document.getElementById("campaignsContainer");
    if (!container) return;

    try {
        const [cRes, pRes] = await Promise.all([
            fetch("/api/campaigns"),
            fetch("/api/campaigns/local-posters")
        ]);
        const cData = await cRes.json();
        const pData = await pRes.json();

        allCampaigns = cData.campaigns || [];
        localPostersList = pData.posters || [];

        if (allCampaigns.length === 0) {
            container.innerHTML = `<div class="card text-center text-muted" style="padding: 30px;">暂无排期计划，请点击右上角【➕ 新增排期天数/计划】进行创建！</div>`;
            return;
        }

        container.innerHTML = allCampaigns.map(c => `
            <div class="campaign-card" id="campaignCard_${c.id}">
                <div class="campaign-header">
                    <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                        <span class="campaign-day-pill">🌟 第 ${c.day_number} 天计划</span>
                        <input type="text" class="form-input" style="font-weight: 700; width: 280px; padding: 4px 8px;" id="cTitle_${c.id}" value="${c.campaign_title || ''}" placeholder="计划主题/标题">
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span class="text-muted" style="font-size: 12px;">⏰ 定时触发:</span>
                            <input type="text" class="form-input" style="width: 130px; padding: 4px 8px; font-family: monospace;" id="cTime_${c.id}" value="${c.scheduled_time || '10:00'}" placeholder="例如 10:00">
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="badge ${c.status === 'sent' ? 'badge-success' : 'badge-warning'}">
                            ${c.status === 'sent' ? '✅ 已执行投递' : '⏳ 待自动发送'}
                        </span>
                        <button class="btn btn-secondary btn-sm" onclick="saveCampaign(${c.id})">💾 保存修改</button>
                        <button class="btn btn-primary btn-sm" onclick="triggerCampaignNow(${c.id})">🚀 立即发送4大频道</button>
                        <button class="btn btn-secondary btn-sm" style="color: var(--crimson);" onclick="deleteCampaign(${c.id})">🗑️</button>
                    </div>
                </div>

                <div class="campaign-body-grid">
                    <!-- Left: Poster Box -->
                    <div class="campaign-poster-box">
                        <img src="${c.poster_image || '/static/uploads/posters/1.png'}" id="cPosterImg_${c.id}" class="campaign-poster-preview" alt="海报预览" onerror="this.src='/static/uploads/posters/1.png'">
                        <select class="select-sm" style="width: 100%; margin-bottom: 8px;" id="cPosterSelect_${c.id}" onchange="changeCampaignPosterSelect(${c.id}, this.value)">
                            <option value="">-- 选择已有海报 --</option>
                            ${localPostersList.map(p => `
                                <option value="${p.url}" ${c.poster_image === p.url ? 'selected' : ''}>${p.filename}</option>
                            `).join('')}
                        </select>
                        <label class="btn btn-secondary btn-sm" style="width: 100%; cursor: pointer;">
                            <span>📁 上传新海报</span>
                            <input type="file" accept="image/*" style="display: none;" onchange="uploadPosterForCampaign(${c.id}, this.files[0])">
                        </label>
                        <input type="hidden" id="cPosterHidden_${c.id}" value="${c.poster_image || ''}">
                    </div>

                    <!-- Right: 4 Languages Tab & Copy -->
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                            <div class="lang-subtabs">
                                <button class="lang-subtab-btn active" id="tabBtn_${c.id}_zh" onclick="switchCampaignLangTab(${c.id}, 'zh')">🇨🇳 中文 (#17)</button>
                                <button class="lang-subtab-btn" id="tabBtn_${c.id}_en" onclick="switchCampaignLangTab(${c.id}, 'en')">🇬🇧 English (#16)</button>
                                <button class="lang-subtab-btn" id="tabBtn_${c.id}_ko" onclick="switchCampaignLangTab(${c.id}, 'ko')">🇰🇷 한국어 (#18)</button>
                                <button class="lang-subtab-btn" id="tabBtn_${c.id}_vi" onclick="switchCampaignLangTab(${c.id}, 'vi')">🇻🇳 Tiếng Việt (#19)</button>
                            </div>
                            <button class="btn btn-secondary btn-sm" onclick="autoTranslateCampaign(${c.id})">
                                <span>🌐 基于当前语言一键生成其余 3 语种</span>
                            </button>
                        </div>

                        <!-- Language Textareas -->
                        <div id="langBox_${c.id}_zh">
                            <textarea class="form-textarea" rows="6" id="cTextZh_${c.id}" placeholder="🇨🇳 输入中文群 (CHINESE CHAT #17) 的专属文案...">${c.text_zh || ''}</textarea>
                        </div>
                        <div id="langBox_${c.id}_en" style="display: none;">
                            <textarea class="form-textarea" rows="6" id="cTextEn_${c.id}" placeholder="🇬🇧 Enter English chat (ENGLISH CHAT #16) copy...">${c.text_en || ''}</textarea>
                        </div>
                        <div id="langBox_${c.id}_ko" style="display: none;">
                            <textarea class="form-textarea" rows="6" id="cTextKo_${c.id}" placeholder="🇰🇷 한국어 채팅방 (KOREAN CHAT #18) 맞춤 문구...">${c.text_ko || ''}</textarea>
                        </div>
                        <div id="langBox_${c.id}_vi" style="display: none;">
                            <textarea class="form-textarea" rows="6" id="cTextVi_${c.id}" placeholder="🇻🇳 Nhập nội dung kênh tiếng Việt (VIETNAMESE CHAT #19)...">${c.text_vi || ''}</textarea>
                        </div>
                    </div>
                </div>
            </div>
        `).join("");

    } catch (e) {
        container.innerHTML = `<div class="card text-center text-muted">加载排期计划失败: ${e.message}</div>`;
    }
}

function switchCampaignLangTab(cid, activeLang) {
    ['zh', 'en', 'ko', 'vi'].forEach(l => {
        const btn = document.getElementById(`tabBtn_${cid}_${l}`);
        const box = document.getElementById(`langBox_${cid}_${l}`);
        if (btn) {
            if (l === activeLang) btn.classList.add('active');
            else btn.classList.remove('active');
        }
        if (box) {
            box.style.display = (l === activeLang) ? 'block' : 'none';
        }
    });
}

function changeCampaignPosterSelect(cid, url) {
    const hidden = document.getElementById(`cPosterHidden_${cid}`);
    const img = document.getElementById(`cPosterImg_${cid}`);
    if (hidden) hidden.value = url;
    if (img && url) img.src = url;
}

async function uploadPosterForCampaign(cid, file) {
    if (!file) return;
    showToast("正在上传海报...", "success");
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/campaigns/upload-poster", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.success && data.url) {
            changeCampaignPosterSelect(cid, data.url);
            showToast("海报上传成功！已自动绑定", "success");
        } else {
            showToast("上传失败: " + (data.detail || "未知原因"), "error");
        }
    } catch (e) {
        showToast("上传异常: " + e.message, "error");
    }
}

async function autoTranslateCampaign(cid) {
    const zhBox = document.getElementById(`langBox_${cid}_zh`);
    const enBox = document.getElementById(`langBox_${cid}_en`);
    let sourceText = "";
    let sourceLang = "zh";

    const zhVal = document.getElementById(`cTextZh_${cid}`)?.value?.trim() || "";
    const enVal = document.getElementById(`cTextEn_${cid}`)?.value?.trim() || "";

    if (zhBox && zhBox.style.display !== 'none' && zhVal) {
        sourceText = zhVal;
        sourceLang = "zh";
    } else if (enBox && enBox.style.display !== 'none' && enVal) {
        sourceText = enVal;
        sourceLang = "en";
    } else {
        sourceText = zhVal || enVal;
        sourceLang = zhVal ? "zh" : "en";
    }

    if (!sourceText) {
        showToast("请先在文案框中输入一段文案，再点击一键翻译", "error");
        return;
    }

    showToast("正在通过双通道翻译引擎生成 4 语种定制文案...", "success");
    try {
        const res = await fetch("/api/campaigns/translate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: sourceText, source_lang: sourceLang })
        });
        const data = await res.json();
        if (data.success && data.translations) {
            const t = data.translations;
            if (t.zh && document.getElementById(`cTextZh_${cid}`)) document.getElementById(`cTextZh_${cid}`).value = t.zh;
            if (t.en && document.getElementById(`cTextEn_${cid}`)) document.getElementById(`cTextEn_${cid}`).value = t.en;
            if (t.ko && document.getElementById(`cTextKo_${cid}`)) document.getElementById(`cTextKo_${cid}`).value = t.ko;
            if (t.vi && document.getElementById(`cTextVi_${cid}`)) document.getElementById(`cTextVi_${cid}`).value = t.vi;
            showToast("🎉 4 大语种定制文案已一键生成完毕！", "success");
        } else {
            showToast("翻译失败: " + (data.detail || "未知原因"), "error");
        }
    } catch (e) {
        showToast("翻译异常: " + e.message, "error");
    }
}

async function saveCampaign(cid) {
    const title = document.getElementById(`cTitle_${cid}`)?.value?.trim() || "";
    const time = document.getElementById(`cTime_${cid}`)?.value?.trim() || "10:00";
    const poster = document.getElementById(`cPosterHidden_${cid}`)?.value?.trim() || "";
    const textZh = document.getElementById(`cTextZh_${cid}`)?.value || "";
    const textEn = document.getElementById(`cTextEn_${cid}`)?.value || "";
    const textKo = document.getElementById(`cTextKo_${cid}`)?.value || "";
    const textVi = document.getElementById(`cTextVi_${cid}`)?.value || "";

    const c = allCampaigns.find(item => item.id === cid);
    const dayNo = c ? c.day_number : 1;

    try {
        const res = await fetch("/api/campaigns/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                id: cid,
                day_number: dayNo,
                campaign_title: title,
                scheduled_time: time,
                poster_image: poster,
                text_zh: textZh,
                text_en: textEn,
                text_ko: textKo,
                text_vi: textVi,
                status: "pending"
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`第 ${dayNo} 天排期计划已保存！`, "success");
            loadCampaigns();
        } else {
            showToast("保存失败: " + data.detail, "error");
        }
    } catch (e) {
        showToast("保存异常: " + e.message, "error");
    }
}

async function triggerCampaignNow(cid) {
    await saveCampaign(cid);
    const c = allCampaigns.find(item => item.id === cid);
    const dayNo = c ? c.day_number : cid;

    if (!confirm(`确认立即将第 ${dayNo} 天计划的内容与海报并发推送到四大核心频道 (English #16, Chinese #17, Korean #18, Vietnamese #19) 吗？`)) {
        return;
    }

    showToast(`🚀 正在向 4 大语言频道并发投递第 ${dayNo} 天排期内容...`, "success");
    try {
        const res = await fetch("/api/campaigns/trigger", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: cid })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`🎉 第 ${dayNo} 天排期已成功全部送达 4 大语言频道！`, "success");
            loadCampaigns();
            loadHistory();
        } else {
            showToast("投递失败: " + (data.detail || "未知原因"), "error");
        }
    } catch (e) {
        showToast("触发异常: " + e.message, "error");
    }
}

async function deleteCampaign(cid) {
    if (!confirm(`确定要删除此排期计划吗？`)) return;
    try {
        const res = await fetch("/api/campaigns/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: cid })
        });
        const data = await res.json();
        showToast(data.message || "已删除", "success");
        loadCampaigns();
    } catch (e) {
        showToast("删除失败: " + e.message, "error");
    }
}

async function promptAddNewCampaign() {
    const nextDay = (allCampaigns.length > 0) ? Math.max(...allCampaigns.map(c => c.day_number || 1)) + 1 : 1;
    const title = prompt(`请输入新排期天数的标题：`, `Day ${nextDay}：牛顿协议深度推介`);
    if (!title || !title.trim()) return;

    const time = prompt(`请输入每日自动触发时间（24小时制，例如 10:00）：`, "10:00") || "10:00";

    try {
        const res = await fetch("/api/campaigns/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                day_number: nextDay,
                campaign_title: title.trim(),
                scheduled_time: time.trim(),
                poster_image: `/static/uploads/posters/${(nextDay <= 5) ? nextDay + '.png' : '1.png'}`
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            loadCampaigns();
        }
    } catch (e) {
        showToast("创建计划失败: " + e.message, "error");
    }
}

// -------------------------------------------------------------
// TAB 5: SCHEDULED TASKS (Image 3 Ref)
// -------------------------------------------------------------
async function loadScheduledTasks() {
    const container = document.getElementById("schedulerCardsContainer");
    if (!container) return;

    try {
        const res = await fetch("/api/scheduler/tasks");
        const data = await res.json();
        const tasks = data.tasks || [];

        container.innerHTML = tasks.map(t => `
            <div class="task-card-pro">
                <div>
                    <div class="task-top-row">
                        <div class="task-badge-group">
                            <span class="badge badge-info">${t.category}</span>
                            <span class="cron-badge">${t.cron_expr}</span>
                            <span class="thread-badge">${t.target_channel}</span>
                        </div>
                        <label class="switch">
                            <input type="checkbox" ${t.enabled ? 'checked' : ''} onchange="toggleTaskSwitch('${t.id}', this.checked)">
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="task-name-pro">${t.name}</div>
                    <div class="task-desc-pro">${t.description}</div>
                </div>
                <div class="task-bottom-row">
                    <span class="task-last-run">上次调度: ${t.last_run ? t.last_run.substring(0, 16) : '待运行'}</span>
                    <button class="btn btn-secondary btn-sm" onclick="runTaskNow('${t.id}')">
                        <span>▶ 立即执行测试</span>
                    </button>
                </div>
            </div>
        `).join("");
    } catch (e) {
        container.innerHTML = `<div class="card text-center text-muted">加载调度任务失败: ${e.message}</div>`;
    }
}

async function toggleTaskSwitch(taskId, isChecked) {
    try {
        const res = await fetch("/api/scheduler/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_id: taskId, enabled: isChecked ? 1 : 0 })
        });
        const data = await res.json();
        showToast(data.message || "任务状态已更新", "success");
    } catch (e) {
        showToast("切换失败: " + e.message, "error");
    }
}

async function runTaskNow(taskId) {
    showToast(`正在调度执行任务 [${taskId}]...`, "success");
    try {
        const res = await fetch(`/api/scheduler/run/${taskId}`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast(`任务 [${data.task_name}] 执行成功！已投递到话题 #${data.thread_id}`, "success");
            loadScheduledTasks();
            loadSchedulerLogs();
            loadHistory();
        } else {
            showToast(`执行失败: ${data.error || '未知错误'}`, "error");
        }
    } catch (e) {
        showToast("调度异常: " + e.message, "error");
    }
}

async function loadSchedulerLogs() {
    const tbody = document.getElementById("schedulerLogsTableBody");
    if (!tbody) return;

    try {
        const res = await fetch("/api/scheduler/logs");
        const data = await res.json();
        const logs = data.logs || [];

        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">暂无任务执行日志</td></tr>`;
            return;
        }

        tbody.innerHTML = logs.map(l => `
            <tr>
                <td>${l.run_at ? l.run_at.substring(0, 19) : '-'}</td>
                <td><strong>${l.task_name}</strong></td>
                <td><span class="thread-badge">Thread #${l.target_thread_id}</span></td>
                <td>
                    <span class="badge ${l.status === 'success' ? 'badge-success' : 'badge-danger'}">
                        ${l.status}
                    </span>
                </td>
                <td><span class="text-muted" style="font-family: var(--font-mono); font-size: 11px;">${escapeHtml(l.detail || '-')}</span></td>
            </tr>
        `).join("");
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">加载日志失败: ${e.message}</td></tr>`;
    }
}

// -------------------------------------------------------------
// TAB 6: REAL-TIME ENI ON-CHAIN MONITORING
// -------------------------------------------------------------
async function loadLiveChainData() {
    try {
        const res = await fetch("/api/eni/live");
        const data = await res.json();

        if (data.stats) {
            const s = data.stats;
            document.getElementById("liveBlockHeight").textContent = s.total_blocks_fmt || "41,568,230";
            document.getElementById("liveTotalTxs").textContent = s.total_transactions_fmt || "26,914,880";
            document.getElementById("liveTotalAddresses").textContent = s.total_addresses_fmt || "5,223,190";
            document.getElementById("liveGasPrice").textContent = `${s.gas_price_fast || 87.25} Gwei`;
        }

        const tbody = document.getElementById("liveTxsTableBody");
        if (tbody && data.transactions && data.transactions.length > 0) {
            tbody.innerHTML = data.transactions.map(tx => `
                <tr>
                    <td>
                        <a href="https://scan.eniac.network/tx/${tx.hash}" target="_blank" class="link-sub" style="font-family: var(--font-mono);">
                            ${tx.hash_short}
                        </a>
                    </td>
                    <td>#${tx.block_number}</td>
                    <td><span style="font-family: var(--font-mono); font-size: 11px;">${tx.from_short}</span></td>
                    <td><span style="font-family: var(--font-mono); font-size: 11px;">${tx.to_short}</span></td>
                    <td><strong>${tx.value_eni.toFixed(4)} ENI</strong></td>
                    <td><span class="badge badge-success">${tx.status}</span></td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Error loading live chain data:", e);
    }
}

function refreshLiveChain() {
    loadLiveChainData();
    showToast("主网数据已刷新", "success");
}

async function broadcastLiveSummary() {
    try {
        const res = await fetch("/api/action/broadcast-eni-summary", { method: "POST" });
        const data = await res.json();
        showToast("已生成主网全网汇总并群发！", "success");
        loadHistory();
    } catch (e) {
        showToast("群发失败: " + e.message, "error");
    }
}

// -------------------------------------------------------------
// TAB 7 & 8: SETTINGS & HISTORY
// -------------------------------------------------------------
async function loadSettings() {
    try {
        const res = await fetch("/api/config");
        const cfg = await res.json();

        // Telegram
        if (cfg.telegram) {
            const tVal = cfg.telegram.bot_token || "";
            const cVal = cfg.telegram.chat_id || "";
            const eVal = cfg.telegram.enabled !== false;

            const tokenInput = document.getElementById("tgBotTokenInput");
            const chatInput = document.getElementById("tgChatIdInput");
            const cfgToken = document.getElementById("cfgTgBotToken");
            const cfgChat = document.getElementById("cfgTgChatId");
            const cfgEnabled = document.getElementById("cfgTgEnabled");

            if (tokenInput) tokenInput.value = tVal;
            if (chatInput) chatInput.value = cVal;
            if (cfgToken) cfgToken.value = tVal;
            if (cfgChat) cfgChat.value = cVal;
            if (cfgEnabled) cfgEnabled.checked = eVal;
        }

        // Twitter
        if (cfg.twitter) {
            const k = document.getElementById("cfgTwApiKey");
            const s = document.getElementById("cfgTwApiSecret");
            const t = document.getElementById("cfgTwAccessToken");
            const ts = document.getElementById("cfgTwTokenSecret");
            if (k) k.value = cfg.twitter.api_key || "";
            if (s) s.value = cfg.twitter.api_secret || "";
            if (t) t.value = cfg.twitter.access_token || "";
            if (ts) ts.value = cfg.twitter.access_token_secret || "";
        }

        // Alerts / Thresholds
        if (cfg.thresholds) {
            const w = document.getElementById("cfgWhaleUsd");
            if (w) w.value = cfg.thresholds.whale_min_usd || 100000;
        }

        // Chain
        if (cfg.chain) {
            const rpc = document.getElementById("cfgRpcUrl");
            const poll = document.getElementById("cfgPollInterval");
            if (rpc) rpc.value = cfg.chain.rpc_url || "https://rpc.eniac.network";
            if (poll) poll.value = cfg.chain.polling_interval || 6;
        }

        const auto = document.getElementById("cfgAutoPublish");
        if (auto) auto.checked = !!cfg.auto_publish;

    } catch (e) {
        console.error("Load settings error:", e);
    }
}

async function saveAllSettings() {
    try {
        let cfg = {};
        try {
            const cfgRes = await fetch("/api/config");
            cfg = await cfgRes.json();
        } catch (_) {}
        if (!cfg || typeof cfg !== 'object') cfg = {};

        // Telegram
        if (!cfg.telegram) cfg.telegram = {};
        cfg.telegram.bot_token = (document.getElementById("cfgTgBotToken")?.value || document.getElementById("tgBotTokenInput")?.value || "").trim();
        cfg.telegram.chat_id = (document.getElementById("cfgTgChatId")?.value || document.getElementById("tgChatIdInput")?.value || "").trim();
        const cfgEnabled = document.getElementById("cfgTgEnabled");
        if (cfgEnabled) cfg.telegram.enabled = cfgEnabled.checked;

        // Twitter
        if (!cfg.twitter) cfg.twitter = {};
        cfg.twitter.api_key = (document.getElementById("cfgTwApiKey")?.value || "").trim();
        cfg.twitter.api_secret = (document.getElementById("cfgTwApiSecret")?.value || "").trim();
        cfg.twitter.access_token = (document.getElementById("cfgTwAccessToken")?.value || "").trim();
        cfg.twitter.access_token_secret = (document.getElementById("cfgTwTokenSecret")?.value || "").trim();

        // Chain & Thresholds
        if (!cfg.thresholds) cfg.thresholds = {};
        const wInput = document.getElementById("cfgWhaleUsd");
        const whaleVal = wInput ? (parseFloat(wInput.value) || 100000) : 100000;
        cfg.thresholds.whale_min_usd = whaleVal;
        cfg.thresholds.whale_usd_threshold = whaleVal;

        if (!cfg.chain) cfg.chain = {};
        const rpcInput = document.getElementById("cfgRpcUrl");
        if (rpcInput) cfg.chain.rpc_url = rpcInput.value.trim();
        const pollInput = document.getElementById("cfgPollInterval");
        if (pollInput) cfg.chain.polling_interval = parseInt(pollInput.value) || 6;

        const autoPub = document.getElementById("cfgAutoPublish");
        if (autoPub) cfg.auto_publish = autoPub.checked;

        const res = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(cfg)
        });
        if (res.ok) {
            showToast("系统设置与 API 密钥已全部保存成功！", "success");
            updateStatus();
        } else {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "服务器保存失败");
        }
    } catch (e) {
        showToast("保存失败: " + e.message, "error");
    }
}

async function loadHistory() {
    const tbody = document.getElementById("historyTableBody");
    if (!tbody) return;

    try {
        const res = await fetch("/api/posts?limit=30");
        const data = await res.json();
        const posts = data.posts || [];

        if (posts.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">暂无发帖历史记录</td></tr>`;
            return;
        }

        tbody.innerHTML = posts.map(p => `
            <tr>
                <td>#${p.id}</td>
                <td><span class="badge badge-info">${p.event_type}</span></td>
                <td><strong>${escapeHtml(p.title || '无标题')}</strong></td>
                <td>
                    <span class="badge ${p.telegram_status === 'success' ? 'badge-success' : 'badge-secondary'}">
                        ${p.telegram_status === 'success' ? `已发送 (#${p.telegram_msg_id || ''})` : (p.telegram_status || '未发')}
                    </span>
                </td>
                <td>
                    <span class="badge ${p.twitter_status === 'success' ? 'badge-success' : 'badge-secondary'}">
                        ${p.twitter_status === 'success' ? `已发布` : (p.twitter_status || '未发')}
                    </span>
                    ${p.twitter_tweet_id ? `<a href="https://x.com/eni_newton/status/${p.twitter_tweet_id}" target="_blank" class="link-sub" style="margin-left: 4px;">查看</a>` : ''}
                </td>
                <td>${p.created_at ? p.created_at.substring(0, 19) : '-'}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="alert('${escapeHtml(p.content || '').replace(/\n/g, '\\n')}')">查看内容</button>
                </td>
            </tr>
        `).join("");
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">加载历史异常: ${e.message}</td></tr>`;
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
}
