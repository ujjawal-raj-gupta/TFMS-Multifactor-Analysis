let chartInstance = null;

function formatUsd(value) {
  return `$${Number(value).toFixed(2)}`;
}

function renderChartTabs(tickers, activeTicker, onSelect) {
  const container = document.getElementById("chart-tabs");
  container.innerHTML = tickers
    .map(
      (ticker) =>
        `<button class="tab-btn ${ticker === activeTicker ? "active" : ""}" data-ticker="${ticker}">${ticker}</button>`
    )
    .join("");

  container.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => onSelect(btn.dataset.ticker));
  });
}

function renderChartMetrics(metrics) {
  const container = document.getElementById("chart-metrics");
  if (!metrics) {
    container.innerHTML = "";
    return;
  }

  const items = [
    ["Latest Close", formatUsd(metrics.latest_close)],
    ["Predicted Next", formatUsd(metrics.predicted_next_close)],
    ["MAE", metrics.mae.toFixed(2)],
    ["R²", metrics.r2.toFixed(3)],
  ];

  container.innerHTML = items
    .map(
      ([label, value]) =>
        `<div class="metric-pill"><div class="label">${label}</div><div class="value">${value}</div></div>`
    )
    .join("");
}

function renderDualLineChart(chartData) {
  const el = document.querySelector("#main-chart");
  if (!chartData || !chartData.dates?.length) {
    el.innerHTML = "<p class='muted'>No chart data available.</p>";
    return;
  }

  if (chartInstance) {
    chartInstance.destroy();
  }

  chartInstance = new ApexCharts(el, {
    chart: {
      type: "line",
      height: 420,
      background: "transparent",
      toolbar: { show: true },
      animations: { enabled: true, easing: "easeinout", speed: 600 },
      zoom: { enabled: true },
    },
    theme: { mode: "dark" },
    colors: ["#00d4ff", "#ff8c42"],
    stroke: { width: [3, 3], curve: "smooth", dashArray: [0, 6] },
    series: [
      { name: "Actual Close", data: chartData.actual },
      { name: "Predicted Next Close", data: chartData.predicted },
    ],
    xaxis: {
      categories: chartData.dates,
      labels: {
        style: { colors: "#94a3b8" },
        rotate: -45,
        formatter: (val) => (val ? val.slice(5) : val),
      },
      tickAmount: 10,
    },
    yaxis: {
      labels: {
        style: { colors: "#94a3b8" },
        formatter: (val) => `$${val.toFixed(0)}`,
      },
    },
    grid: { borderColor: "rgba(255,255,255,0.06)" },
    legend: {
      labels: { colors: "#e8edf5" },
      position: "top",
    },
    tooltip: {
      shared: true,
      intersect: false,
      theme: "dark",
      x: { show: true },
      y: {
        formatter: (val) => formatUsd(val),
      },
      custom: function ({ series, seriesIndex, dataPointIndex, w }) {
        const date = w.globals.categoryLabels[dataPointIndex];
        const actual = series[0][dataPointIndex];
        const predicted = series[1][dataPointIndex];
        const delta = predicted - actual;
        const sign = delta >= 0 ? "+" : "";
        return `<div class="apex-tooltip-custom" style="padding:10px;background:#111827;border:1px solid rgba(255,255,255,0.1);border-radius:8px;">
          <div style="font-weight:600;margin-bottom:6px;">${date}</div>
          <div style="color:#00d4ff;">Actual: ${formatUsd(actual)}</div>
          <div style="color:#ff8c42;">Predicted: ${formatUsd(predicted)}</div>
          <div style="color:#94a3b8;margin-top:4px;">Delta: ${sign}${delta.toFixed(2)}</div>
        </div>`;
      },
    },
  });

  chartInstance.render();
}

window.ChartsModule = {
  renderChartTabs,
  renderDualLineChart,
  renderChartMetrics,
};
