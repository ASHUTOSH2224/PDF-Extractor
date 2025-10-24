'use client'

import React from 'react';
import 'katex/dist/katex.min.css';
import { InlineMath, BlockMath } from 'react-katex';

interface LatexRendererProps {
  content: string;
}

export function LatexRenderer({ content }: LatexRendererProps) {
  // Split content into blocks and inline math
  const renderLatexContent = (text: string) => {
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    
    // Match block math ($$...$$)
    const blockMathRegex = /\$\$([\s\S]*?)\$\$/g;
    let blockMatch;
    
    while ((blockMatch = blockMathRegex.exec(text)) !== null) {
      // Add text before the block math
      if (blockMatch.index > lastIndex) {
        const beforeText = text.slice(lastIndex, blockMatch.index);
        parts.push(renderInlineMath(beforeText));
      }
      
      // Add the block math
      try {
        parts.push(
          <div key={`block-${blockMatch.index}`} className="my-4">
            <BlockMath math={blockMatch[1].trim()} />
          </div>
        );
      } catch (error) {
        parts.push(
          <div key={`block-error-${blockMatch.index}`} className="my-4 p-3 bg-red-50 border border-red-200 rounded text-red-700">
            <strong>LaTeX Error:</strong> {error instanceof Error ? error.message : 'Invalid LaTeX syntax'}
            <pre className="mt-2 text-sm">{blockMatch[0]}</pre>
          </div>
        );
      }
      
      lastIndex = blockMatch.index + blockMatch[0].length;
    }
    
    // Add remaining text
    if (lastIndex < text.length) {
      const remainingText = text.slice(lastIndex);
      parts.push(renderInlineMath(remainingText));
    }
    
    return parts;
  };
  
  const renderInlineMath = (text: string) => {
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    
    // Match inline math ($...$)
    const inlineMathRegex = /\$([^$]+?)\$/g;
    let inlineMatch;
    
    while ((inlineMatch = inlineMathRegex.exec(text)) !== null) {
      // Add text before the inline math
      if (inlineMatch.index > lastIndex) {
        const beforeText = text.slice(lastIndex, inlineMatch.index);
        parts.push(
          <span key={`text-${lastIndex}`} className="text-gray-800 dark:text-gray-200">
            {beforeText}
          </span>
        );
      }
      
      // Add the inline math
      try {
        parts.push(
          <InlineMath 
            key={`inline-${inlineMatch.index}`}
            math={inlineMatch[1].trim()} 
          />
        );
      } catch (error) {
        parts.push(
          <span 
            key={`inline-error-${inlineMatch.index}`}
            className="bg-red-100 text-red-700 px-1 rounded text-sm"
            title={`LaTeX Error: ${error instanceof Error ? error.message : 'Invalid LaTeX syntax'}`}
          >
            {inlineMatch[0]}
          </span>
        );
      }
      
      lastIndex = inlineMatch.index + inlineMatch[0].length;
    }
    
    // Add remaining text
    if (lastIndex < text.length) {
      const remainingText = text.slice(lastIndex);
      parts.push(
        <span key={`text-${lastIndex}`} className="text-gray-800 dark:text-gray-200">
          {remainingText}
        </span>
      );
    }
    
    return parts.length > 0 ? parts : (
      <span className="text-gray-800 dark:text-gray-200">{text}</span>
    );
  };

  return (
    <div className="latex-content prose prose-sm max-w-none dark:prose-invert">
      {renderLatexContent(content)}
    </div>
  );
}
