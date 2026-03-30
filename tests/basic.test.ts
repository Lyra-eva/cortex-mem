/**
 * Evolution V5 基础测试
 */

import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';

const EMBEDDING_SERVER_URL = 'http://127.0.0.1:9721';

describe('Embedding Server', () => {
  it('health endpoint should return ok', async () => {
    const resp = await fetch(`${EMBEDDING_SERVER_URL}/health`);
    const data: any = await resp.json();
    expect(data.status).toBe('ok');
    expect(data.model).toBe('bge-small-zh-v1.5');
  });

  it('should generate embeddings', async () => {
    const resp = await fetch(`${EMBEDDING_SERVER_URL}/embed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts: ['你好', '世界'] })
    });
    const data: any = await resp.json();
    expect(data.embeddings).toBeDefined();
    expect(data.embeddings.length).toBe(2);
    expect(data.embeddings[0].length).toBe(512);
  });

  it('should save and search memory', async () => {
    const testContent = `测试记忆 ${Date.now()}`;
    const agentId = 'main';

    // Save
    const saveResp = await fetch(`${EMBEDDING_SERVER_URL}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: testContent,
        agent_id: agentId,
        type: 'episodic'
      })
    });
    expect(saveResp.ok).toBe(true);

    // Search
    const searchResp = await fetch(`${EMBEDDING_SERVER_URL}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: '测试记忆',
        agent_id: agentId,
        limit: 5
      })
    });
    const searchData: any = await searchResp.json();
    expect(searchData.results).toBeDefined();
    expect(searchData.results.length).toBeGreaterThan(0);
  });
});

describe('Memory Stats', () => {
  it('should return tenant stats', async () => {
    const resp = await fetch(`${EMBEDDING_SERVER_URL}/health`);
    const data: any = await resp.json();
    expect(data.stats).toBeDefined();
    expect(data.stats.main).toBeDefined();
    expect(typeof data.stats.main.memories).toBe('number');
  });
});
