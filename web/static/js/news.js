const BADGE_LABELS = {
  positive: "Bullish",
  negative: "Bearish",
  neutral: "Neutral",
};

function renderStockNews(newsPayload) {
  const container = document.getElementById("news-container");
  const articles = newsPayload?.articles || [];
  const insights = newsPayload?.insights || {};

  document.getElementById("news-insights-summary").textContent = insights.summary || "";
  const list = document.getElementById("news-insights-list");
  list.innerHTML = (insights.bullets || [])
    .map((b) => `<li>${b}</li>`)
    .join("");

  if (!articles.length) {
    container.innerHTML = "<p class='muted'>No news articles available.</p>";
    return;
  }

  container.innerHTML = `<div class="news-grid">${articles
    .map((article) => {
      const badgeClass = article.sentiment || "neutral";
      const badgeLabel = BADGE_LABELS[badgeClass] || "Neutral";
      const link = article.url
        ? `<a href="${article.url}" target="_blank" rel="noopener">${article.title}</a>`
        : article.title;
      return `<article class="news-card">
        <h4>${link}</h4>
        <div class="news-meta">
          <span>${article.source} · ${article.published_at}</span>
          <span class="badge ${badgeClass}">${badgeLabel}</span>
        </div>
      </article>`;
    })
    .join("")}</div>`;
}

window.NewsModule = { renderStockNews };
