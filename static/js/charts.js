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

  const FONT = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
  const ACCENT = '#3273dc';

  function baseLayout(title) {
    return {
      title: { text: title, font: { size: 16, color: '#1f2937' } },
      font: { family: FONT, color: '#333' },
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

  function pie(title, counts) {
    const labels = Object.keys(counts);
    const values = labels.map(function (k) { return counts[k]; });
    return {
      data: [{
        type: 'pie',
        labels: labels,
        values: values,
        textposition: 'inside',
        textinfo: 'percent',
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
        yaxis: { title: { text: yLabel }, gridcolor: '#eee' },
      }),
    };
  }

  // Build a dropdown (updatemenus) that toggles one visible trace at a time and
  // rewrites the title / y-axis label to match the selection.
  function dropdownButtons(keys, labelFor, axisField) {
    return keys.map(function (key, i) {
      const visible = keys.map(function (_, j) { return j === i; });
      const layoutPatch = { 'title.text': labelFor[key] };
      if (axisField) layoutPatch[axisField] = labelFor[key];
      return { method: 'update', label: labelFor[key], args: [{ visible: visible }, layoutPatch] };
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
        a.brands, a.values, '#9b59b6', '');
    },

    'chart-video-formats': function (d) {
      const formats = Object.keys(d.video_formats);
      const labels = formats.map(function (f) { return f.replace('video_', ''); });
      const supported = formats.map(function (f) { return d.video_formats[f].true; });
      const notSupported = formats.map(function (f) { return d.video_formats[f].false; });
      return {
        data: [
          { type: 'bar', name: 'Supported', x: labels, y: supported, marker: { color: '#2ecc71' } },
          { type: 'bar', name: 'Not supported', x: labels, y: notSupported, marker: { color: '#e74c3c' } },
        ],
        layout: Object.assign(baseLayout('Video Format Support'), {
          height: 500,
          barmode: 'group',
          xaxis: { automargin: true },
          yaxis: { title: { text: 'Count' }, gridcolor: '#eee' },
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
          yaxis: { gridcolor: '#eee' },
          updatemenus: [{
            buttons: dropdownButtons(specs, SPEC_LABELS, null),
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
          colorscale: 'RdBu', reversescale: true,
          texttemplate: '%{z}', textfont: { size: 9 },
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
            x: t.years, y: t.avg_price, yaxis: 'y2', line: { color: '#e67e22' },
          },
        ],
        layout: Object.assign(baseLayout('Yearly Market Trends'), {
          height: 500,
          xaxis: { title: { text: 'Announcement Year' }, automargin: true },
          yaxis: { title: { text: 'Number of Phones' }, gridcolor: '#eee' },
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
          yaxis: { title: { text: 'Price (USD)' }, gridcolor: '#eee' },
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
          yaxis: { title: { text: 'Frequency' }, gridcolor: '#eee' },
          bargap: 0.05,
          updatemenus: [{
            buttons: cols.map(function (col, i) {
              const label = COLUMN_LABELS[col] || col;
              const visible = cols.map(function (_, j) { return j === i; });
              return {
                method: 'update', label: label,
                args: [{ visible: visible }, { 'title.text': label + ' Distribution', 'xaxis.title.text': label }],
              };
            }),
            x: 1, xanchor: 'right', y: 1.18, yanchor: 'top', showactive: true,
          }],
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
      const fig = CHARTS[id](chartData);
      Plotly.newPlot(el, fig.data, fig.layout, fig.config || BASE_CONFIG);
      renderedIds.add(id);
    });
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

    fetch('/data/charts.json')
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (d) {
        chartData = d;
        renderVisibleCharts();
      })
      .catch(function (err) {
        console.error('Failed to load chart data:', err);
      });
  });
})();
