---
theme: dashboard
toc: false
---

# Total value

```js
import {plotValue, plotBreakdownBar, plotBreakdownArea} from "./components/plots.js";
import {createStack, getPertChange} from "./components/helpers.js";
```

```js
const breakdown = FileAttachment("./data/value.json").json();
```

<!-- Cards with big numbers -->

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Last 7 days change [%]</h2>
    <span class="big">${getPertChange(breakdown, 7)}</span>
  </div>
  <div class="card">
    <h2>Last 30 days change [%]</h2>
    <span class="big">${getPertChange(breakdown, 30)}</span>
  </div>
</div>

<!--- Re-render whenever the container resizes --->
<div class="grid grid-cols-1">
    <div class="card">${resize((width) => plotValue(breakdown, {width}))} </div>
</div>

# Breakdown

<div class="grid grid-cols-1">
    <div class="card">${resize((width) => plotBreakdownBar(createStack(breakdown), {width}))} </div>
</div>

<div class="grid grid-cols-1">
    <div class="card">${resize((width) => plotBreakdownArea(createStack(breakdown), {width}))} </div>
</div>