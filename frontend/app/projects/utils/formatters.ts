/**
 * Format a date string into a human-readable relative time
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
  
  if (diffInMinutes < 1) return 'Just now';
  if (diffInMinutes < 60) return `${diffInMinutes} mins ago`;
  
  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) return `${diffInHours} hours ago`;
  
  const diffInDays = Math.floor(diffInHours / 24);
  return `${diffInDays} days ago`;
}

/**
 * Format latency in milliseconds to seconds with 2 decimal places
 */
export function formatLatency(latencyMs: number | null | undefined): string {
  if (!latencyMs) return "-";
  return `${(latencyMs / 1000).toFixed(2)}s`;
}

/**
 * Format cost to 4 decimal places with dollar sign
 */
export function formatCost(cost: number | null | undefined): string {
  return `$${(cost || 0).toFixed(4)}`;
}

/**
 * Format rating display
 */
export function formatRating(rating: number | null | undefined): string | null {
  if (!rating) return null;
  return `${rating}/5`;
}

