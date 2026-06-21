/**
 * Animated flow diagrams for each selling point.
 * Pure CSS animations with SVG — no external libs needed.
 * Each diagram shows the workflow visually with:
 *   - Moving data packets along paths
 *   - Pulsing/glowing active nodes
 *   - Flowing arrows
 */

import React from 'react';

// ─── Shared styling for flow containers ──────────────────────────────────────

const flowStyle: React.CSSProperties = {
  width: '100%',
  height: '120px',
  marginTop: '0.75rem',
  borderRadius: '10px',
  background: 'var(--rf-bg-subtle)',
  border: '1px solid var(--rf-border-light)',
  overflow: 'hidden',
  position: 'relative',
};

// ─── 1. Any Language Flow ─────────────────────────────────────────────────────

export function FlowAnyLanguage() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="120" viewBox="0 0 400 120">
        {/* Nodes */}
        <rect x="10" y="20" width="60" height="30" rx="6" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1.5">
          <animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="40" y="39" textAnchor="middle" fontSize="9" fontWeight="600" fill="#1e40af">Python</text>

        <rect x="10" y="60" width="60" height="30" rx="6" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1.5">
          <animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="40" y="79" textAnchor="middle" fontSize="9" fontWeight="600" fill="#92400e">JS/Go</text>

        {/* API box */}
        <rect x="160" y="30" width="80" height="50" rx="8" fill="#ede9fe" stroke="#7c3aed" strokeWidth="2" />
        <text x="200" y="55" textAnchor="middle" fontSize="10" fontWeight="700" fill="#5b21b6">HTTP API</text>
        <text x="200" y="68" textAnchor="middle" fontSize="7" fill="#7c3aed">JSON in/out</text>

        {/* RAGForge box */}
        <rect x="300" y="30" width="80" height="50" rx="8" fill="#f0fdf4" stroke="#22c55e" strokeWidth="2" />
        <text x="340" y="55" textAnchor="middle" fontSize="10" fontWeight="700" fill="#166534">RAGForge</text>
        <text x="340" y="68" textAnchor="middle" fontSize="7" fill="#22c55e">All modules</text>

        {/* Arrows with flowing packets */}
        <line x1="72" y1="35" x2="158" y2="50" stroke="#94a3b8" strokeWidth="1" strokeDasharray="4,3" />
        <line x1="72" y1="75" x2="158" y2="60" stroke="#94a3b8" strokeWidth="1" strokeDasharray="4,3" />
        <line x1="242" y1="55" x2="298" y2="55" stroke="#94a3b8" strokeWidth="1" strokeDasharray="4,3" />

        {/* Moving packets */}
        <circle r="4" fill="#3b82f6">
          <animateMotion dur="2s" repeatCount="indefinite" path="M72,35 L158,50" />
        </circle>
        <circle r="4" fill="#f59e0b">
          <animateMotion dur="2.5s" repeatCount="indefinite" path="M72,75 L158,60" />
        </circle>
        <circle r="3" fill="#7c3aed">
          <animateMotion dur="1.5s" repeatCount="indefinite" path="M242,55 L298,55" />
        </circle>
      </svg>
    </div>
  );
}

// ─── 2. Zero Dependencies Flow ────────────────────────────────────────────────

export function FlowZeroDeps() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="120" viewBox="0 0 400 120">
        <text x="20" y="25" fontSize="9" fill="#94a3b8">pip install ragforge</text>
        {/* Progress bar animation */}
        <rect x="20" y="35" width="360" height="12" rx="6" fill="#f1f5f9" stroke="#e2e8f0" />
        <rect x="20" y="35" width="0" height="12" rx="6" fill="#22c55e">
          <animate attributeName="width" from="0" to="360" dur="1.5s" repeatCount="indefinite" />
        </rect>
        {/* Checkmarks appearing */}
        <text x="20" y="70" fontSize="9" fill="#22c55e" opacity="0">
          ✓ parsing ready
          <animate attributeName="opacity" from="0" to="1" begin="0.5s" dur="0.3s" fill="freeze" repeatCount="indefinite" />
        </text>
        <text x="20" y="85" fontSize="9" fill="#22c55e" opacity="0">
          ✓ chunking ready
          <animate attributeName="opacity" from="0" to="1" begin="0.8s" dur="0.3s" fill="freeze" repeatCount="indefinite" />
        </text>
        <text x="20" y="100" fontSize="9" fill="#22c55e" opacity="0">
          ✓ evaluation ready
          <animate attributeName="opacity" from="0" to="1" begin="1.1s" dur="0.3s" fill="freeze" repeatCount="indefinite" />
        </text>
        <text x="150" y="70" fontSize="9" fill="#22c55e" opacity="0">
          ✓ coordination ready
          <animate attributeName="opacity" from="0" to="1" begin="1.4s" dur="0.3s" fill="freeze" repeatCount="indefinite" />
        </text>
        <text x="150" y="85" fontSize="9" fill="#64748b">0 external deps</text>
        <text x="300" y="70" fontSize="11" fontWeight="700" fill="#5b4ff5" opacity="0">
          Ready! 🚀
          <animate attributeName="opacity" from="0" to="1" begin="1.5s" dur="0.5s" fill="freeze" repeatCount="indefinite" />
        </text>
      </svg>
    </div>
  );
}

// ─── 3. Tables & Code Intact Flow ─────────────────────────────────────────────

export function FlowChunkingIntact() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="120" viewBox="0 0 400 120">
        {/* Document with table */}
        <rect x="15" y="15" width="70" height="90" rx="4" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5" />
        <rect x="22" y="40" width="56" height="30" rx="2" fill="#dbeafe" stroke="#93c5fd" strokeWidth="0.5" />
        <text x="50" y="58" textAnchor="middle" fontSize="7" fill="#1e40af">TABLE</text>
        <text x="50" y="28" textAnchor="middle" fontSize="7" fill="#64748b">doc.md</text>
        <rect x="22" y="76" width="56" height="20" rx="2" fill="#dcfce7" stroke="#86efac" strokeWidth="0.5" />
        <text x="50" y="89" textAnchor="middle" fontSize="6" fill="#166534">code block</text>

        {/* Arrow */}
        <path d="M90,55 L140,55" stroke="#94a3b8" strokeWidth="1.5" strokeDasharray="4,3" markerEnd="url(#arrowGreen)" />
        <circle r="4" fill="#10b981">
          <animateMotion dur="1.5s" repeatCount="indefinite" path="M90,55 L140,55" />
        </circle>

        {/* Chunks output — table intact */}
        <rect x="150" y="10" width="100" height="35" rx="4" fill="#fff" stroke="#10b981" strokeWidth="1.5">
          <animate attributeName="stroke-opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="200" y="25" textAnchor="middle" fontSize="7" fontWeight="600" fill="#166534">Chunk 1</text>
        <rect x="160" y="28" width="80" height="12" rx="2" fill="#dbeafe" />
        <text x="200" y="37" textAnchor="middle" fontSize="6" fill="#1e40af">TABLE ✓ intact</text>

        <rect x="150" y="52" width="100" height="35" rx="4" fill="#fff" stroke="#10b981" strokeWidth="1.5">
          <animate attributeName="stroke-opacity" values="0.4;1;0.4" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="200" y="67" textAnchor="middle" fontSize="7" fontWeight="600" fill="#166534">Chunk 2</text>
        <rect x="160" y="70" width="80" height="12" rx="2" fill="#dcfce7" />
        <text x="200" y="79" textAnchor="middle" fontSize="6" fill="#166534">CODE ✓ intact</text>

        {/* vs bad chunking */}
        <text x="290" y="20" fontSize="7" fill="#ef4444">❌ Fixed chunking:</text>
        <rect x="290" y="25" width="90" height="18" rx="3" fill="#fef2f2" stroke="#fca5a5" />
        <text x="335" y="37" textAnchor="middle" fontSize="6" fill="#dc2626">TABLE cut in half</text>
        <rect x="290" y="48" width="90" height="18" rx="3" fill="#fef2f2" stroke="#fca5a5" />
        <text x="335" y="60" textAnchor="middle" fontSize="6" fill="#dc2626">CODE broken</text>
        <text x="290" y="85" fontSize="7" fill="#10b981">✓ Structure-aware:</text>
        <text x="290" y="97" fontSize="7" fontWeight="600" fill="#10b981">Everything stays whole</text>

        <defs>
          <marker id="arrowGreen" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6" fill="#10b981" />
          </marker>
        </defs>
      </svg>
    </div>
  );
}

// ─── 4. Multi-Agent Coordination Flow ─────────────────────────────────────────

export function FlowCoordination() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="120" viewBox="0 0 400 120">
        {/* Blackboard (center) */}
        <rect x="150" y="25" width="100" height="70" rx="8" fill="#fdf4ff" stroke="#a855f7" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="1;0.5;1" dur="3s" repeatCount="indefinite" />
        </rect>
        <text x="200" y="45" textAnchor="middle" fontSize="9" fontWeight="700" fill="#7e22ce">Blackboard</text>
        <text x="200" y="58" textAnchor="middle" fontSize="7" fill="#a855f7">shared state</text>
        <text x="200" y="72" textAnchor="middle" fontSize="6" fill="#c084fc">findings ✓</text>
        <text x="200" y="83" textAnchor="middle" fontSize="6" fill="#c084fc">review ✓</text>

        {/* Agent 1: Researcher */}
        <rect x="15" y="20" width="65" height="30" rx="6" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1.5">
          <animate attributeName="opacity" values="1;0.7;1" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="47" y="39" textAnchor="middle" fontSize="7" fontWeight="600" fill="#1e40af">Researcher</text>

        {/* Agent 2: Critic */}
        <rect x="15" y="65" width="65" height="30" rx="6" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1.5">
          <animate attributeName="opacity" values="0.7;1;0.7" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="47" y="84" textAnchor="middle" fontSize="7" fontWeight="600" fill="#92400e">Critic</text>

        {/* Agent 3: Writer */}
        <rect x="320" y="40" width="65" height="30" rx="6" fill="#dcfce7" stroke="#22c55e" strokeWidth="1.5">
          <animate attributeName="opacity" values="0.5;1;0.5" dur="2.5s" repeatCount="indefinite" />
        </rect>
        <text x="352" y="59" textAnchor="middle" fontSize="7" fontWeight="600" fill="#166534">Writer</text>

        {/* Arrows: agents → board → agents (no direct messaging!) */}
        <circle r="3" fill="#3b82f6">
          <animateMotion dur="2s" repeatCount="indefinite" path="M80,35 L148,45" />
        </circle>
        <circle r="3" fill="#f59e0b">
          <animateMotion dur="2.5s" repeatCount="indefinite" path="M80,80 L148,65" />
        </circle>
        <circle r="3" fill="#22c55e">
          <animateMotion dur="2s" repeatCount="indefinite" path="M252,55 L318,55" />
        </circle>

        {/* Label */}
        <text x="200" y="112" textAnchor="middle" fontSize="7" fill="#64748b">No direct messaging — only read/write board</text>
      </svg>
    </div>
  );
}

// ─── 5. Evaluation / Prove Changes Help Flow ──────────────────────────────────

export function FlowEvaluation() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="120" viewBox="0 0 400 120">
        {/* Config A */}
        <rect x="15" y="15" width="70" height="40" rx="6" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1.5" />
        <text x="50" y="33" textAnchor="middle" fontSize="8" fontWeight="600" fill="#1e40af">Config A</text>
        <text x="50" y="46" textAnchor="middle" fontSize="6" fill="#3b82f6">structure</text>

        {/* Config B */}
        <rect x="15" y="65" width="70" height="40" rx="6" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1.5" />
        <text x="50" y="83" textAnchor="middle" fontSize="8" fontWeight="600" fill="#92400e">Config B</text>
        <text x="50" y="96" textAnchor="middle" fontSize="6" fill="#f59e0b">fixed</text>

        {/* Golden dataset */}
        <rect x="120" y="40" width="70" height="35" rx="6" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5" />
        <text x="155" y="57" textAnchor="middle" fontSize="7" fontWeight="600" fill="#475569">Golden Set</text>
        <text x="155" y="68" textAnchor="middle" fontSize="6" fill="#94a3b8">20 questions</text>

        {/* Arrows */}
        <circle r="3" fill="#3b82f6">
          <animateMotion dur="1.5s" repeatCount="indefinite" path="M87,35 L118,52" />
        </circle>
        <circle r="3" fill="#f59e0b">
          <animateMotion dur="1.8s" repeatCount="indefinite" path="M87,85 L118,62" />
        </circle>

        {/* Result bars */}
        <text x="220" y="25" fontSize="7" fill="#475569">Hit Rate:</text>
        <rect x="270" y="18" width="80" height="8" rx="4" fill="#f1f5f9" />
        <rect x="270" y="18" width="0" height="8" rx="4" fill="#3b82f6">
          <animate attributeName="width" from="0" to="68" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="355" y="25" fontSize="7" fontWeight="600" fill="#3b82f6">85%</text>

        <text x="220" y="43" fontSize="7" fill="#475569">MRR:</text>
        <rect x="270" y="36" width="80" height="8" rx="4" fill="#f1f5f9" />
        <rect x="270" y="36" width="0" height="8" rx="4" fill="#3b82f6">
          <animate attributeName="width" from="0" to="58" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="355" y="43" fontSize="7" fontWeight="600" fill="#3b82f6">73%</text>

        <text x="220" y="70" fontSize="7" fill="#475569">Hit Rate:</text>
        <rect x="270" y="63" width="80" height="8" rx="4" fill="#f1f5f9" />
        <rect x="270" y="63" width="0" height="8" rx="4" fill="#f59e0b">
          <animate attributeName="width" from="0" to="45" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="355" y="70" fontSize="7" fontWeight="600" fill="#f59e0b">56%</text>

        <text x="220" y="100" fontSize="8" fontWeight="700" fill="#22c55e">✓ Config A wins (+29%)</text>
      </svg>
    </div>
  );
}

// ─── 6. Grounded Answers Flow ─────────────────────────────────────────────────

export function FlowGroundedAnswers() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="120" viewBox="0 0 400 120">
        {/* Question */}
        <rect x="10" y="40" width="70" height="35" rx="6" fill="#ede9fe" stroke="#7c3aed" strokeWidth="1.5" />
        <text x="45" y="57" textAnchor="middle" fontSize="7" fontWeight="600" fill="#5b21b6">Question</text>
        <text x="45" y="68" textAnchor="middle" fontSize="6" fill="#7c3aed">"refund?"</text>

        {/* Retrieved chunks */}
        <rect x="110" y="20" width="70" height="22" rx="4" fill="#dbeafe" stroke="#93c5fd" strokeWidth="1">
          <animate attributeName="opacity" values="0.5;1;0.5" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="145" y="34" textAnchor="middle" fontSize="6" fill="#1e40af">chunk [0.94]</text>
        <rect x="110" y="48" width="70" height="22" rx="4" fill="#dbeafe" stroke="#93c5fd" strokeWidth="1">
          <animate attributeName="opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="145" y="62" textAnchor="middle" fontSize="6" fill="#1e40af">chunk [0.81]</text>
        <rect x="110" y="76" width="70" height="22" rx="4" fill="#f1f5f9" stroke="#e2e8f0" strokeWidth="1" />
        <text x="145" y="90" textAnchor="middle" fontSize="6" fill="#94a3b8">chunk [0.32]</text>

        {/* LLM */}
        <rect x="210" y="35" width="60" height="45" rx="8" fill="#fdf4ff" stroke="#a855f7" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="1;0.4;1" dur="1.5s" repeatCount="indefinite" />
        </rect>
        <text x="240" y="57" textAnchor="middle" fontSize="8" fontWeight="700" fill="#7e22ce">LLM</text>
        <text x="240" y="69" textAnchor="middle" fontSize="6" fill="#a855f7">grounded</text>

        {/* Answer */}
        <rect x="300" y="30" width="90" height="55" rx="6" fill="#f0fdf4" stroke="#22c55e" strokeWidth="1.5" />
        <text x="345" y="48" textAnchor="middle" fontSize="7" fontWeight="600" fill="#166534">Answer</text>
        <text x="345" y="60" textAnchor="middle" fontSize="6" fill="#22c55e">+ sources cited</text>
        <text x="345" y="72" textAnchor="middle" fontSize="6" fill="#22c55e">or refuses ✓</text>

        {/* Moving packets */}
        <circle r="3" fill="#7c3aed">
          <animateMotion dur="1.5s" repeatCount="indefinite" path="M82,57 L108,57" />
        </circle>
        <circle r="3" fill="#3b82f6">
          <animateMotion dur="1.8s" repeatCount="indefinite" path="M182,50 L208,50" />
        </circle>
        <circle r="3" fill="#22c55e">
          <animateMotion dur="1.5s" repeatCount="indefinite" path="M272,57 L298,57" />
        </circle>
      </svg>
    </div>
  );
}

// ─── 7. Migration at Scale Flow ───────────────────────────────────────────────

export function FlowMigration() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="120" viewBox="0 0 400 120">
        {/* Old model */}
        <rect x="15" y="30" width="70" height="50" rx="6" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1.5" />
        <text x="50" y="50" textAnchor="middle" fontSize="7" fontWeight="600" fill="#92400e">Old Model</text>
        <text x="50" y="63" textAnchor="middle" fontSize="6" fill="#f59e0b">1M chunks</text>
        <text x="50" y="74" textAnchor="middle" fontSize="6" fill="#d97706">LIVE ●</text>

        {/* Shadow re-embed */}
        <rect x="130" y="15" width="80" height="35" rx="6" fill="#ede9fe" stroke="#7c3aed" strokeWidth="1.5">
          <animate attributeName="stroke-opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="170" y="33" textAnchor="middle" fontSize="7" fontWeight="600" fill="#5b21b6">Re-embed</text>
        <text x="170" y="44" textAnchor="middle" fontSize="6" fill="#7c3aed">shadow index</text>

        {/* Validate */}
        <rect x="130" y="60" width="80" height="35" rx="6" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1.5" />
        <text x="170" y="78" textAnchor="middle" fontSize="7" fontWeight="600" fill="#1e40af">Validate</text>
        <text x="170" y="89" textAnchor="middle" fontSize="6" fill="#3b82f6">quality OK?</text>

        {/* Swap */}
        <rect x="255" y="35" width="55" height="40" rx="6" fill="#dcfce7" stroke="#22c55e" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="0.5;1;0.5" dur="1.5s" repeatCount="indefinite" />
        </rect>
        <text x="282" y="55" textAnchor="middle" fontSize="7" fontWeight="700" fill="#166534">Swap</text>
        <text x="282" y="66" textAnchor="middle" fontSize="6" fill="#22c55e">atomic</text>

        {/* New model */}
        <rect x="340" y="30" width="50" height="50" rx="6" fill="#f0fdf4" stroke="#22c55e" strokeWidth="2" />
        <text x="365" y="50" textAnchor="middle" fontSize="7" fontWeight="600" fill="#166534">New</text>
        <text x="365" y="63" textAnchor="middle" fontSize="6" fill="#22c55e">LIVE ●</text>

        {/* Flowing packets */}
        <circle r="3" fill="#f59e0b">
          <animateMotion dur="2s" repeatCount="indefinite" path="M87,55 L128,32" />
        </circle>
        <circle r="3" fill="#3b82f6">
          <animateMotion dur="2s" repeatCount="indefinite" path="M212,77 L253,55" />
        </circle>
        <circle r="3" fill="#22c55e">
          <animateMotion dur="1.5s" repeatCount="indefinite" path="M312,55 L338,55" />
        </circle>

        <text x="200" y="112" textAnchor="middle" fontSize="7" fill="#64748b">Production stays live during migration</text>
      </svg>
    </div>
  );
}

// ─── 8. Context-Aware Chunking Flow ───────────────────────────────────────────

export function FlowContextChunking() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="120" viewBox="0 0 400 120">
        {/* Document structure analysis */}
        <rect x="15" y="10" width="80" height="100" rx="4" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5" />
        <text x="55" y="25" textAnchor="middle" fontSize="7" fontWeight="600" fill="#475569">Document</text>
        {/* Headers detected */}
        <rect x="22" y="30" width="66" height="10" rx="2" fill="#ede9fe" />
        <text x="55" y="38" textAnchor="middle" fontSize="5" fill="#5b21b6"># Header 1</text>
        <rect x="22" y="43" width="66" height="15" rx="2" fill="#f8fafc" />
        <text x="55" y="53" textAnchor="middle" fontSize="5" fill="#64748b">paragraph...</text>
        <rect x="22" y="61" width="66" height="10" rx="2" fill="#ede9fe" />
        <text x="55" y="69" textAnchor="middle" fontSize="5" fill="#5b21b6">## Header 2</text>
        <rect x="22" y="74" width="66" height="12" rx="2" fill="#dbeafe" />
        <text x="55" y="83" textAnchor="middle" fontSize="5" fill="#1e40af">| table |</text>
        <rect x="22" y="89" width="66" height="14" rx="2" fill="#dcfce7" />
        <text x="55" y="99" textAnchor="middle" fontSize="5" fill="#166534">```code```</text>

        {/* Analysis step */}
        <rect x="120" y="35" width="75" height="45" rx="8" fill="#fdf4ff" stroke="#a855f7" strokeWidth="1.5">
          <animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="157" y="53" textAnchor="middle" fontSize="7" fontWeight="600" fill="#7e22ce">Analyze</text>
        <text x="157" y="65" textAnchor="middle" fontSize="6" fill="#a855f7">structure</text>
        <text x="157" y="75" textAnchor="middle" fontSize="6" fill="#a855f7">first</text>

        {/* Smart output */}
        <rect x="230" y="10" width="85" height="28" rx="5" fill="#f0fdf4" stroke="#22c55e" strokeWidth="1.5">
          <animate attributeName="opacity" values="1;0.6;1" dur="2.5s" repeatCount="indefinite" />
        </rect>
        <text x="272" y="24" textAnchor="middle" fontSize="6" fontWeight="600" fill="#166534">section: Header 1</text>
        <text x="272" y="33" textAnchor="middle" fontSize="5" fill="#22c55e">paragraph text</text>

        <rect x="230" y="44" width="85" height="28" rx="5" fill="#f0fdf4" stroke="#22c55e" strokeWidth="1.5">
          <animate attributeName="opacity" values="0.6;1;0.6" dur="2.5s" repeatCount="indefinite" />
        </rect>
        <text x="272" y="58" textAnchor="middle" fontSize="6" fontWeight="600" fill="#166534">section: Header 2</text>
        <text x="272" y="67" textAnchor="middle" fontSize="5" fill="#22c55e">table INTACT ✓</text>

        <rect x="230" y="78" width="85" height="28" rx="5" fill="#f0fdf4" stroke="#22c55e" strokeWidth="1.5">
          <animate attributeName="opacity" values="0.8;1;0.8" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="272" y="92" textAnchor="middle" fontSize="6" fontWeight="600" fill="#166534">section: Header 2</text>
        <text x="272" y="101" textAnchor="middle" fontSize="5" fill="#22c55e">code INTACT ✓</text>

        {/* Flowing packets */}
        <circle r="3" fill="#a855f7">
          <animateMotion dur="1.5s" repeatCount="indefinite" path="M97,55 L118,55" />
        </circle>
        <circle r="3" fill="#22c55e">
          <animateMotion dur="1.8s" repeatCount="indefinite" path="M197,57 L228,57" />
        </circle>

        <text x="350" y="55" fontSize="7" fontWeight="600" fill="#5b4ff5">Context</text>
        <text x="350" y="67" fontSize="7" fontWeight="600" fill="#5b4ff5">first,</text>
        <text x="350" y="79" fontSize="7" fontWeight="600" fill="#5b4ff5">then split</text>
      </svg>
    </div>
  );
}

// ─── 9. Model Swap Safely Flow ────────────────────────────────────────────────

export function FlowModelSwap() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="120" viewBox="0 0 400 120">
        {/* Step indicators */}
        <circle cx="50" cy="55" r="18" fill="#dbeafe" stroke="#3b82f6" strokeWidth="2">
          <animate attributeName="r" values="18;20;18" dur="2s" repeatCount="indefinite" />
        </circle>
        <text x="50" y="52" textAnchor="middle" fontSize="7" fontWeight="700" fill="#1e40af">1</text>
        <text x="50" y="62" textAnchor="middle" fontSize="5" fill="#3b82f6">Shadow</text>

        <circle cx="140" cy="55" r="18" fill="#ede9fe" stroke="#7c3aed" strokeWidth="2">
          <animate attributeName="r" values="18;20;18" dur="2s" begin="0.5s" repeatCount="indefinite" />
        </circle>
        <text x="140" y="52" textAnchor="middle" fontSize="7" fontWeight="700" fill="#5b21b6">2</text>
        <text x="140" y="62" textAnchor="middle" fontSize="5" fill="#7c3aed">Validate</text>

        <circle cx="230" cy="55" r="18" fill="#dcfce7" stroke="#22c55e" strokeWidth="2">
          <animate attributeName="r" values="18;20;18" dur="2s" begin="1s" repeatCount="indefinite" />
        </circle>
        <text x="230" y="52" textAnchor="middle" fontSize="7" fontWeight="700" fill="#166534">3</text>
        <text x="230" y="62" textAnchor="middle" fontSize="5" fill="#22c55e">Swap</text>

        <circle cx="320" cy="55" r="18" fill="#fef3c7" stroke="#f59e0b" strokeWidth="2">
          <animate attributeName="r" values="18;20;18" dur="2s" begin="1.5s" repeatCount="indefinite" />
        </circle>
        <text x="320" y="52" textAnchor="middle" fontSize="7" fontWeight="700" fill="#92400e">4</text>
        <text x="320" y="62" textAnchor="middle" fontSize="5" fill="#f59e0b">Backup</text>

        {/* Connecting arrows */}
        <line x1="70" y1="55" x2="120" y2="55" stroke="#94a3b8" strokeWidth="1.5" strokeDasharray="3,2" />
        <line x1="160" y1="55" x2="210" y2="55" stroke="#94a3b8" strokeWidth="1.5" strokeDasharray="3,2" />
        <line x1="250" y1="55" x2="300" y2="55" stroke="#94a3b8" strokeWidth="1.5" strokeDasharray="3,2" />

        {/* Moving packets */}
        <circle r="3" fill="#3b82f6">
          <animateMotion dur="1.5s" repeatCount="indefinite" path="M70,55 L120,55" />
        </circle>
        <circle r="3" fill="#7c3aed">
          <animateMotion dur="1.5s" repeatCount="indefinite" path="M160,55 L210,55" begin="0.5s" />
        </circle>
        <circle r="3" fill="#22c55e">
          <animateMotion dur="1.5s" repeatCount="indefinite" path="M250,55 L300,55" begin="1s" />
        </circle>

        <text x="200" y="95" textAnchor="middle" fontSize="7" fill="#64748b">If quality drops → auto-abort, old stays live</text>
        <text x="200" y="108" textAnchor="middle" fontSize="7" fontWeight="600" fill="#22c55e">Zero downtime, zero data loss</text>
      </svg>
    </div>
  );
}

// ─── 10. One Tool Not Six Flow ────────────────────────────────────────────────

export function FlowOneTool() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="120" viewBox="0 0 400 120">
        {/* Center: RAGForge */}
        <rect x="155" y="30" width="90" height="55" rx="12" fill="#ede9fe" stroke="#5b4ff5" strokeWidth="2.5">
          <animate attributeName="stroke-opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="200" y="52" textAnchor="middle" fontSize="10" fontWeight="800" fill="#5b21b6">RAGForge</text>
        <text x="200" y="65" textAnchor="middle" fontSize="6" fill="#7c3aed">pip install ragforge</text>
        <text x="200" y="77" textAnchor="middle" fontSize="6" fill="#a855f7">1 tool, 1 CLI, 1 API</text>

        {/* Surrounding modules */}
        <rect x="10" y="10" width="55" height="22" rx="4" fill="#dbeafe" stroke="#93c5fd" strokeWidth="1">
          <animate attributeName="opacity" values="0.7;1;0.7" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="37" y="24" textAnchor="middle" fontSize="6" fill="#1e40af">Parse</text>

        <rect x="10" y="38" width="55" height="22" rx="4" fill="#dcfce7" stroke="#86efac" strokeWidth="1">
          <animate attributeName="opacity" values="1;0.7;1" dur="2s" repeatCount="indefinite" />
        </rect>
        <text x="37" y="52" textAnchor="middle" fontSize="6" fill="#166534">Chunk</text>

        <rect x="10" y="66" width="55" height="22" rx="4" fill="#fef3c7" stroke="#fcd34d" strokeWidth="1">
          <animate attributeName="opacity" values="0.7;1;0.7" dur="2.5s" repeatCount="indefinite" />
        </rect>
        <text x="37" y="80" textAnchor="middle" fontSize="6" fill="#92400e">Retrieve</text>

        <rect x="10" y="94" width="55" height="22" rx="4" fill="#fdf4ff" stroke="#d8b4fe" strokeWidth="1">
          <animate attributeName="opacity" values="1;0.7;1" dur="2.2s" repeatCount="indefinite" />
        </rect>
        <text x="37" y="108" textAnchor="middle" fontSize="6" fill="#7e22ce">Generate</text>

        <rect x="335" y="10" width="55" height="22" rx="4" fill="#f0fdf4" stroke="#86efac" strokeWidth="1">
          <animate attributeName="opacity" values="0.7;1;0.7" dur="2.3s" repeatCount="indefinite" />
        </rect>
        <text x="362" y="24" textAnchor="middle" fontSize="6" fill="#166534">Eval</text>

        <rect x="335" y="38" width="55" height="22" rx="4" fill="#fef3c7" stroke="#fcd34d" strokeWidth="1">
          <animate attributeName="opacity" values="1;0.7;1" dur="2.1s" repeatCount="indefinite" />
        </rect>
        <text x="362" y="52" textAnchor="middle" fontSize="6" fill="#92400e">Quantize</text>

        <rect x="335" y="66" width="55" height="22" rx="4" fill="#dbeafe" stroke="#93c5fd" strokeWidth="1">
          <animate attributeName="opacity" values="0.7;1;0.7" dur="1.9s" repeatCount="indefinite" />
        </rect>
        <text x="362" y="80" textAnchor="middle" fontSize="6" fill="#1e40af">Migrate</text>

        <rect x="335" y="94" width="55" height="22" rx="4" fill="#fce7f3" stroke="#f9a8d4" strokeWidth="1">
          <animate attributeName="opacity" values="1;0.7;1" dur="2.4s" repeatCount="indefinite" />
        </rect>
        <text x="362" y="108" textAnchor="middle" fontSize="6" fill="#be185d">Agents</text>

        {/* Connections flowing inward */}
        <circle r="2.5" fill="#3b82f6">
          <animateMotion dur="2s" repeatCount="indefinite" path="M67,21 L153,50" />
        </circle>
        <circle r="2.5" fill="#22c55e">
          <animateMotion dur="2.2s" repeatCount="indefinite" path="M67,49 L153,55" />
        </circle>
        <circle r="2.5" fill="#f59e0b">
          <animateMotion dur="2.4s" repeatCount="indefinite" path="M67,77 L153,58" />
        </circle>
        <circle r="2.5" fill="#a855f7">
          <animateMotion dur="2.6s" repeatCount="indefinite" path="M67,105 L153,63" />
        </circle>
        <circle r="2.5" fill="#22c55e">
          <animateMotion dur="2s" repeatCount="indefinite" path="M333,21 L247,50" />
        </circle>
        <circle r="2.5" fill="#f59e0b">
          <animateMotion dur="2.3s" repeatCount="indefinite" path="M333,49 L247,55" />
        </circle>
        <circle r="2.5" fill="#3b82f6">
          <animateMotion dur="2.1s" repeatCount="indefinite" path="M333,77 L247,60" />
        </circle>
        <circle r="2.5" fill="#ec4899">
          <animateMotion dur="2.5s" repeatCount="indefinite" path="M333,105 L247,65" />
        </circle>
      </svg>
    </div>
  );
}

// ─── Map selling point IDs to their flow components ──────────────────────────

export const flowMap: Record<string, React.FC> = {
  'any-language': FlowAnyLanguage,
  'zero-deps': FlowZeroDeps,
  'tables-intact': FlowChunkingIntact,
  'coordination': FlowCoordination,
  'evaluation': FlowEvaluation,
  'grounded': FlowGroundedAnswers,
  'migration-scale': FlowMigration,
  'context-chunking': FlowContextChunking,
  'model-swap': FlowModelSwap,
  'one-tool': FlowOneTool,
};
