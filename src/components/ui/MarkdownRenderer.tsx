import React, { useState, useEffect, useRef } from 'react';
import katex from 'katex';
import './MarkdownRenderer.css';

// ─── Types ────────────────────────────────────────────────────────────────────

type Block =
  | { type: 'heading'; level: number; content: string }
  | { type: 'mathblock'; content: string }
  | { type: 'code'; lang: string; content: string }
  | { type: 'table'; rows: string[] }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] }
  | { type: 'paragraph'; content: string };

// ─── Inline KaTeX Math Rendering Components ────────────────────────────────────

const InlineMath: React.FC<{ formula: string }> = ({ formula }) => {
  const containerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      try {
        katex.render(formula, containerRef.current, {
          displayMode: false,
          throwOnError: false,
        });
      } catch (err) {
        console.error('KaTeX inline error:', err);
        containerRef.current.textContent = `$${formula}$`;
      }
    }
  }, [formula]);

  return <span ref={containerRef} className="inline-math" />;
};

const BlockMath: React.FC<{ formula: string }> = ({ formula }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      try {
        katex.render(formula, containerRef.current, {
          displayMode: true,
          throwOnError: false,
        });
      } catch (err) {
        console.error('KaTeX block error:', err);
        containerRef.current.textContent = `$$${formula}$$`;
      }
    }
  }, [formula]);

  return <div ref={containerRef} className="block-math" />;
};

// ─── Custom Code Block Rendering Component ─────────────────────────────────────

const CodeBlock: React.FC<{ lang: string; code: string }> = ({ lang, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderCodeContent = () => {
    const trimmedCode = code.replace(/^\n+|\n+$/g, '');
    
    if (lang === 'diff') {
      const lines = trimmedCode.split('\n');
      return (
        <pre className="code-pre diff-pre">
          <code>
            {lines.map((line, idx) => {
              let className = 'diff-line';
              if (line.startsWith('+') && !line.startsWith('+++')) {
                className += ' diff-add';
              } else if (line.startsWith('-') && !line.startsWith('---')) {
                className += ' diff-delete';
              }
              return (
                <div key={idx} className={className}>
                  {line}
                </div>
              );
            })}
          </code>
        </pre>
      );
    }

    if (lang === 'logs' || lang === 'bash' || lang === 'sh') {
      return (
        <pre className="code-pre console-pre">
          <code>{trimmedCode}</code>
        </pre>
      );
    }

    return (
      <pre className="code-pre standard-pre">
        <code>{trimmedCode}</code>
      </pre>
    );
  };

  return (
    <div className={`code-block-container ${lang || 'raw'}`}>
      <div className="code-block-header">
        <span className="code-block-lang">{lang || 'code'}</span>
        <button className="code-block-copy-btn" onClick={handleCopy}>
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div className="code-block-body">
        {renderCodeContent()}
      </div>
    </div>
  );
};

// ─── Inline Rendering Engine ───────────────────────────────────────────────────

const renderInline = (text: string): React.ReactNode => {
  const tokens: (string | React.ReactNode)[] = [text];

  // 1. Process Inline Math $...$
  let nextTokens: (string | React.ReactNode)[] = [];
  for (const token of tokens) {
    if (typeof token !== 'string') {
      nextTokens.push(token);
      continue;
    }
    const regex = /(?<!\\)\$(?!\$)(.*?)(?<!\\)\$/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(token)) !== null) {
      const matchIndex = match.index;
      const matchText = match[0];
      const innerText = match[1];

      if (matchIndex > lastIndex) {
        nextTokens.push(token.substring(lastIndex, matchIndex));
      }

      nextTokens.push(
        <InlineMath key={`math-${matchIndex}`} formula={innerText} />
      );
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < token.length) {
      nextTokens.push(token.substring(lastIndex));
    }
  }
  tokens.length = 0;
  tokens.push(...nextTokens);

  // 2. Process Inline Code `...`
  nextTokens = [];
  for (const token of tokens) {
    if (typeof token !== 'string') {
      nextTokens.push(token);
      continue;
    }
    const regex = /`([^`]+)`/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(token)) !== null) {
      const matchIndex = match.index;
      const innerText = match[1];

      if (matchIndex > lastIndex) {
        nextTokens.push(token.substring(lastIndex, matchIndex));
      }

      nextTokens.push(
        <code key={`code-${matchIndex}`} className="inline-code">
          {innerText}
        </code>
      );
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < token.length) {
      nextTokens.push(token.substring(lastIndex));
    }
  }
  tokens.length = 0;
  tokens.push(...nextTokens);

  // 3. Process Images ![alt](url)
  nextTokens = [];
  for (const token of tokens) {
    if (typeof token !== 'string') {
      nextTokens.push(token);
      continue;
    }
    const regex = /!\[([^\]]*)\]\(([^)]+)\)/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(token)) !== null) {
      const matchIndex = match.index;
      const altText = match[1];
      const imageUrl = match[2];

      if (matchIndex > lastIndex) {
        nextTokens.push(token.substring(lastIndex, matchIndex));
      }

      nextTokens.push(
        <span key={`img-${matchIndex}`} className="premium-image-card">
          <img src={imageUrl} alt={altText} className="premium-image" />
          {altText && <span className="premium-image-caption">{altText}</span>}
        </span>
      );
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < token.length) {
      nextTokens.push(token.substring(lastIndex));
    }
  }
  tokens.length = 0;
  tokens.push(...nextTokens);

  // 4. Process Links [text](url)
  nextTokens = [];
  for (const token of tokens) {
    if (typeof token !== 'string') {
      nextTokens.push(token);
      continue;
    }
    const regex = /\[([^\]]+)\]\(([^)]+)\)/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(token)) !== null) {
      const matchIndex = match.index;
      const linkText = match[1];
      const linkUrl = match[2];

      if (matchIndex > lastIndex) {
        nextTokens.push(token.substring(lastIndex, matchIndex));
      }

      nextTokens.push(
        <a key={`link-${matchIndex}`} href={linkUrl} target="_blank" rel="noopener noreferrer" className="markdown-link">
          {linkText}
        </a>
      );
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < token.length) {
      nextTokens.push(token.substring(lastIndex));
    }
  }
  tokens.length = 0;
  tokens.push(...nextTokens);

  // 5. Process Bold **text**
  nextTokens = [];
  for (const token of tokens) {
    if (typeof token !== 'string') {
      nextTokens.push(token);
      continue;
    }
    const regex = /\*\*([^*]+)\*\*/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(token)) !== null) {
      const matchIndex = match.index;
      const innerText = match[1];

      if (matchIndex > lastIndex) {
        nextTokens.push(token.substring(lastIndex, matchIndex));
      }

      nextTokens.push(
        <strong key={`bold-${matchIndex}`}>
          {innerText}
        </strong>
      );
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < token.length) {
      nextTokens.push(token.substring(lastIndex));
    }
  }
  tokens.length = 0;
  tokens.push(...nextTokens);

  // 6. Process Italic *text*
  nextTokens = [];
  for (const token of tokens) {
    if (typeof token !== 'string') {
      nextTokens.push(token);
      continue;
    }
    const regex = /\*([^*]+)\*/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(token)) !== null) {
      const matchIndex = match.index;
      const innerText = match[1];

      if (matchIndex > lastIndex) {
        nextTokens.push(token.substring(lastIndex, matchIndex));
      }

      nextTokens.push(
        <em key={`italic-${matchIndex}`}>
          {innerText}
        </em>
      );
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < token.length) {
      nextTokens.push(token.substring(lastIndex));
    }
  }
  tokens.length = 0;
  tokens.push(...nextTokens);

  return <>{tokens}</>;
};

// ─── Custom Table Component ───────────────────────────────────────────────────

const TableBlock: React.FC<{ rows: string[] }> = ({ rows }) => {
  const cleanRows = rows.map((r) => r.trim()).filter((r) => r !== '');
  if (cleanRows.length === 0) return null;

  const parseRowCells = (row: string) => {
    const parts = row.split('|');
    let cells = parts.slice(1, parts.length - 1);
    if (parts.length <= 2) {
      cells = parts;
    }
    return cells.map((c) => c.trim());
  };

  const headers = parseRowCells(cleanRows[0]);
  let dataRows = cleanRows.slice(1);
  if (dataRows.length > 0 && dataRows[0].includes('---')) {
    dataRows = dataRows.slice(1);
  }

  return (
    <div className="table-responsive-container">
      <table className="premium-markdown-table">
        <thead>
          <tr>
            {headers.map((h, idx) => (
              <th key={idx}>{renderInline(h)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataRows.map((row, rIdx) => {
            const cells = parseRowCells(row);
            return (
              <tr key={rIdx}>
                {cells.map((cell, cIdx) => (
                  <td key={cIdx}>{renderInline(cell)}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

// ─── Block-Level Parsing Loop ──────────────────────────────────────────────────

const parseBlocks = (text: string): Block[] => {
  const lines = text.split('\n');
  const blocks: Block[] = [];

  let currentCode: { lang: string; content: string[] } | null = null;
  let currentMath: { content: string[] } | null = null;
  let currentTable: { rows: string[] } | null = null;
  let currentList: { type: 'ul' | 'ol'; items: string[] } | null = null;
  let currentParagraph: string[] = [];

  const flushParagraph = () => {
    if (currentParagraph.length > 0) {
      blocks.push({ type: 'paragraph', content: currentParagraph.join('\n') });
      currentParagraph = [];
    }
  };

  const flushList = () => {
    if (currentList) {
      blocks.push({ type: currentList.type, items: currentList.items });
      currentList = null;
    }
  };

  const flushTable = () => {
    if (currentTable) {
      blocks.push({ type: 'table', rows: currentTable.rows });
      currentTable = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. Code block handling
    if (trimmed.startsWith('```')) {
      if (currentCode) {
        blocks.push({ type: 'code', lang: currentCode.lang, content: currentCode.content.join('\n') });
        currentCode = null;
      } else {
        flushParagraph();
        flushList();
        flushTable();
        const lang = trimmed.slice(3).trim();
        currentCode = { lang, content: [] };
      }
      continue;
    }

    if (currentCode) {
      currentCode.content.push(line);
      continue;
    }

    // 2. Math block handling
    if (trimmed.startsWith('$$')) {
      if (currentMath) {
        currentMath.content.push(line);
        blocks.push({ type: 'mathblock', content: currentMath.content.join('\n').replace(/\$\$/g, '') });
        currentMath = null;
      } else {
        if (trimmed.endsWith('$$') && trimmed.length > 2) {
          flushParagraph();
          flushList();
          flushTable();
          blocks.push({ type: 'mathblock', content: trimmed.slice(2, -2) });
        } else {
          flushParagraph();
          flushList();
          flushTable();
          currentMath = { content: [line] };
        }
      }
      continue;
    }

    if (currentMath) {
      currentMath.content.push(line);
      if (trimmed.endsWith('$$')) {
        blocks.push({ type: 'mathblock', content: currentMath.content.join('\n').replace(/\$\$/g, '') });
        currentMath = null;
      }
      continue;
    }

    // 3. Table handling
    if (trimmed.startsWith('|')) {
      flushParagraph();
      flushList();
      if (!currentTable) {
        currentTable = { rows: [] };
      }
      currentTable.rows.push(line);
      continue;
    } else {
      flushTable();
    }

    // 4. Headers handling
    if (trimmed.startsWith('#')) {
      const match = /^(\s*#+)\s+(.*)$/.exec(line);
      if (match) {
        flushParagraph();
        flushList();
        const level = match[1].trim().length;
        blocks.push({ type: 'heading', level: Math.min(level, 6), content: match[2] });
        continue;
      }
    }

    // 5. Lists handling
    const unorderedMatch = /^(\s*)[-*+]\s+(.*)$/.exec(line);
    const orderedMatch = /^(\s*)\d+\.\s+(.*)$/.exec(line);
    if (unorderedMatch) {
      flushParagraph();
      if (!currentList || currentList.type !== 'ul') {
        flushList();
        currentList = { type: 'ul', items: [] };
      }
      currentList.items.push(unorderedMatch[2]);
      continue;
    } else if (orderedMatch) {
      flushParagraph();
      if (!currentList || currentList.type !== 'ol') {
        flushList();
        currentList = { type: 'ol', items: [] };
      }
      currentList.items.push(orderedMatch[2]);
      continue;
    }

    // Empty line separates paragraphs/lists
    if (trimmed === '') {
      flushParagraph();
      flushList();
      continue;
    }

    // Regular paragraph line
    flushList();
    currentParagraph.push(line);
  }

  flushParagraph();
  flushList();
  flushTable();

  return blocks;
};

// ─── Main Renderer Component ───────────────────────────────────────────────────

export interface MarkdownRendererProps {
  content: string;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  if (!content) return null;

  const blocks = parseBlocks(content);

  return (
    <div className="premium-markdown-body">
      {blocks.map((block, idx) => {
        switch (block.type) {
          case 'heading': {
            const Tag = `h${block.level}` as keyof JSX.IntrinsicElements;
            return (
              <Tag key={idx} className={`markdown-h${block.level}`}>
                {renderInline(block.content)}
              </Tag>
            );
          }
          case 'mathblock':
            return <BlockMath key={idx} formula={block.content} />;
          case 'code':
            return <CodeBlock key={idx} lang={block.lang} code={block.content} />;
          case 'table':
            return <TableBlock key={idx} rows={block.rows} />;
          case 'ul':
            return (
              <ul key={idx} className="markdown-ul">
                {block.items.map((item, iIdx) => (
                  <li key={iIdx}>{renderInline(item)}</li>
                ))}
              </ul>
            );
          case 'ol':
            return (
              <ol key={idx} className="markdown-ol">
                {block.items.map((item, iIdx) => (
                  <li key={iIdx}>{renderInline(item)}</li>
                ))}
              </ol>
            );
          case 'paragraph':
          default:
            return (
              <p key={idx} className="markdown-p">
                {renderInline(block.content)}
              </p>
            );
        }
      })}
    </div>
  );
};

export default MarkdownRenderer;
