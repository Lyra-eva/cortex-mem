/**
 * HTTP 连接池（Keepalive 复用连接）
 */

import * as http from 'node:http';
import * as https from 'node:https';

// HTTP Agent（连接池）
export const httpAgent = new http.Agent({
  keepAlive: true,
  maxSockets: 50,
  maxFreeSockets: 10,
  timeout: 5000
});

// HTTPS Agent（连接池）
export const httpsAgent = new https.Agent({
  keepAlive: true,
  maxSockets: 50,
  maxFreeSockets: 10,
  timeout: 5000
});

// 优化的 fetch 函数（使用连接池）
export async function fetchWithAgent(url: string, options: any = {}): Promise<any> {
  const agent = url.startsWith('https') ? httpsAgent : httpAgent;
  return fetch(url, { ...options, agent });
}
