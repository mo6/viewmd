---
title: "NVIDIA (NVDA) 1-year stock price: a Mermaid xychart-beta demo"
author: viewmd
tags: [mermaid, xychart, demo]
status: draft
---

# NVIDIA (NVDA) 1-year stock price

This page uses NVIDIA (NVDA): a real, publicly traded, AI-infrastructure-adjacent stock, plotted with Mermaid's `xychart-beta` diagram type.

Month-end closing prices, August 2025 through August 2026:

```mermaid
xychart-beta
    title "NVDA month-end close, Aug 2025 - Aug 2026"
    x-axis [Aug25, Sep25, Oct25, Nov25, Dec25, Jan26, Feb26, Mar26, Apr26, May26, Jun26, Jul26, Aug26]
    y-axis "USD" 150 --> 230
    line [173.95, 186.34, 202.23, 176.77, 186.27, 190.90, 176.97, 174.20, 199.34, 210.89, 200.09, 200.75, 225.16]
```

Viewing this file with `./viewmd.sh docs/nvidia-stock-xychart.md` renders the chart above as a stair-step line chart (VIEWMD-0048). Plot width follows `--width` (capped at the viewport; never narrower than half of it).

Data source: month-end close prices as reported via public financial-data aggregators
(stockanalysis.com, StatMuse) in August 2026; treat as approximate, not exchange-verified ticks.
