import * as Plot from "npm:@observablehq/plot";
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

const domain_max = 30000

export function plotValue(breakdown, {width} = {}) {

    return Plot.plot({
      width,
      //title: "Total portfolio value",
      x: {type: "utc", ticks: "week", label: "Time [days]"},
      y: {grid: true, inset: 10, label: "Value [euros]", domain: [0, domain_max]},
      marks: [
        Plot.areaY(breakdown, {
          x: "time",
          y: "value",
          fillOpacity: 0.2
          }),
        Plot.lineY(breakdown, {
          x: "time",
          y: "value",
          stroke: "green",
          tip: false
          }),
        Plot.ruleY([0]),
        Plot.ruleX(breakdown, Plot.pointerX({x: "time",
                                             py: "value",
                                             stroke: "red"})),
        Plot.dot(breakdown, Plot.pointerX({x: "time",
                                           y: "value",
                                           stroke: "red"})),
        Plot.text(breakdown, Plot.pointerX({px: "time",
                                            py: "value",
                                            dx: 100,
                                            dy: -18,
                                            frameAnchor: "top-left",
                                            fontVariant: "tabular-nums",
                                            text: (d) => [`Date ${d.time}`,
                                                          `Value ${d.value.toFixed(2)}`].join("    ")}))
        ]
    });
}

export function plotBreakdownBar(stackArray, {width} = {}) {

    return Plot.plot({
      width,
      //title: "Portfolio breakdown",
      x: {label: "Time [days]"},
      y: {grid: true, label: "Value [euros]", domain: [0, domain_max]},
      color: {legend: true},
      marks: [
        Plot.rectY(stackArray, {
          x: "time",
          y: "value",
          interval: "day",
          fill: "name",
          tip: true
          })
        ]
    });
}

export function plotBreakdownArea(stackArray, {width} = {}) {

  return Plot.plot({
    width,
    //title: "Portfolio breakdown",
    x: {label: "Time [days]"},
    y: {grid: true, label: "Value [euros]", domain: [0, domain_max]},
    color: {legend: true},
    marks: [
      Plot.areaY(stackArray, {
        x: "time",
        y: "value",
        interval: "day",
        fill: "name",
        tip: true
        }),
      Plot.ruleY([0])
      ]
  });
}

export function plotBreakdownChange(stackArray, date, {width} = {}) {

    const bisector = d3.bisector((i) => stackArray[i].time);
    const basis = (I, Y) => Y[I[bisector.center(I, date)]];

    return Plot.plot({

    style: "overflow: visible;",
    y: {
        //type: "log",
        grid: true,
        label: "Change in individual value (%)",
        tickFormat: ((f) => (x) => f((x - 1) * 100))(d3.format("+d")),
        //domain: [0, 100]
    },
    width,
    //title: "",
    x: {label: "Time [days]"},
    color: {legend: true},
    marks: [
      Plot.ruleY([1]),
      Plot.ruleX([date]),
      Plot.lineY(stackArray, Plot.normalizeY(basis, {
        x: "time",
        y: "value",
        interval: "day",
        stroke: "name",
        //marker: true
        //tip: true
        })),
      ]
    });
}

export function plotValueChange(breakdown, date, {width} = {}) {

    const bisector = d3.bisector((i) => breakdown[i].time);
    const basis = (I, Y) => Y[I[bisector.center(I, date)]];

    return Plot.plot({

    style: "overflow: visible;",
    y: {
        //type: "log",
        grid: true,
        label: "Change in total value (%)",
        tickFormat: ((f) => (x) => f((x - 1) * 100))(d3.format("+d")),
        //domain: [0, 100]
    },
    width,
    //title: "",
    x: {label: "Time [days]"},
    color: {legend: true},
    marks: [
      Plot.ruleY([1]),
      Plot.ruleX([date]),
      Plot.lineY(breakdown, Plot.normalizeY(basis, {
        x: "time",
        y: "value",
        interval: "day",
        //stroke: "name",
        //marker: true
        //tip: true
        })),
      ]
    });
}