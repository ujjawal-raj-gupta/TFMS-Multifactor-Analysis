let currentStock = null;
let searchDebounce = null;
let loadingInterval = null;
let loadingStepIndex = 0;

const LOADING_STEPS = [
  "Fetching market data...",
  "Engineering multifactor features...",
  "Running prediction model...",
  "Building explainable AI breakdown...",
  "Analyzing news & sentiment...",
];

function resetLoadingProgress() {
  loadingStepIndex = 0;
  document.getElementById("loading-bar-fill").style.width = "0%";
  document.querySelectorAll(".loading-step").forEach((el) => {
    el.classList.remove("active", "done");
  });
}

function advanceLoadingStep() {
  const textEl = document.getElementById("loading-text");
  const stepEls = document.querySelectorAll(".loading-step");
  const barFill = document.getElementById("loading-bar-fill");

  textEl.classList.add("is-changing");
  setTimeout(() => {
    textEl.textContent = LOADING_STEPS[loadingStepIndex];
    textEl.classList.remove("is-changing");
  }, 120);

  stepEls.forEach((el, i) => {
    el.classList.toggle("active", i === loadingStepIndex);
    el.classList.toggle("done", i < loadingStepIndex);
  });

  const pct = ((loadingStepIndex + 1) / LOADING_STEPS.length) * 100;
  barFill.style.width = `${pct}%`;
}

function showLoading(show, title = "Loading analysis") {
  const overlay = document.getElementById("loading-overlay");
  const titleEl = document.getElementById("loading-title");
  const textEl = document.getElementById("loading-text");

  clearInterval(loadingInterval);

  if (show) {
    titleEl.textContent = title.replace(/\.\.\.$/, "");
    resetLoadingProgress();
    advanceLoadingStep();
    overlay.classList.add("is-active");
    overlay.setAttribute("aria-hidden", "false");

    loadingInterval = setInterval(() => {
      if (loadingStepIndex >= LOADING_STEPS.length - 1) return;
      loadingStepIndex += 1;
      advanceLoadingStep();
    }, 850);
    return;
  }

  overlay.classList.remove("is-active");
  overlay.setAttribute("aria-hidden", "true");
  textEl.textContent = "Preparing your dashboard...";
  resetLoadingProgress();
}

function showView(view) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.getElementById(`view-${view}`).classList.add("active");

  const isHome = view === "home";
  document.getElementById("app-shell").classList.toggle("app-shell--home", isHome);
  document.getElementById("stock-nav").classList.toggle("hidden", isHome);
}

function showStockTab(tab) {
  document.querySelectorAll(".stock-tab").forEach((t) => t.classList.remove("active"));
  document.getElementById(`tab-${tab}`).classList.add("active");
  document.querySelectorAll("#stock-nav .nav-item[data-stock-tab]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.stockTab === tab);
  });
}

function initNavigation() {
  document.getElementById("back-home").addEventListener("click", () => {
    currentStock = null;
    showView("home");
    document.getElementById("stock-search").value = "";
    document.getElementById("generated-at").textContent = "";
  });

  document.querySelectorAll("#stock-nav .nav-item[data-stock-tab]").forEach((btn) => {
    btn.addEventListener("click", () => showStockTab(btn.dataset.stockTab));
  });
}

function renderOverviewMetrics(summary) {
  const items = [
    ["Current Price", `$${summary.price.toFixed(2)}`],
    ["Daily Change", `${summary.change >= 0 ? "+" : ""}${summary.change.toFixed(2)} (${summary.change_pct.toFixed(2)}%)`],
    ["Predicted Next Close", `$${summary.predicted_next_close.toFixed(2)}`],
    ["Model R²", summary.r2.toFixed(3)],
    ["Model MAE", summary.mae.toFixed(2)],
    ["Sentiment Score", summary.sentiment_score.toFixed(3)],
  ];
  document.getElementById("overview-metrics").innerHTML = items
    .map(([label, value]) => `<div class="metric-pill"><div class="label">${label}</div><div class="value">${value}</div></div>`)
    .join("");
}

function renderStockHeader(summary) {
  document.getElementById("stock-title").textContent = `${summary.company} (${summary.ticker})`;
  document.getElementById("stock-subtitle").textContent = `Last updated ${summary.last_date}`;
  const sign = summary.change >= 0 ? "+" : "";
  const cls = summary.change >= 0 ? "up" : "down";
  document.getElementById("stock-price-badge").innerHTML = `
    <span class="price-big">$${summary.price.toFixed(2)}</span>
    <span class="delta ${cls}">${sign}${summary.change.toFixed(2)} (${sign}${summary.change_pct.toFixed(2)}%)</span>`;
}

function renderStock(stock) {
  currentStock = stock;
  const { summary, chart, explanation, news } = stock;

  renderStockHeader(summary);
  renderOverviewMetrics(summary);
  document.getElementById("generated-at").textContent = `Last updated ${summary.last_date}`;

  const move = summary.change >= 0 ? "up" : "down";
  document.getElementById("overview-summary").textContent =
    `${summary.company} is ${move} ${Math.abs(summary.change_pct).toFixed(2)}% today at $${summary.price.toFixed(2)}. ` +
    `The model forecasts $${summary.predicted_next_close.toFixed(2)} for the next session (R² ${summary.r2.toFixed(3)}). ` +
    `Select a section in the sidebar to explore the chart, explainable AI breakdown, or news-driven insights.`;

  ChartsModule.renderDualLineChart(chart);
  ChartsModule.renderChartMetrics(chart.metrics);

  ExplainModule.renderExplanation(explanation);
  NewsModule.renderStockNews(news);

  showView("stock");
  showStockTab("overview");
}

async function loadStock(ticker) {
  showLoading(true, `Analyzing ${ticker}...`);
  try {
    const res = await fetch(`/api/stock/${encodeURIComponent(ticker)}`);
    if (!res.ok) {
      const err = await res.json();
      alert(err.error || "Stock not found.");
      return;
    }
    renderStock(await res.json());
  } catch (err) {
    console.error(err);
    alert("Failed to load stock data.");
  } finally {
    showLoading(false);
  }
}

async function fetchSuggestions(query) {
  const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
  const data = await res.json();
  return data.results || [];
}

function renderSuggestions(results) {
  const box = document.getElementById("search-suggestions");
  if (!results.length) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }
  box.classList.remove("hidden");
  box.innerHTML = results
    .map(
      (r) =>
        `<button type="button" class="suggestion-item" data-ticker="${r.ticker}">${r.label}</button>`
    )
    .join("");
  box.querySelectorAll(".suggestion-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById("stock-search").value = btn.dataset.ticker;
      box.classList.add("hidden");
      loadStock(btn.dataset.ticker);
    });
  });
}

function initSearch() {
  const input = document.getElementById("stock-search");

  input.addEventListener("input", () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(async () => {
      renderSuggestions(await fetchSuggestions(input.value));
    }, 200);
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      document.getElementById("search-suggestions").classList.add("hidden");
      loadStock(input.value);
    }
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-wrap")) {
      document.getElementById("search-suggestions").classList.add("hidden");
    }
  });
}

async function refreshData() {
  showLoading(true, "Refreshing market data...");
  try {
    await fetch("/api/refresh", { method: "POST" });
    document.getElementById("generated-at").textContent = `Updated: ${new Date().toLocaleString()}`;
    if (currentStock) {
      await loadStock(currentStock.summary.ticker);
    }
  } finally {
    showLoading(false);
  }
}

document.getElementById("refresh-btn").addEventListener("click", refreshData);

initNavigation();
initSearch();
showView("home");
showLoading(false);
