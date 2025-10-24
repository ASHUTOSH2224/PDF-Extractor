/**
 * Format content for display, extracting text from various structures
 */
export function formatContentForDisplay(content: Record<string, any>): string {
  if (!content || Object.keys(content).length === 0) {
    return "No content available for this page.";
  }

  let textContent = "";
  
  // Check for common text fields
  if (content.text) {
    textContent = content.text;
  } else if (content.content) {
    textContent = content.content;
  } else if (content.extracted_text) {
    textContent = content.extracted_text;
  } else if (content.raw_text) {
    textContent = content.raw_text;
  } else if (Array.isArray(content)) {
    // If content is an array, join all text elements
    textContent = content
      .map(item => typeof item === 'string' ? item : item.text || item.content || '')
      .filter(text => text.trim())
      .join('\n\n');
  } else {
    // If content is an object, try to extract all text values
    const textValues = Object.values(content)
      .filter(value => typeof value === 'string' && value.trim())
      .join('\n\n');
    textContent = textValues || JSON.stringify(content, null, 2);
  }

  return textContent || "No readable text content found.";
}

export interface ContentInfo {
  parsed: any;
  hasCombined: boolean;
  hasText: boolean;
  hasTable: boolean;
  hasMarkdown: boolean;
  hasLatex: boolean;
  isStructured: boolean;
}

/**
 * Determine available content sections and structure
 */
export function getContentInfo(content: any): ContentInfo {
  try {
    const parsed = typeof content === 'string' ? JSON.parse(content) : content;
    if (parsed && typeof parsed === 'object') {
      const combined = parsed.COMBINED && String(parsed.COMBINED).trim() !== '';
      const text = parsed.TEXT && String(parsed.TEXT).trim() !== '';
      const table = parsed.TABLE && String(parsed.TABLE).trim() !== '';
      const markdown = parsed.MARKDOWN && String(parsed.MARKDOWN).trim() !== '';
      const latex = parsed.LATEX && String(parsed.LATEX).trim() !== '';
      return { 
        parsed, 
        hasCombined: combined, 
        hasText: text, 
        hasTable: table, 
        hasMarkdown: markdown,
        hasLatex: latex,
        isStructured: true 
      };
    }
  } catch {
    // fallthrough to plain text
  }
  return { 
    parsed: content, 
    hasCombined: false, 
    hasText: true, 
    hasTable: false, 
    hasMarkdown: false,
    hasLatex: false,
    isStructured: false 
  };
}

/**
 * Get content for a specific view mode
 */
export function getContentForViewMode(
  content: any,
  viewMode: 'combined' | 'text' | 'table' | 'markdown' | 'latex'
): string {
  const info = getContentInfo(content);
  
  if (!info.isStructured) {
    return formatContentForDisplay(info.parsed);
  }

  const contentMap: Record<typeof viewMode, string | undefined> = {
    combined: info.parsed.COMBINED,
    text: info.parsed.TEXT,
    table: info.parsed.TABLE,
    markdown: info.parsed.MARKDOWN,
    latex: info.parsed.LATEX,
  };

  const value = contentMap[viewMode] ?? '';
  return value && String(value).trim() !== '' 
    ? String(value) 
    : 'No content available for this view.';
}

