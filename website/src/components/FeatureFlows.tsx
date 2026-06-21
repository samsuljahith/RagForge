/**
 * Animated flow diagrams for the Feature Explorer panel.
 * Each feature gets a visual workflow showing how data moves through it.
 * Pure SVG animations — no external deps, works everywhere.
 */

import React from 'react';

const flowStyle: React.CSSProperties = {
  width: '100%',
  height: '130px',
  marginTop: '0.75rem',
  borderRadius: '10px',
  background: 'var(--rf-bg-subtle)',
  border: '1px solid var(--rf-border-light)',
  overflow: 'hidden',
};

export function FlowParsing() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="130" viewBox="0 0 420 130">
        {/* Source files */}
        <rect x="10" y="20" width="50" height="25" rx="4" fill="#fee2e2" stroke="#f87171" strokeWidth="1"><animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/></rect>
        <text x="35" y="36" textAnchor="middle" fontSize="7" fill="#991b1b">.pdf</text>
        <rect x="10" y="52" width="50" height="25" rx="4" fill="#dbeafe" stroke="#60a5fa" strokeWidth="1"><animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite"/></rect>
        <text x="35" y="68" textAnchor="middle" fontSize="7" fill="#1e40af">.html</text>
        <rect x="10" y="84" width="50" height="25" rx="4" fill="#dcfce7" stroke="#4ade80" strokeWidth="1"><animate attributeName="opacity" values="1;0.7;1" dur="2.5s" repeatCount="indefinite"/></rect>
        <text x="35" y="100" textAnchor="middle" fontSize="7" fill="#166534">.md</text>

        {/* Auto-detect */}
        <rect x="110" y="40" width="80" height="50" rx="8" fill="#fdf4ff" stroke="#a855f7" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/>
        </rect>
        <text x="150" y="60" textAnchor="middle" fontSize="8" fontWeight="700" fill="#7e22ce">Auto-detect</text>
        <text x="150" y="73" textAnchor="middle" fontSize="6" fill="#a855f7">format by ext</text>
        <text x="150" y="84" textAnchor="middle" fontSize="6" fill="#c084fc">or use Docling</text>

        {/* Clean document */}
        <rect x="250" y="35" width="90" height="60" rx="8" fill="#f0fdf4" stroke="#22c55e" strokeWidth="2"/>
        <text x="295" y="55" textAnchor="middle" fontSize="9" fontWeight="700" fill="#166534">Document</text>
        <text x="295" y="68" textAnchor="middle" fontSize="6" fill="#22c55e">clean text</text>
        <text x="295" y="80" textAnchor="middle" fontSize="6" fill="#22c55e">+ metadata</text>
        <text x="295" y="92" textAnchor="middle" fontSize="6" fill="#86efac">~tokens estimated</text>

        {/* Packets */}
        <circle r="4" fill="#f87171"><animateMotion dur="1.5s" repeatCount="indefinite" path="M62,32 L108,55"/></circle>
        <circle r="4" fill="#60a5fa"><animateMotion dur="1.8s" repeatCount="indefinite" path="M62,64 L108,62"/></circle>
        <circle r="4" fill="#4ade80"><animateMotion dur="2s" repeatCount="indefinite" path="M62,96 L108,72"/></circle>
        <circle r="4" fill="#a855f7"><animateMotion dur="1.5s" repeatCount="indefinite" path="M192,65 L248,65"/></circle>

        <text x="360" y="65" fontSize="7" fill="#64748b">→ ready for</text>
        <text x="360" y="77" fontSize="7" fill="#64748b">chunking</text>
      </svg>
    </div>
  );
}

export function FlowChunking() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="130" viewBox="0 0 420 130">
        {/* Document */}
        <rect x="10" y="15" width="60" height="100" rx="4" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5"/>
        <rect x="16" y="22" width="48" height="6" rx="2" fill="#ede9fe"/><text x="40" y="27" textAnchor="middle" fontSize="4" fill="#5b21b6"># Header</text>
        <rect x="16" y="32" width="48" height="12" rx="2" fill="#f8fafc"/>
        <rect x="16" y="48" width="48" height="6" rx="2" fill="#ede9fe"/><text x="40" y="53" textAnchor="middle" fontSize="4" fill="#5b21b6">## Section</text>
        <rect x="16" y="58" width="48" height="20" rx="2" fill="#dbeafe"/><text x="40" y="70" textAnchor="middle" fontSize="5" fill="#1e40af">TABLE</text>
        <rect x="16" y="82" width="48" height="18" rx="2" fill="#dcfce7"/><text x="40" y="93" textAnchor="middle" fontSize="5" fill="#166534">CODE</text>
        <text x="40" y="115" textAnchor="middle" fontSize="6" fill="#94a3b8">analyze first</text>

        {/* Arrow */}
        <circle r="4" fill="#10b981"><animateMotion dur="1.5s" repeatCount="indefinite" path="M72,65 L120,65"/></circle>

        {/* Chunker */}
        <rect x="125" y="35" width="75" height="60" rx="8" fill="#ecfdf5" stroke="#10b981" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/>
        </rect>
        <text x="162" y="57" textAnchor="middle" fontSize="8" fontWeight="700" fill="#065f46">Structure</text>
        <text x="162" y="70" textAnchor="middle" fontSize="6" fill="#10b981">Chunker</text>
        <text x="162" y="82" textAnchor="middle" fontSize="5" fill="#6ee7b7">context-aware</text>

        {/* Output chunks */}
        <rect x="240" y="12" width="80" height="28" rx="5" fill="#f0fdf4" stroke="#22c55e" strokeWidth="1.5">
          <animate attributeName="opacity" values="1;0.6;1" dur="2.5s" repeatCount="indefinite"/>
        </rect>
        <text x="280" y="25" textAnchor="middle" fontSize="6" fontWeight="600" fill="#166534">Chunk 1 [Header]</text>
        <text x="280" y="35" textAnchor="middle" fontSize="5" fill="#22c55e">paragraph text</text>

        <rect x="240" y="46" width="80" height="28" rx="5" fill="#f0fdf4" stroke="#22c55e" strokeWidth="1.5">
          <animate attributeName="opacity" values="0.6;1;0.6" dur="2.5s" repeatCount="indefinite"/>
        </rect>
        <text x="280" y="59" textAnchor="middle" fontSize="6" fontWeight="600" fill="#166534">Chunk 2 [Section]</text>
        <text x="280" y="69" textAnchor="middle" fontSize="5" fill="#22c55e">TABLE ✓ intact</text>

        <rect x="240" y="80" width="80" height="28" rx="5" fill="#f0fdf4" stroke="#22c55e" strokeWidth="1.5">
          <animate attributeName="opacity" values="0.8;1;0.8" dur="2s" repeatCount="indefinite"/>
        </rect>
        <text x="280" y="93" textAnchor="middle" fontSize="6" fontWeight="600" fill="#166534">Chunk 3 [Section]</text>
        <text x="280" y="103" textAnchor="middle" fontSize="5" fill="#22c55e">CODE ✓ intact</text>

        <circle r="3" fill="#22c55e"><animateMotion dur="1.5s" repeatCount="indefinite" path="M202,65 L238,30"/></circle>
        <circle r="3" fill="#22c55e"><animateMotion dur="1.8s" repeatCount="indefinite" path="M202,65 L238,60"/></circle>
        <circle r="3" fill="#22c55e"><animateMotion dur="2s" repeatCount="indefinite" path="M202,65 L238,94"/></circle>

        <text x="350" y="60" fontSize="7" fontWeight="600" fill="#10b981">Each chunk</text>
        <text x="350" y="72" fontSize="7" fontWeight="600" fill="#10b981">tagged with</text>
        <text x="350" y="84" fontSize="7" fontWeight="600" fill="#10b981">its section</text>
      </svg>
    </div>
  );
}

export function FlowRetrieval() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="130" viewBox="0 0 420 130">
        {/* Query */}
        <rect x="10" y="45" width="55" height="35" rx="6" fill="#ede9fe" stroke="#7c3aed" strokeWidth="1.5"/>
        <text x="37" y="62" textAnchor="middle" fontSize="7" fontWeight="600" fill="#5b21b6">Query</text>
        <text x="37" y="73" textAnchor="middle" fontSize="5" fill="#7c3aed">"refunds?"</text>

        {/* Dense search */}
        <rect x="95" y="15" width="65" height="35" rx="6" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1.5">
          <animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/>
        </rect>
        <text x="127" y="32" textAnchor="middle" fontSize="7" fontWeight="600" fill="#1e40af">Dense</text>
        <text x="127" y="43" textAnchor="middle" fontSize="5" fill="#3b82f6">vectors</text>

        {/* BM25 */}
        <rect x="95" y="60" width="65" height="35" rx="6" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1.5">
          <animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite"/>
        </rect>
        <text x="127" y="77" textAnchor="middle" fontSize="7" fontWeight="600" fill="#92400e">BM25</text>
        <text x="127" y="88" textAnchor="middle" fontSize="5" fill="#f59e0b">keywords</text>

        {/* RRF fusion */}
        <rect x="195" y="35" width="60" height="40" rx="8" fill="#fdf4ff" stroke="#a855f7" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="1;0.4;1" dur="1.5s" repeatCount="indefinite"/>
        </rect>
        <text x="225" y="53" textAnchor="middle" fontSize="7" fontWeight="700" fill="#7e22ce">RRF</text>
        <text x="225" y="65" textAnchor="middle" fontSize="5" fill="#a855f7">fusion</text>

        {/* Reranker */}
        <rect x="285" y="35" width="55" height="40" rx="6" fill="#ecfdf5" stroke="#10b981" strokeWidth="1.5"/>
        <text x="312" y="53" textAnchor="middle" fontSize="7" fontWeight="600" fill="#065f46">Rerank</text>
        <text x="312" y="65" textAnchor="middle" fontSize="5" fill="#10b981">precision</text>

        {/* Top-K results */}
        <rect x="365" y="30" width="45" height="50" rx="6" fill="#f0fdf4" stroke="#22c55e" strokeWidth="2"/>
        <text x="387" y="50" textAnchor="middle" fontSize="7" fontWeight="700" fill="#166534">Top-K</text>
        <text x="387" y="62" textAnchor="middle" fontSize="5" fill="#22c55e">results</text>
        <text x="387" y="74" textAnchor="middle" fontSize="5" fill="#86efac">scored</text>

        {/* Flowing packets */}
        <circle r="3" fill="#7c3aed"><animateMotion dur="1.2s" repeatCount="indefinite" path="M67,55 L93,32"/></circle>
        <circle r="3" fill="#7c3aed"><animateMotion dur="1.4s" repeatCount="indefinite" path="M67,65 L93,77"/></circle>
        <circle r="3" fill="#3b82f6"><animateMotion dur="1.5s" repeatCount="indefinite" path="M162,32 L193,50"/></circle>
        <circle r="3" fill="#f59e0b"><animateMotion dur="1.5s" repeatCount="indefinite" path="M162,77 L193,60"/></circle>
        <circle r="3" fill="#a855f7"><animateMotion dur="1.3s" repeatCount="indefinite" path="M257,55 L283,55"/></circle>
        <circle r="3" fill="#10b981"><animateMotion dur="1.2s" repeatCount="indefinite" path="M342,55 L363,55"/></circle>

        <text x="210" y="105" textAnchor="middle" fontSize="6" fill="#64748b">Hybrid: semantic + keyword = best of both</text>
        <text x="210" y="118" textAnchor="middle" fontSize="6" fontWeight="600" fill="#5b4ff5">Dense catches meaning, BM25 catches exact terms</text>
      </svg>
    </div>
  );
}

export function FlowGeneration() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="130" viewBox="0 0 420 130">
        <rect x="10" y="40" width="55" height="40" rx="6" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1.5"/>
        <text x="37" y="58" textAnchor="middle" fontSize="7" fontWeight="600" fill="#1e40af">Chunks</text>
        <text x="37" y="70" textAnchor="middle" fontSize="5" fill="#3b82f6">[0.94] [0.81]</text>

        <rect x="100" y="30" width="80" height="55" rx="8" fill="#fdf4ff" stroke="#8b5cf6" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="1;0.4;1" dur="1.8s" repeatCount="indefinite"/>
        </rect>
        <text x="140" y="50" textAnchor="middle" fontSize="8" fontWeight="700" fill="#5b21b6">LLM</text>
        <text x="140" y="62" textAnchor="middle" fontSize="6" fill="#7c3aed">grounded</text>
        <text x="140" y="73" textAnchor="middle" fontSize="5" fill="#a855f7">prompt</text>

        <rect x="220" y="25" width="100" height="65" rx="8" fill="#f0fdf4" stroke="#22c55e" strokeWidth="2"/>
        <text x="270" y="43" textAnchor="middle" fontSize="8" fontWeight="700" fill="#166534">Answer</text>
        <text x="270" y="56" textAnchor="middle" fontSize="6" fill="#22c55e">+ source [1] [2]</text>
        <text x="270" y="68" textAnchor="middle" fontSize="5" fill="#86efac">cited & grounded</text>
        <text x="270" y="82" textAnchor="middle" fontSize="5" fill="#22c55e">or refuses if</text>
        <text x="270" y="92" textAnchor="middle" fontSize="5" fill="#22c55e">insufficient ✓</text>

        <rect x="350" y="40" width="60" height="40" rx="6" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1"/>
        <text x="380" y="57" textAnchor="middle" fontSize="6" fontWeight="600" fill="#92400e">Provider</text>
        <text x="380" y="69" textAnchor="middle" fontSize="5" fill="#f59e0b">OpenAI</text>
        <text x="380" y="79" textAnchor="middle" fontSize="5" fill="#f59e0b">Anthropic</text>

        <circle r="3" fill="#3b82f6"><animateMotion dur="1.5s" repeatCount="indefinite" path="M67,60 L98,57"/></circle>
        <circle r="3" fill="#8b5cf6"><animateMotion dur="1.5s" repeatCount="indefinite" path="M182,57 L218,57"/></circle>

        <text x="210" y="118" textAnchor="middle" fontSize="6" fill="#64748b">No hallucination — answers only from retrieved evidence</text>
      </svg>
    </div>
  );
}

export function FlowEval() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="130" viewBox="0 0 420 130">
        <rect x="10" y="35" width="60" height="50" rx="6" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5"/>
        <text x="40" y="55" textAnchor="middle" fontSize="7" fontWeight="600" fill="#475569">Golden</text>
        <text x="40" y="67" textAnchor="middle" fontSize="6" fill="#94a3b8">20 Q&amp;A</text>

        <rect x="105" y="30" width="70" height="55" rx="8" fill="#ecfdf5" stroke="#06b6d4" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/>
        </rect>
        <text x="140" y="52" textAnchor="middle" fontSize="8" fontWeight="700" fill="#0e7490">Evaluate</text>
        <text x="140" y="65" textAnchor="middle" fontSize="6" fill="#06b6d4">retrieve + judge</text>
        <text x="140" y="77" textAnchor="middle" fontSize="5" fill="#67e8f9">per question</text>

        {/* Metric bars */}
        <text x="210" y="28" fontSize="6" fill="#475569">hit_rate</text>
        <rect x="250" y="22" width="70" height="7" rx="3" fill="#f1f5f9"/>
        <rect x="250" y="22" width="0" height="7" rx="3" fill="#10b981"><animate attributeName="width" from="0" to="60" dur="2s" repeatCount="indefinite"/></rect>
        <text x="325" y="28" fontSize="6" fontWeight="700" fill="#10b981">85%</text>

        <text x="210" y="44" fontSize="6" fill="#475569">MRR</text>
        <rect x="250" y="38" width="70" height="7" rx="3" fill="#f1f5f9"/>
        <rect x="250" y="38" width="0" height="7" rx="3" fill="#6366f1"><animate attributeName="width" from="0" to="51" dur="2s" repeatCount="indefinite"/></rect>
        <text x="325" y="44" fontSize="6" fontWeight="700" fill="#6366f1">73%</text>

        <text x="210" y="60" fontSize="6" fill="#475569">precision@5</text>
        <rect x="250" y="54" width="70" height="7" rx="3" fill="#f1f5f9"/>
        <rect x="250" y="54" width="0" height="7" rx="3" fill="#f97316"><animate attributeName="width" from="0" to="43" dur="2s" repeatCount="indefinite"/></rect>
        <text x="325" y="60" fontSize="6" fontWeight="700" fill="#f97316">62%</text>

        <text x="210" y="76" fontSize="6" fill="#475569">faithfulness</text>
        <rect x="250" y="70" width="70" height="7" rx="3" fill="#f1f5f9"/>
        <rect x="250" y="70" width="0" height="7" rx="3" fill="#8b5cf6"><animate attributeName="width" from="0" to="64" dur="2s" repeatCount="indefinite"/></rect>
        <text x="325" y="76" fontSize="6" fontWeight="700" fill="#8b5cf6">92%</text>

        <circle r="3" fill="#06b6d4"><animateMotion dur="1.5s" repeatCount="indefinite" path="M72,60 L103,57"/></circle>
        <circle r="3" fill="#10b981"><animateMotion dur="1.8s" repeatCount="indefinite" path="M177,55 L208,40"/></circle>

        <text x="270" y="100" textAnchor="middle" fontSize="6" fill="#64748b">A/B compare configs → know which is better</text>
        <text x="270" y="115" textAnchor="middle" fontSize="7" fontWeight="600" fill="#06b6d4">Prove it, don't guess</text>
      </svg>
    </div>
  );
}

export function FlowQuantization() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="130" viewBox="0 0 420 130">
        <rect x="10" y="30" width="70" height="55" rx="6" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1.5"/>
        <text x="45" y="50" textAnchor="middle" fontSize="7" fontWeight="600" fill="#92400e">float32</text>
        <text x="45" y="63" textAnchor="middle" fontSize="6" fill="#f59e0b">512 bytes/vec</text>
        <text x="45" y="76" textAnchor="middle" fontSize="6" fill="#d97706">quality: 1.00</text>

        <rect x="120" y="35" width="65" height="45" rx="8" fill="#fdf4ff" stroke="#a855f7" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="1;0.4;1" dur="1.5s" repeatCount="indefinite"/>
        </rect>
        <text x="152" y="55" textAnchor="middle" fontSize="7" fontWeight="700" fill="#7e22ce">Quantize</text>
        <text x="152" y="68" textAnchor="middle" fontSize="5" fill="#a855f7">compress</text>

        <rect x="225" y="30" width="70" height="55" rx="6" fill="#dcfce7" stroke="#22c55e" strokeWidth="1.5"/>
        <text x="260" y="50" textAnchor="middle" fontSize="7" fontWeight="600" fill="#166534">int8</text>
        <text x="260" y="63" textAnchor="middle" fontSize="6" fill="#22c55e">128 bytes/vec</text>
        <text x="260" y="76" textAnchor="middle" fontSize="6" fill="#16a34a">quality: 0.98</text>

        <rect x="330" y="30" width="80" height="55" rx="6" fill="#f0fdf4" stroke="#22c55e" strokeWidth="2"/>
        <text x="370" y="48" textAnchor="middle" fontSize="7" fontWeight="700" fill="#166534">Result</text>
        <text x="370" y="61" textAnchor="middle" fontSize="6" fill="#22c55e">4x smaller</text>
        <text x="370" y="74" textAnchor="middle" fontSize="6" fill="#22c55e">-2% quality</text>
        <text x="370" y="87" textAnchor="middle" fontSize="6" fontWeight="600" fill="#16a34a">75% cheaper</text>

        <circle r="3" fill="#f59e0b"><animateMotion dur="1.5s" repeatCount="indefinite" path="M82,57 L118,57"/></circle>
        <circle r="3" fill="#a855f7"><animateMotion dur="1.5s" repeatCount="indefinite" path="M187,57 L223,57"/></circle>
        <circle r="3" fill="#22c55e"><animateMotion dur="1.3s" repeatCount="indefinite" path="M297,57 L328,57"/></circle>

        <text x="210" y="115" textAnchor="middle" fontSize="6" fill="#64748b">Measure tradeoff on YOUR data before committing</text>
      </svg>
    </div>
  );
}

export function FlowCoord() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="130" viewBox="0 0 420 130">
        <rect x="160" y="20" width="100" height="75" rx="10" fill="#fdf4ff" stroke="#ec4899" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="1;0.5;1" dur="2.5s" repeatCount="indefinite"/>
        </rect>
        <text x="210" y="42" textAnchor="middle" fontSize="9" fontWeight="700" fill="#be185d">Blackboard</text>
        <text x="210" y="56" textAnchor="middle" fontSize="6" fill="#ec4899">shared state</text>
        <text x="210" y="70" textAnchor="middle" fontSize="5" fill="#f9a8d4">findings | review</text>
        <text x="210" y="82" textAnchor="middle" fontSize="5" fill="#f9a8d4">answer | markers</text>

        <rect x="20" y="15" width="65" height="28" rx="6" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1.5"><animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/></rect>
        <text x="52" y="33" textAnchor="middle" fontSize="7" fontWeight="600" fill="#1e40af">Researcher</text>

        <rect x="20" y="55" width="65" height="28" rx="6" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1.5"><animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite"/></rect>
        <text x="52" y="73" textAnchor="middle" fontSize="7" fontWeight="600" fill="#92400e">Critic</text>

        <rect x="20" y="95" width="65" height="28" rx="6" fill="#dcfce7" stroke="#22c55e" strokeWidth="1.5"><animate attributeName="opacity" values="0.8;1;0.8" dur="2.5s" repeatCount="indefinite"/></rect>
        <text x="52" y="113" textAnchor="middle" fontSize="7" fontWeight="600" fill="#166534">Writer</text>

        <rect x="310" y="35" width="95" height="50" rx="8" fill="#f0fdf4" stroke="#22c55e" strokeWidth="2"/>
        <text x="357" y="55" textAnchor="middle" fontSize="7" fontWeight="700" fill="#166534">10-70% less</text>
        <text x="357" y="68" textAnchor="middle" fontSize="6" fill="#22c55e">tokens vs direct</text>
        <text x="357" y="80" textAnchor="middle" fontSize="5" fill="#86efac">messaging</text>

        <circle r="3" fill="#3b82f6"><animateMotion dur="2s" repeatCount="indefinite" path="M87,29 L158,40"/></circle>
        <circle r="3" fill="#f59e0b"><animateMotion dur="2.2s" repeatCount="indefinite" path="M87,69 L158,57"/></circle>
        <circle r="3" fill="#22c55e"><animateMotion dur="2.5s" repeatCount="indefinite" path="M87,109 L158,75"/></circle>
        <circle r="3" fill="#ec4899"><animateMotion dur="1.8s" repeatCount="indefinite" path="M262,55 L308,55"/></circle>

        <text x="210" y="115" textAnchor="middle" fontSize="6" fill="#64748b">Agents never call each other — only read/write board</text>
      </svg>
    </div>
  );
}

export function FlowTracing() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="130" viewBox="0 0 420 130">
        <rect x="10" y="40" width="50" height="35" rx="6" fill="#ede9fe" stroke="#7c3aed" strokeWidth="1.5"/>
        <text x="35" y="58" textAnchor="middle" fontSize="7" fontWeight="600" fill="#5b21b6">Query</text>

        {/* Pipeline steps traced */}
        <rect x="85" y="15" width="55" height="24" rx="4" fill="#dbeafe" stroke="#93c5fd" strokeWidth="1">
          <animate attributeName="opacity" values="0.5;1;0.5" dur="3s" begin="0s" repeatCount="indefinite"/>
        </rect>
        <text x="112" y="30" textAnchor="middle" fontSize="6" fill="#1e40af">retrieve 12ms</text>

        <rect x="85" y="45" width="55" height="24" rx="4" fill="#dcfce7" stroke="#86efac" strokeWidth="1">
          <animate attributeName="opacity" values="0.5;1;0.5" dur="3s" begin="0.5s" repeatCount="indefinite"/>
        </rect>
        <text x="112" y="60" textAnchor="middle" fontSize="6" fill="#166534">rerank 8ms</text>

        <rect x="85" y="75" width="55" height="24" rx="4" fill="#fdf4ff" stroke="#d8b4fe" strokeWidth="1">
          <animate attributeName="opacity" values="0.5;1;0.5" dur="3s" begin="1s" repeatCount="indefinite"/>
        </rect>
        <text x="112" y="90" textAnchor="middle" fontSize="6" fill="#7e22ce">generate 340ms</text>

        {/* Trace store */}
        <rect x="170" y="30" width="70" height="55" rx="8" fill="#f8fafc" stroke="#14b8a6" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/>
        </rect>
        <text x="205" y="50" textAnchor="middle" fontSize="7" fontWeight="700" fill="#0f766e">SQLite</text>
        <text x="205" y="63" textAnchor="middle" fontSize="6" fill="#14b8a6">trace store</text>
        <text x="205" y="75" textAnchor="middle" fontSize="5" fill="#5eead4">every step</text>

        {/* Dashboard */}
        <rect x="275" y="20" width="130" height="85" rx="8" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5"/>
        <text x="340" y="38" textAnchor="middle" fontSize="7" fontWeight="700" fill="#0f766e">Dashboard</text>
        <rect x="285" y="44" width="110" height="8" rx="3" fill="#f1f5f9"/><rect x="285" y="44" width="0" height="8" rx="3" fill="#14b8a6"><animate attributeName="width" from="0" to="80" dur="2s" repeatCount="indefinite"/></rect>
        <rect x="285" y="57" width="110" height="8" rx="3" fill="#f1f5f9"/><rect x="285" y="57" width="0" height="8" rx="3" fill="#06b6d4"><animate attributeName="width" from="0" to="60" dur="2s" begin="0.3s" repeatCount="indefinite"/></rect>
        <rect x="285" y="70" width="110" height="8" rx="3" fill="#f1f5f9"/><rect x="285" y="70" width="0" height="8" rx="3" fill="#8b5cf6"><animate attributeName="width" from="0" to="100" dur="2s" begin="0.6s" repeatCount="indefinite"/></rect>
        <text x="340" y="94" textAnchor="middle" fontSize="6" fill="#14b8a6">ragforge ui → browser</text>

        <circle r="3" fill="#7c3aed"><animateMotion dur="1.5s" repeatCount="indefinite" path="M62,57 L83,30"/></circle>
        <circle r="3" fill="#14b8a6"><animateMotion dur="1.5s" repeatCount="indefinite" path="M142,55 L168,55"/></circle>
        <circle r="3" fill="#06b6d4"><animateMotion dur="1.8s" repeatCount="indefinite" path="M242,57 L273,57"/></circle>
      </svg>
    </div>
  );
}

export function FlowMigrate() {
  return (
    <div style={flowStyle}>
      <svg width="100%" height="130" viewBox="0 0 420 130">
        <rect x="10" y="35" width="60" height="50" rx="6" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1.5"/>
        <text x="40" y="55" textAnchor="middle" fontSize="7" fontWeight="600" fill="#92400e">Model A</text>
        <text x="40" y="68" textAnchor="middle" fontSize="5" fill="#f59e0b">1M chunks</text>
        <text x="40" y="79" textAnchor="middle" fontSize="5" fill="#d97706">LIVE</text>

        <rect x="100" y="25" width="70" height="40" rx="6" fill="#ede9fe" stroke="#7c3aed" strokeWidth="1.5">
          <animate attributeName="stroke-opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/>
        </rect>
        <text x="135" y="43" textAnchor="middle" fontSize="7" fontWeight="600" fill="#5b21b6">Shadow</text>
        <text x="135" y="56" textAnchor="middle" fontSize="5" fill="#7c3aed">re-embed</text>

        <rect x="100" y="72" width="70" height="35" rx="6" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1.5"/>
        <text x="135" y="88" textAnchor="middle" fontSize="7" fontWeight="600" fill="#1e40af">Validate</text>
        <text x="135" y="100" textAnchor="middle" fontSize="5" fill="#3b82f6">quality ≥ 0.95?</text>

        <rect x="205" y="40" width="55" height="40" rx="8" fill="#dcfce7" stroke="#22c55e" strokeWidth="2">
          <animate attributeName="stroke-opacity" values="0.5;1;0.5" dur="1.5s" repeatCount="indefinite"/>
        </rect>
        <text x="232" y="58" textAnchor="middle" fontSize="7" fontWeight="700" fill="#166534">Swap</text>
        <text x="232" y="70" textAnchor="middle" fontSize="5" fill="#22c55e">atomic</text>

        <rect x="295" y="35" width="60" height="50" rx="6" fill="#f0fdf4" stroke="#22c55e" strokeWidth="2"/>
        <text x="325" y="55" textAnchor="middle" fontSize="7" fontWeight="600" fill="#166534">Model B</text>
        <text x="325" y="68" textAnchor="middle" fontSize="5" fill="#22c55e">1M chunks</text>
        <text x="325" y="79" textAnchor="middle" fontSize="5" fill="#16a34a">LIVE ✓</text>

        <rect x="370" y="45" width="40" height="30" rx="4" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="1"/>
        <text x="390" y="60" textAnchor="middle" fontSize="5" fill="#94a3b8">backup</text>
        <text x="390" y="70" textAnchor="middle" fontSize="5" fill="#94a3b8">kept</text>

        <circle r="3" fill="#f59e0b"><animateMotion dur="1.8s" repeatCount="indefinite" path="M72,55 L98,42"/></circle>
        <circle r="3" fill="#3b82f6"><animateMotion dur="2s" repeatCount="indefinite" path="M172,90 L203,65"/></circle>
        <circle r="3" fill="#22c55e"><animateMotion dur="1.5s" repeatCount="indefinite" path="M262,60 L293,60"/></circle>

        <text x="210" y="122" textAnchor="middle" fontSize="6" fill="#64748b">Production stays live. Auto-abort if quality drops.</text>
      </svg>
    </div>
  );
}

// ─── Map feature IDs to flow components ───────────────────────────────────────

export const featureFlowMap: Record<string, React.FC> = {
  'parsing': FlowParsing,
  'chunking': FlowChunking,
  'retrieval': FlowRetrieval,
  'generation': FlowGeneration,
  'evaluation': FlowEval,
  'quantization': FlowQuantization,
  'coordination': FlowCoord,
  'tracing': FlowTracing,
  'migration': FlowMigrate,
};
