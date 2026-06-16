/*
 * Client-side Plotly charts for the dashboard.
 *
 * Charts live inside tab panels (display:none until selected) and <details>
 * elements (no layout when collapsed). Plotly drawn into a zero-width container
 * renders collapsed, so we lazily draw each chart the first time its container
 * becomes visible, and call Plotly.Plots.resize() on later reveals.
 *
 * Adding a chart: register a builder in CHARTS keyed by its div id and add a
 * matching <div id="..."> in index.html.
 */
(function () {
  'use strict';

  let chartData = null;
  const renderedIds = new Set();

  // --- Warm Editorial theme (mirrors design/tokens.css) -----------------------
  // Chart fills use a soft pastel palette so they sit calmly on the warm paper.
  // (The UI chrome — tabs, KPI borders — keeps the deeper --accent in main.css.)
  const FONT = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
  const ACCENT = '#8FC6B6';      // pastel teal — primary series / "good"
  const TEXT = '#2A2622';
  const MUTED = '#6F665C';
  const GRID = '#ECE6DC';        // warm hairline grid
  // Reference lines / "not supported" — a slightly deeper soft clay so thin
  // dashed lines stay visible against pastel fills.
  const REFERENCE = '#D99873';
  // Categorical colorway; pies and any trace without an explicit color cycle this.
  const COLORWAY = ['#8FC6B6', '#EAB79C', '#A9C4DE', '#ECD5A6', '#C8BBDA', '#E4BAC9', '#C6D4A6'];
  // Tiers, low -> high price (Budget / Mid-range / Flagship). Three maximally
  // distinct pastels (lavender / amber / teal) so the clusters separate cleanly.
  const TIER_COLORS = ['#C8BBDA', '#ECD5A6', '#8FC6B6'];
  // Diverging scale for the correlation heatmap: soft clay (neg) -> paper -> pastel teal (pos).
  const DIVERGING = [[0, '#D99873'], [0.5, '#F4EEE4'], [1, '#8FC6B6']];
  // ----------------------------------------------------------------------------

  function baseLayout(title) {
    return {
      title: { text: title, font: { size: 16, color: TEXT } },
      font: { family: FONT, color: TEXT },
      colorway: COLORWAY,
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      margin: { t: 50, r: 20, b: 80, l: 60 },
      autosize: true,
    };
  }

  const BASE_CONFIG = { responsive: true, displayModeBar: false };

  // Human-readable labels for the numeric columns used by histograms.
  const COLUMN_LABELS = {
    'inches': 'Screen Size (inches)',
    'battery': 'Battery Capacity (mAh)',
    'ram(GB)': 'RAM (GB)',
    'weight(g)': 'Weight (g)',
    'storage(GB)': 'Storage (GB)',
    'price(USD)': 'Price (USD)',
    'width': 'Width (pixels)',
    'height': 'Height (pixels)',
    'announcement_year': 'Announcement Year',
  };

  const SPEC_LABELS = {
    'height': 'Average Height (pixels)',
    'ram(GB)': 'Average RAM (GB)',
    'storage(GB)': 'Average Storage (GB)',
    'weight(g)': 'Average Weight (g)',
  };

  // Short labels for the hero KPI "top price driver" stat.
  const DRIVER_LABELS = {
    'ram(GB)': 'RAM', 'storage(GB)': 'Storage', 'battery': 'Battery',
    'inches': 'Screen size', 'weight(g)': 'Weight', 'width': 'Resolution',
    'height': 'Resolution', 'announcement_year': 'Release year',
  };

  function pie(title, counts) {
    const labels = Object.keys(counts);
    const values = labels.map(function (k) { return counts[k]; });
    const total = values.reduce(function (a, b) { return a + b; }, 0);
    // Match the prior matplotlib pies: suppress the percent label on slices < 3.5%
    // so the long tail of minor categories doesn't clutter the chart.
    const sliceText = values.map(function (v) {
      const pct = total ? (v / total) * 100 : 0;
      return pct >= 3.5 ? pct.toFixed(1) + '%' : '';
    });
    return {
      data: [{
        type: 'pie',
        labels: labels,
        values: values,
        textposition: 'inside',
        textinfo: 'text',
        text: sliceText,
        hovertemplate: '<b>%{label}</b><br>%{value} phones<br>%{percent}<extra></extra>',
        sort: true,
        direction: 'clockwise',
      }],
      layout: Object.assign(baseLayout(title), {
        height: 460,
        showlegend: true,
        legend: { font: { size: 11 } },
      }),
    };
  }

  function bar(title, yLabel, brands, values, color, valuePrefix) {
    return {
      data: [{
        type: 'bar',
        x: brands,
        y: values,
        marker: { color: color },
        hovertemplate: '<b>%{x}</b><br>' + (valuePrefix || '') + '%{y}<extra></extra>',
      }],
      layout: Object.assign(baseLayout(title), {
        height: 500,
        xaxis: { tickangle: -45, automargin: true },
        yaxis: { title: { text: yLabel }, gridcolor: GRID },
      }),
    };
  }

  // Build a dropdown (updatemenus) that shows one trace at a time and rewrites the
  // title (and optionally an axis label) to match the selection. `label`/`title`/
  // `axisText` are functions of the trace key so callers control the wording.
  function dropdownButtons(keys, label, title, axisField, axisText) {
    return keys.map(function (key, i) {
      const visible = keys.map(function (_, j) { return j === i; });
      const layoutPatch = { 'title.text': title(key) };
      if (axisField) layoutPatch[axisField] = axisText(key);
      return { method: 'update', label: label(key), args: [{ visible: visible }, layoutPatch] };
    });
  }

  const CHARTS = {
    'chart-brand-pie': function (d) {
      return pie('Smartphone Distribution by Brand', d.brand_counts);
    },

    'chart-os-pie': function (d) {
      return pie('Smartphone Distribution by Operating System', d.os_counts);
    },

    'chart-battery-type-pie': function (d) {
      return pie('Battery Type Distribution', d.battery_type_counts);
    },

    'chart-avg-price-by-brand': function (d) {
      const a = d.avg_price_by_brand;
      return bar('Average Price by Brand', 'Average Price (USD)', a.brands, a.values, ACCENT, '$');
    },

    'chart-battery-efficiency': function (d) {
      const a = d.battery_efficiency_by_brand;
      return bar('Battery Efficiency by Brand (mAh per USD)', 'mAh / USD',
        a.brands, a.values, '#C8BBDA', '');
    },

    'chart-video-formats': function (d) {
      const formats = Object.keys(d.video_formats);
      const labels = formats.map(function (f) { return f.replace('video_', ''); });
      const supported = formats.map(function (f) { return d.video_formats[f].true; });
      const notSupported = formats.map(function (f) { return d.video_formats[f].false; });
      return {
        data: [
          { type: 'bar', name: 'Supported', x: labels, y: supported, marker: { color: ACCENT } },
          { type: 'bar', name: 'Not supported', x: labels, y: notSupported, marker: { color: REFERENCE } },
        ],
        layout: Object.assign(baseLayout('Video Format Support'), {
          height: 500,
          barmode: 'group',
          xaxis: { automargin: true },
          yaxis: { title: { text: 'Count' }, gridcolor: GRID },
          legend: { orientation: 'h', y: 1.08, x: 0 },
        }),
      };
    },

    'chart-specs-by-brand': function (d) {
      const specs = Object.keys(d.specs_by_brand);
      const traces = specs.map(function (spec, i) {
        const s = d.specs_by_brand[spec];
        return {
          type: 'bar', name: SPEC_LABELS[spec], x: s.brands, y: s.values,
          marker: { color: ACCENT }, visible: i === 0,
          hovertemplate: '<b>%{x}</b><br>%{y}<extra></extra>',
        };
      });
      return {
        data: traces,
        layout: Object.assign(baseLayout(SPEC_LABELS[specs[0]]), {
          height: 500,
          xaxis: { tickangle: -45, automargin: true },
          yaxis: { gridcolor: GRID },
          updatemenus: [{
            buttons: dropdownButtons(
              specs,
              function (k) { return SPEC_LABELS[k]; },
              function (k) { return SPEC_LABELS[k]; }
            ),
            x: 1, xanchor: 'right', y: 1.18, yanchor: 'top', showactive: true,
          }],
        }),
      };
    },

    'chart-correlation': function (d) {
      return {
        data: [{
          type: 'heatmap',
          z: d.correlation.matrix,
          x: d.correlation.labels,
          y: d.correlation.labels,
          zmin: -1, zmax: 1, zmid: 0,
          colorscale: DIVERGING,
          texttemplate: '%{z:.2f}', textfont: { size: 9 },
          hovertemplate: '%{x} / %{y}<br>r = %{z}<extra></extra>',
          colorbar: { title: { text: 'Correlation' } },
        }],
        layout: Object.assign(baseLayout('Feature Correlation Heatmap'), {
          height: 620,
          xaxis: { tickangle: -45, automargin: true },
          yaxis: { automargin: true, autorange: 'reversed' },
        }),
      };
    },

    'chart-yearly-trends': function (d) {
      const t = d.yearly_trends;
      return {
        data: [
          { type: 'bar', name: 'Releases', x: t.years, y: t.releases, marker: { color: ACCENT } },
          {
            type: 'scatter', mode: 'lines+markers', name: 'Avg Price (USD)',
            x: t.years, y: t.avg_price, yaxis: 'y2', line: { color: REFERENCE },
          },
        ],
        layout: Object.assign(baseLayout('Yearly Market Trends'), {
          height: 500,
          xaxis: { title: { text: 'Announcement Year' }, automargin: true },
          yaxis: { title: { text: 'Number of Phones' }, gridcolor: GRID },
          yaxis2: {
            title: { text: 'Average Price (USD)' }, overlaying: 'y', side: 'right',
            showgrid: false,
          },
          legend: { orientation: 'h', y: 1.12, x: 0 },
        }),
      };
    },

    'chart-price-by-os': function (d) {
      const traces = Object.keys(d.price_by_os).map(function (os) {
        return { type: 'box', name: os, y: d.price_by_os[os], boxpoints: false };
      });
      return {
        data: traces,
        layout: Object.assign(baseLayout('Price Distribution by Operating System'), {
          height: 500,
          showlegend: false,
          xaxis: { tickangle: -25, automargin: true },
          yaxis: { title: { text: 'Price (USD)' }, gridcolor: GRID },
        }),
      };
    },

    'chart-histograms': function (d) {
      const cols = Object.keys(d.histograms);
      const traces = cols.map(function (col, i) {
        return {
          type: 'histogram', name: COLUMN_LABELS[col] || col,
          x: d.histograms[col], marker: { color: ACCENT },
          visible: i === 0,
        };
      });
      const first = COLUMN_LABELS[cols[0]] || cols[0];
      return {
        data: traces,
        layout: Object.assign(baseLayout(first + ' Distribution'), {
          height: 500,
          xaxis: { title: { text: first }, automargin: true },
          yaxis: { title: { text: 'Frequency' }, gridcolor: GRID },
          bargap: 0.05,
          updatemenus: [{
            buttons: dropdownButtons(
              cols,
              function (k) { return COLUMN_LABELS[k] || k; },
              function (k) { return (COLUMN_LABELS[k] || k) + ' Distribution'; },
              'xaxis.title.text',
              function (k) { return COLUMN_LABELS[k] || k; }
            ),
            x: 1, xanchor: 'right', y: 1.18, yanchor: 'top', showactive: true,
          }],
        }),
      };
    },

    'chart-price-drivers': function (d) {
      const imp = d.price_model.importance.slice().reverse();
      const m = d.price_model.metrics;
      return {
        data: [{
          type: 'bar', orientation: 'h',
          x: imp.map(function (f) { return f.importance; }),
          y: imp.map(function (f) { return f.feature; }),
          marker: { color: ACCENT },
          hovertemplate: '%{y}: %{x:.3f}<extra></extra>',
        }],
        layout: Object.assign(baseLayout('What Drives Price? — Random Forest feature importance'), {
          height: 460,
          margin: { t: 70, r: 20, b: 45, l: 120 },
          xaxis: { title: { text: 'Importance' }, gridcolor: GRID },
          yaxis: { automargin: true },
          annotations: [{
            xref: 'paper', yref: 'paper', x: 0, y: 1.08, xanchor: 'left', showarrow: false,
            text: 'Random Forest R² ' + m.random_forest.r2 + ', MAE $' + m.random_forest.mae +
                  '  ·  Linear R² ' + m.linear.r2 + ', MAE $' + m.linear.mae,
            font: { size: 11, color: '#666' },
          }],
        }),
      };
    },

    'chart-pred-actual': function (d) {
      const pa = d.price_model.pred_vs_actual;
      const hi = Math.max(Math.max.apply(null, pa.actual), Math.max.apply(null, pa.predicted));
      return {
        data: [
          {
            type: 'scatter', mode: 'markers', name: 'Phones',
            x: pa.actual, y: pa.predicted,
            marker: { color: ACCENT, size: 6, opacity: 0.65 },
            hovertemplate: 'actual $%{x}<br>predicted $%{y}<extra></extra>',
          },
          {
            type: 'scatter', mode: 'lines', name: 'Perfect prediction',
            x: [0, hi], y: [0, hi], line: { color: REFERENCE, dash: 'dash' }, hoverinfo: 'skip',
          },
        ],
        layout: Object.assign(baseLayout('Predicted vs Actual Price (test set)'), {
          height: 480,
          xaxis: { title: { text: 'Actual Price (USD)' }, gridcolor: GRID },
          yaxis: { title: { text: 'Predicted Price (USD)' }, gridcolor: GRID },
          legend: { orientation: 'h', y: 1.1, x: 0 },
        }),
      };
    },

    'chart-value-ranking': function (d) {
      const best = d.value_ranking.best.slice().reverse();
      return {
        data: [{
          type: 'bar', orientation: 'h',
          x: best.map(function (p) { return p.residual; }),
          y: best.map(function (p) { return p.name + ' · ' + p.brand; }),
          marker: { color: ACCENT },
          customdata: best.map(function (p) { return [p.actual, p.predicted]; }),
          hovertemplate: '<b>%{y}</b><br>actual $%{customdata[0]} · predicted $%{customdata[1]}' +
                         '<br>value gap $%{x}<extra></extra>',
        }],
        layout: Object.assign(baseLayout('Best Value Phones — priced below their spec-predicted price'), {
          height: 540,
          margin: { t: 60, r: 20, b: 50, l: 200 },
          xaxis: { title: { text: 'Predicted − Actual Price (USD)' }, gridcolor: GRID },
          yaxis: { automargin: true },
        }),
      };
    },

    'chart-tiers-scatter': function (d) {
      const pts = d.tiers.points;
      const colors = TIER_COLORS;
      const traces = d.tiers.names.map(function (name, t) {
        const xs = [], ys = [];
        for (let i = 0; i < pts.tier.length; i++) {
          if (pts.tier[i] === t) { xs.push(pts.storage[i]); ys.push(pts.price[i]); }
        }
        return {
          type: 'scatter', mode: 'markers', name: name, x: xs, y: ys,
          marker: { color: colors[t], size: 6, opacity: 0.75 },
          hovertemplate: name + '<br>storage %{x} GB · $%{y}<extra></extra>',
        };
      });
      return {
        data: traces,
        layout: Object.assign(baseLayout('Market Tiers (k-means): Storage vs Price'), {
          height: 500,
          xaxis: { title: { text: 'Storage (GB)' }, gridcolor: GRID },
          yaxis: { title: { text: 'Price (USD)' }, gridcolor: GRID },
          legend: { orientation: 'h', y: 1.1, x: 0 },
        }),
      };
    },

    'chart-tiers-summary': function (d) {
      const s = d.tiers.summary;
      return {
        data: [{
          type: 'table',
          header: {
            values: ['Tier', 'Count', 'Mean price', 'Mean RAM (GB)', 'Mean battery', 'Mean storage (GB)'],
            fill: { color: '#E3F2EE' }, align: 'left',
            font: { color: TEXT, size: 12 },
          },
          cells: {
            values: [
              s.map(function (r) { return r.tier; }),
              s.map(function (r) { return r.count; }),
              s.map(function (r) { return '$' + r.mean_price; }),
              s.map(function (r) { return r.mean_ram; }),
              s.map(function (r) { return r.mean_battery + ' mAh'; }),
              s.map(function (r) { return r.mean_storage; }),
            ],
            align: 'left', font: { size: 12 }, height: 26,
          },
        }],
        layout: Object.assign(baseLayout('Tier Profiles'), {
          height: 230, margin: { t: 50, r: 10, b: 10, l: 10 },
        }),
      };
    },
  };

  function isVisible(el) {
    // offsetParent is null for display:none ancestors; width guards collapsed details.
    return el.offsetParent !== null && el.clientWidth > 0;
  }

  function renderVisibleCharts() {
    if (!chartData) return;
    Object.keys(CHARTS).forEach(function (id) {
      const el = document.getElementById(id);
      if (!el || !isVisible(el)) return;
      if (renderedIds.has(id)) {
        Plotly.Plots.resize(el);
        return;
      }
      // A builder may throw if its data hasn't arrived yet (charts.json and
      // insights.json load independently). Skip without marking rendered so the
      // chart is retried on the next merge/visibility pass.
      let fig;
      try {
        fig = CHARTS[id](chartData);
      } catch (err) {
        return;
      }
      Plotly.newPlot(el, fig.data, fig.layout, fig.config || BASE_CONFIG);
      renderedIds.add(id);
    });
  }

  // Fill the hero KPI strip from whichever payload has arrived. Each stat is
  // guarded so it populates as soon as its source data is present (charts.json
  // carries the count; insights.json carries the model-derived stats).
  function setText(id, value) {
    const el = document.getElementById(id);
    if (el && value != null) el.textContent = value;
  }
  function populateKPIs(d) {
    if (d.brand_counts) {
      const total = Object.keys(d.brand_counts).reduce(
        function (a, k) { return a + d.brand_counts[k]; }, 0);
      setText('kpi-count', total.toLocaleString());
    }
    if (d.price_model) {
      const top = d.price_model.importance[0];
      setText('kpi-driver', DRIVER_LABELS[top.feature] || top.feature);
      setText('kpi-r2', 'R² ' + d.price_model.metrics.random_forest.r2);
    }
    if (d.value_ranking) {
      setText('kpi-value', d.value_ranking.best[0].name);
    }
  }

  // Expose so the inline tab handler (or console) can trigger a pass if needed.
  window.renderVisibleCharts = renderVisibleCharts;

  document.addEventListener('DOMContentLoaded', function () {
    // Re-check visibility after a tab switch or a <details> open/close.
    // rAF lets the browser apply the display change before we measure width.
    function schedule() { requestAnimationFrame(renderVisibleCharts); }

    document.querySelectorAll('.tab-button').forEach(function (btn) {
      btn.addEventListener('click', schedule);
    });
    document.querySelectorAll('details').forEach(function (det) {
      det.addEventListener('toggle', schedule);
    });

    function getJSON(url) {
      return fetch(url).then(function (r) {
        if (!r.ok) throw new Error(url + ' HTTP ' + r.status);
        return r.json();
      });
    }

    // Descriptive charts (charts.json) and modeling insights (insights.json) load
    // independently: the modeling endpoint is heavier, so we don't let it block or
    // sink the descriptive charts. Each merges what it has and re-renders.
    function merge(data) {
      chartData = Object.assign({}, chartData, data);
      populateKPIs(chartData);
      renderVisibleCharts();
    }
    getJSON('/data/charts.json')
      .then(merge)
      .catch(function (err) { console.error('Failed to load charts.json:', err); });
    getJSON('/data/insights.json')
      .then(merge)
      .catch(function (err) { console.error('Failed to load insights.json:', err); });
  });
})();
