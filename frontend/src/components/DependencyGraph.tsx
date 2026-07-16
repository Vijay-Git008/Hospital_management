import React, { useState, useEffect } from 'react';

interface GraphNode {
  id: string;
  data: {
    label: string;
    type: 'patient' | 'resource';
    res_type?: string;
    status?: string;
  };
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  animated: boolean;
}

interface DependencyGraphProps {
  graphData?: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
}

export function DependencyGraph({ graphData }: DependencyGraphProps) {
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="panel-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        No network graph data. Load a simulation scenario.
      </div>
    );
  }

  // Calculate high quality coordinates for nodes using a structured grid/layered layout
  const width = 600;
  const height = 400;

  const patients = graphData.nodes.filter(n => n.data.type === 'patient');
  const resources = graphData.nodes.filter(n => n.data.type === 'resource');

  // Map node coordinates
  const coords: Record<string, { x: number; y: number }> = {};

  // Lay out patients on the left column
  patients.forEach((p, idx) => {
    const spacing = height / (patients.length + 1);
    coords[p.id] = {
      x: 100,
      y: spacing * (idx + 1)
    };
  });

  // Lay out resources on the right column
  resources.forEach((r, idx) => {
    const spacing = height / (resources.length + 1);
    coords[r.id] = {
      x: 500,
      y: spacing * (idx + 1)
    };
  });

  const [time, setTime] = useState(0);
  useEffect(() => {
    const int = setInterval(() => setTime(t => t + 1), 50);
    return () => clearInterval(int);
  }, []);

  return (
    <div className="panel-content" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', background: 'var(--bg-surface-elevated)' }}>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', alignSelf: 'flex-start', marginBottom: '8px' }}>
        Live Dependency Map: Left = Patient Agents, Right = Resource Agents (Glowing lines = Active Allocations)
      </div>

      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} style={{ flex: 1, maxHeight: '350px' }}>
        {/* Draw Edges */}
        {graphData.edges.map((e) => {
          const startBase = coords[e.source];
          const endBase = coords[e.target];
          if (!startBase || !endBase) return null;
          
          const isAllocated = e.label === 'allocated';
          // Add subtle dynamic float based on time
          const start = { x: startBase.x, y: startBase.y + Math.sin(time / 10 + startBase.x) * (isAllocated ? 0 : 3) };
          const end = { x: endBase.x, y: endBase.y + Math.cos(time / 10 + endBase.y) * (isAllocated ? 0 : 3) };

          return (
            <g key={e.id}>
              <line
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
                stroke={isAllocated ? 'var(--color-success)' : 'var(--border-color)'}
                strokeWidth={isAllocated ? 2 : 1}
                strokeDasharray={isAllocated ? 'none' : '4,4'}
                style={{
                  filter: isAllocated ? 'drop-shadow(0px 0px 4px var(--color-success))' : 'none'
                }}
              />
              {/* Optional animated pulse dot along edge */}
              {isAllocated && (
                <circle r="3" fill="var(--color-success)">
                  <animateMotion 
                    dur="3s" 
                    repeatCount="indefinite" 
                    path={`M ${start.x} ${start.y} L ${end.x} ${end.y}`} 
                  />
                </circle>
              )}
            </g>
          );
        })}

        {/* Draw Nodes */}
        {graphData.nodes.map((n) => {
          const pt = coords[n.id];
          if (!pt) return null;

          const isPatient = n.data.type === 'patient';
          const name = n.data.label;
          const status = n.data.status;
          
          let color = 'var(--text-muted)';
          if (isPatient) {
            color = status === 'Allocated' ? 'var(--color-success)' : 'var(--color-warning)';
          } else {
            color = status === 'Available' ? 'var(--color-stable)' : status === 'Occupied' ? 'var(--color-success)' : 'var(--color-warning)';
          }

          // Dynamic floating effect for nodes
          const isAllocated = (isPatient && status === 'Allocated') || (!isPatient && status === 'Occupied');
          const floatY = pt.y + (isAllocated ? 0 : Math.sin(time / 10 + pt.x) * 3);

          return (
            <g key={n.id} transform={`translate(${pt.x}, ${floatY})`}>
              <circle 
                r={isPatient ? 12 : 8} 
                fill="var(--bg-surface)" 
                stroke={color} 
                strokeWidth={2}
                style={{ filter: `drop-shadow(0px 0px 3px ${color})` }}
              />
              <text
                y={isPatient ? 22 : 18}
                textAnchor="middle"
                fill="var(--text-primary)"
                fontSize="9"
                fontFamily="var(--font-sans)"
                fontWeight="600"
              >
                {name.length > 15 ? `${name.substring(0, 12)}...` : name}
              </text>
              <text
                y={isPatient ? -18 : -14}
                textAnchor="middle"
                fill="var(--text-muted)"
                fontSize="7"
                fontFamily="var(--font-mono)"
              >
                {isPatient ? 'Patient' : n.data.res_type}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
