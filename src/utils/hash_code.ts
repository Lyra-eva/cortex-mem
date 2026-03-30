/**
 * 字符串 Hash 函数（用于缓存 key）
 */

export function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash;
}

export function hashContent(content: string): string {
  return `${Math.abs(hashCode(content)) & 0xFFFFFFFF}`;
}
