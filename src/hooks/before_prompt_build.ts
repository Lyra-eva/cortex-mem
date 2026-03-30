/**
 * before_prompt_build 钩子处理
 * 功能：检索记忆 + 注入上下文 + 自动保存对话 + 缓存失效联动
 */

import { fetchWithAgent, hashContent } from '../utils';
import { cacheManager } from '../cache';

export interface HookContext {
  currentAgentId: string;
  redisClient: any;
  debugLog: (msg: string) => void;
}

export async function handleBeforePromptBuild(
  event: any,
  ctx: HookContext
): Promise<any> {
  const { currentAgentId, debugLog } = ctx;
  debugLog(`before_prompt_build agent: ${currentAgentId}`);

  // 提取用户消息
  let content = '';
  const prompt = event?.prompt || '';
  if (typeof prompt === 'string' && prompt.length > 0) {
    const lines = prompt.split('\n');
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();
      if (line.length > 0) {
        content = line.replace(/^[^\s:]+:\s*/, '');
        break;
      }
    }
  }

  if (content.length < 3) return {};

  // 自动保存对话 + 缓存失效联动
  if (content.length > 15) {
    setImmediate(async () => {
      try {
        const saveResp = await fetchWithAgent('http://127.0.0.1:9721/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: content.slice(0, 500),
            type: 'episodic',
            agent_id: currentAgentId,
            metadata: { source: 'user', timestamp: Date.now() }
          })
        });
        debugLog(`✅ Auto-saved episode for ${currentAgentId}`);

        // 缓存失效联动
        const keys = await cacheManager.keys(`cache:${currentAgentId}:episodic:*`);
        if (keys.length > 0) {
          await cacheManager.del(...keys);
          debugLog(`Cache invalidated: ${keys.length} keys`);
        }
      } catch (e) {
        debugLog(`❌ Save failed: ${(e as Error).message}`);
      }
    });
  }

  // 检索相关记忆并注入（带缓存）
  const memType = 'episodic';
  const cacheKey = `cache:${currentAgentId}:${memType}:${hashContent(content)}`;

  try {
    let memories: any[] = [];
    let cacheHit = false;

    // 检查缓存
    const cached = await cacheManager.get<any[]>(cacheKey);
    if (cached && Array.isArray(cached)) {
      memories = cached;
      cacheHit = true;
      debugLog(`Cache HIT: ${cacheKey}`);
    }

    // 缓存未命中 → 检索
    if (!cacheHit && memories.length === 0) {
      const resp = await fetchWithAgent('http://127.0.0.1:9721/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: content,
          agent_id: currentAgentId,
          type: memType,
          limit: 3
        })
      });

      if (resp.ok) {
        const data: any = await resp.json();
        memories = data.results || [];

        // 写入缓存
        if (memories.length > 0) {
          const ttl = memType === 'episodic' ? 1800 : 7200;
          await cacheManager.set(cacheKey, memories, ttl);
          debugLog(`Cache written: ${cacheKey} (TTL=${ttl}s)`);
        }
      }
    }

    // 注入记忆上下文
    if (memories.length > 0) {
      const memoryText = memories.map((m: any) => {
        const content = m.content || '';
        return `• ${content.slice(0, 150)}`;
      }).join('\n');

      debugLog(`Injecting ${memories.length} memories (${cacheHit ? 'cache' : 'search'})`);
      return {
        prependSystemContext: `[相关记忆]\n${memoryText}`
      };
    }
  } catch (e) {
    debugLog(`Search failed: ${(e as Error).message}`);
  }

  return {};
}
