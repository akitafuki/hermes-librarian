/**
 * Interactive D3 Knowledge Graph for Hermes Librarian
 */
function renderGraph(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const width = container.clientWidth || 900;
  const height = container.clientHeight || 650;

  // Clear previous SVG
  container.innerHTML = '';

  const svg = d3.select(`#${containerId}`)
    .append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', [0, 0, width, height]);

  // Main zoomable group
  const g = svg.append('g');

  // Zoom behavior
  const zoom = d3.zoom()
    .scaleExtent([0.15, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
    });

  svg.call(zoom);

  // Tooltip
  const tooltip = d3.select('body').append('div')
    .attr('class', 'graph-tooltip fixed hidden z-50 px-3 py-2 text-xs rounded shadow-lg bg-slate-900 text-white pointer-events-none');

  fetch('/api/graph')
    .then(res => res.json())
    .then(data => {
      const nodes = data.nodes;
      const links = data.links;

      if (!nodes || nodes.length === 0) {
        container.innerHTML = `
          <div class="flex flex-col items-center justify-center h-full text-slate-400">
            <svg class="w-12 h-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
            <p>Archive some links to see your knowledge graph evolve!</p>
          </div>
        `;
        return;
      }

      // Force simulation setup
      const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(d => {
          if (d.target.kind === 'tag') return 60;
          if (d.target.kind === 'domain') return 75;
          return 50;
        }))
        .force('charge', d3.forceManyBody().strength(-120))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => getNodeRadius(d) + 5));

      // Draw Edges
      const link = g.append('g')
        .attr('stroke', '#94a3b8')
        .attr('stroke-opacity', 0.4)
        .selectAll('line')
        .data(links)
        .join('line')
        .attr('stroke-width', 1.2);

      // Draw Nodes
      const node = g.append('g')
        .selectAll('g')
        .data(nodes)
        .join('g')
        .attr('cursor', 'pointer')
        .call(d3.drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended)
        );

      // Node Circles
      node.append('circle')
        .attr('r', d => getNodeRadius(d))
        .attr('fill', d => getNodeColor(d))
        .attr('stroke', '#ffffff')
        .attr('stroke-width', 1.5)
        .attr('class', 'transition-all duration-150');

      // Labels for tags and domains
      node.filter(d => d.kind === 'tag' || d.kind === 'domain' || (d.kind === 'link' && nodes.length < 40))
        .append('text')
        .attr('x', d => getNodeRadius(d) + 4)
        .attr('y', 3)
        .attr('font-size', d => d.kind === 'tag' ? '12px' : '10px')
        .attr('font-family', 'sans-serif')
        .attr('font-weight', d => d.kind === 'tag' ? '600' : '400')
        .attr('fill', 'currentColor')
        .attr('class', 'text-slate-700 dark:text-slate-300 pointer-events-none select-none')
        .text(d => d.label);

      // Tooltip Interactions
      node.on('mouseover', (event, d) => {
        tooltip.style('left', (event.pageX + 12) + 'px')
          .style('top', (event.pageY - 12) + 'px')
          .classed('hidden', false)
          .html(`<strong>${escapeHtml(d.label)}</strong><br><span class="text-slate-400 capitalize">${d.kind}</span>${d.count ? ` (${d.count})` : ''}`);
      })
      .on('mousemove', (event) => {
        tooltip.style('left', (event.pageX + 12) + 'px')
          .style('top', (event.pageY - 12) + 'px');
      })
      .on('mouseout', () => {
        tooltip.classed('hidden', true);
      });

      // Highlight connections on single click
      let selectedNode = null;
      node.on('click', (event, d) => {
        event.stopPropagation();
        if (selectedNode === d.id) {
          // Reset highlights
          node.style('opacity', 1);
          link.style('opacity', 0.4);
          selectedNode = null;
          return;
        }

        selectedNode = d.id;
        const connectedNodes = new Set([d.id]);
        links.forEach(l => {
          const s = typeof l.source === 'object' ? l.source.id : l.source;
          const t = typeof l.target === 'object' ? l.target.id : l.target;
          if (s === d.id) connectedNodes.add(t);
          if (t === d.id) connectedNodes.add(s);
        });

        node.style('opacity', n => connectedNodes.has(n.id) ? 1 : 0.15);
        link.style('opacity', l => {
          const s = typeof l.source === 'object' ? l.source.id : l.source;
          const t = typeof l.target === 'object' ? l.target.id : l.target;
          return (s === d.id || t === d.id) ? 0.9 : 0.05;
        });
      });

      // Double click link node -> open URL
      node.on('dblclick', (event, d) => {
        if (d.url) {
          window.open(d.url, '_blank');
        }
      });

      svg.on('click', () => {
        node.style('opacity', 1);
        link.style('opacity', 0.4);
        selectedNode = null;
      });

      // Simulation tick
      simulation.on('tick', () => {
        link
          .attr('x1', d => d.source.x)
          .attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x)
          .attr('y2', d => d.target.y);

        node.attr('transform', d => `translate(${d.x},${d.y})`);
      });

      // Drag functions
      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }

      // Graph search filter input
      const searchBox = document.getElementById('graph-search');
      if (searchBox) {
        searchBox.addEventListener('input', (e) => {
          const val = e.target.value.toLowerCase().trim();
          if (!val) {
            node.style('opacity', 1);
            link.style('opacity', 0.4);
            return;
          }
          node.style('opacity', d => d.label.toLowerCase().includes(val) ? 1 : 0.1);
          link.style('opacity', 0.05);
        });
      }

      // Reset zoom button
      const resetBtn = document.getElementById('graph-reset-btn');
      if (resetBtn) {
        resetBtn.addEventListener('click', () => {
          svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
        });
      }
    });

  function getNodeRadius(d) {
    if (d.kind === 'tag') return Math.min(22, 9 + (d.count || 1) * 2.5);
    if (d.kind === 'domain') return Math.min(18, 8 + (d.count || 1) * 1.5);
    return 6;
  }

  function getNodeColor(d) {
    if (d.kind === 'tag') return '#8b5cf6'; // Violet
    if (d.kind === 'domain') return '#10b981'; // Emerald
    // Link nodes by type
    if (d.type === 'github') return '#0f172a';
    if (d.type === 'video') return '#ef4444';
    if (d.type === 'paper') return '#f59e0b';
    if (d.type === 'tool') return '#06b6d4';
    return '#3b82f6'; // Blue default
  }

  function escapeHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
}
