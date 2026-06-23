function renderExplanation(data) {
  const barsEl = document.getElementById("explain-bars");
  const narrativeEl = document.getElementById("explain-narrative");
  const featuresEl = document.getElementById("explain-features");
  const fundEl = document.getElementById("fundamentals-grid");
  const methodEl = document.getElementById("explain-method");

  if (!data || !data.groups) {
    barsEl.innerHTML = "";
    narrativeEl.textContent = "";
    featuresEl.innerHTML = "";
    fundEl.innerHTML = "";
    return;
  }

  methodEl.textContent = data.method || "";

  const groups = ["technical", "fundamental", "sentiment"];
  barsEl.innerHTML = groups
    .map((group) => {
      const info = data.groups[group] || { pct: 0 };
      return `<div class="explain-bar-row">
        <span class="name">${group}</span>
        <div class="explain-bar-track">
          <div class="explain-bar-fill ${group}" style="width:${info.pct}%"></div>
        </div>
        <span class="pct">${info.pct}%</span>
      </div>`;
    })
    .join("");

  narrativeEl.textContent = data.narrative || "";

  featuresEl.innerHTML = groups
    .map((group) => {
      const info = data.groups[group] || { top_features: [] };
      const items = (info.top_features || [])
        .map((feat) => {
          const cls = feat.impact >= 0 ? "positive" : "negative";
          const sign = feat.impact >= 0 ? "+" : "";
          const extra =
            feat.value !== undefined
              ? ` <span class="muted">(value ${feat.value}, baseline ${feat.baseline})</span>`
              : "";
          return `<div class="feature-item">${feat.name}${extra} <span class="impact ${cls}">${sign}${feat.impact}</span></div>`;
        })
        .join("");
      return `<div class="feature-group"><h4>${group}</h4>${items || "<p class='muted'>—</p>"}</div>`;
    })
    .join("");

  const f = data.fundamentals || {};
  if (fundEl) {
    fundEl.innerHTML = `<div class="feature-group full-width"><h4>Fundamental Snapshot</h4>
      <div class="fund-grid">
        <div class="fund-item"><span>P/E</span><strong>${(f.pe_ratio || 0).toFixed(2)}</strong></div>
        <div class="fund-item"><span>Forward P/E</span><strong>${(f.forward_pe || 0).toFixed(2)}</strong></div>
        <div class="fund-item"><span>Profit Margin</span><strong>${((f.profit_margin || 0) * 100).toFixed(1)}%</strong></div>
        <div class="fund-item"><span>Revenue Growth</span><strong>${((f.revenue_growth || 0) * 100).toFixed(1)}%</strong></div>
        <div class="fund-item"><span>ROE</span><strong>${((f.roe || 0) * 100).toFixed(1)}%</strong></div>
        <div class="fund-item"><span>Debt/Equity</span><strong>${(f.debt_to_equity || 0).toFixed(2)}</strong></div>
      </div></div>`;
  }
}

window.ExplainModule = { renderExplanation };
