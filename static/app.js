function renderPlot(divId, figJson){
  const el = document.getElementById(divId);
  if(!el) return;
  const fig = (typeof figJson === "string") ? JSON.parse(figJson) : figJson;
  Plotly.newPlot(el, fig.data, fig.layout, {responsive:true, displaylogo:false});
}

function initDataTable(selector){
  const el = $(selector);
  if(!el.length) return;
  el.DataTable({
    pageLength: 25,
    lengthMenu: [10, 25, 50, 100],
    order: [],
    scrollX: true
  });
}
