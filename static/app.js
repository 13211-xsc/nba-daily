/**
 * NBA Daily - 前端逻辑
 */
let currentView = "article";
let currentArticleId = null;

document.addEventListener("DOMContentLoaded", () => { loadTodayArticle(); });

async function loadTodayArticle() {
    showLoading(true); hideAll();
    try {
        const resp = await fetch("/api/today");
        const data = await resp.json();
        if (data.status === "ok") { renderArticle(data.article); showView("articleView"); }
        else { showView("emptyState"); }
    } catch (err) { showView("emptyState"); }
    finally { showLoading(false); }
}

function renderArticle(article) {
    currentArticleId = article.id;
    document.getElementById("articleTitle").textContent = article.title;
    document.getElementById("articleDate").textContent = "📅 " + (article.published || "").slice(0, 10);
    document.getElementById("articleSource").textContent = "📍 " + article.source;
    document.getElementById("articleStats").textContent = article.word_count + "词";
    document.getElementById("articleLink").href = article.url;

    const coverDiv = document.getElementById("coverImage");
    if (article.images && article.images.length > 0) {
        const today = new Date().toISOString().slice(0, 10);
        coverDiv.innerHTML = `<img src="/api/image/${today}/${article.images[0].path}" alt="">`;
        coverDiv.style.display = "block";
    } else { coverDiv.style.display = "none"; }

    const body = document.getElementById("articleBody");
    let html = "";
    if (article.paragraphs && article.paragraphs.length > 0) {
        article.paragraphs.forEach((para, i) => {
            html += `<div class="para-block">
                <div class="para-en"><div class="para-label">🇺🇸 EN</div><div>${escapeHtml(para.en)}</div></div>`;
            if (para.zh) {
                html += `<div class="para-zh"><div class="para-label">🇨🇳 中文</div><div>${escapeHtml(para.zh)}</div></div>`;
            }
            html += `</div>`;
            if (article.images && i < article.images.length - 1) {
                const img = article.images[i + 1];
                const today = new Date().toISOString().slice(0, 10);
                html += `<div class="inline-image">
                    <img src="/api/image/${today}/${img.path}" alt="${escapeHtml(img.alt||'')}" loading="lazy">
                    ${img.alt?`<div class="img-caption">${escapeHtml(img.alt)}</div>`:""}</div>`;
            }
        });
    } else { html = "<p style='color:#999;text-align:center;padding:40px;'>文章内容为空</p>"; }
    body.innerHTML = html;
    window.scrollTo(0, 0);
}

async function refreshArticle() {
    showLoading(true);
    try {
        const resp = await fetch("/api/refresh", { method: "POST" });
        const data = await resp.json();
        showToast(data.status==="ok" ? (data.cached?"📋 文章已存在":"✅ 新文章已就绪!") : "❌ "+(data.message||"失败"));
        if (data.status === "ok") await loadTodayArticle();
    } catch (err) { showToast("❌ 网络错误"); }
    finally { showLoading(false); }
}

async function showHistory() {
    showLoading(true); hideAll();
    try {
        const resp = await fetch("/api/history");
        const data = await resp.json();
        const list = document.getElementById("historyList");
        if (data.articles && data.articles.length > 0) {
            list.innerHTML = data.articles.map(a => `
                <div class="history-item" onclick="loadArticle(${a.id})">
                    <div class="hi-title">${escapeHtml(a.title)}</div>
                    <div class="hi-meta">📅 ${(a.published||"").slice(0,10)} · 📍 ${a.source} · ${a.word_count}词</div>
                </div>`).join("");
        } else { list.innerHTML = "<p style='text-align:center;color:#999;padding:30px;'>暂无历史文章</p>"; }
        document.getElementById("btnBack").style.display = "block";
        showView("historyView"); currentView = "history";
    } catch (err) { showToast("加载历史失败"); }
    finally { showLoading(false); }
}

async function loadArticle(id) {
    showLoading(true); hideAll();
    try {
        const resp = await fetch(`/api/article/${id}`);
        const data = await resp.json();
        if (data.status === "ok") {
            renderArticle(data.article); showView("articleView");
            currentView = "article"; document.getElementById("btnBack").style.display = "none";
        }
    } catch (err) { showToast("加载文章失败"); }
    finally { showLoading(false); }
}

function goBack() {
    if (currentView === "history") {
        hideAll(); showView("articleView");
        currentView = "article"; document.getElementById("btnBack").style.display = "none";
    }
}

function showLoading(s) { document.getElementById("loading").style.display = s?"block":"none"; }
function hideAll() { ["articleView","emptyState","historyView"].forEach(id=>document.getElementById(id).style.display="none"); }
function showView(id) { document.getElementById(id).style.display = "block"; }

function showToast(msg) {
    const t = document.getElementById("toast"); t.textContent = msg; t.classList.add("show");
    setTimeout(()=>t.classList.remove("show"), 2500);
}

function escapeHtml(text) {
    const div = document.createElement("div"); div.textContent = text; return div.innerHTML;
}
