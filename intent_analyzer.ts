/**
 * 意图分析器 - 自动分析用户意图并触发对应系统
 */

export interface IntentResult {
  type: 'reasoning' | 'learning' | 'emotional' | 'task' | 'perception' | 'conversation';
  confidence: number;
  action?: string;
  params?: any;
}

/**
 * 分析用户消息意图
 */
export function analyzeIntent(content: string): IntentResult {
  const contentLower = content.toLowerCase();
  
  const patterns: Record<string, { patterns: string[]; confidence: number }> = {
    reasoning: {
      patterns: ['影响', '为什么', '推理', '分析', '原因', '结果', '如何影响', '对...的影响'],
      confidence: 0.9
    },
    learning: {
      patterns: ['学习', '记住', '文档', '材料', '知识', '笔记', '记录'],
      confidence: 0.85
    },
    emotional: {
      patterns: ['心情', '高兴', '难过', '情绪', '开心', '生气', '伤心', '感觉'],
      confidence: 0.8
    },
    task: {
      patterns: ['帮我', '执行', '任务', '发送', '完成', '做'],
      confidence: 0.85
    },
    perception: {
      patterns: ['分析这条', '优先级', '紧急', '重要'],
      confidence: 0.75
    }
  };
  
  // 匹配意图
  let bestMatch: { type: string; confidence: number } = { type: 'conversation', confidence: 0.5 };
  
  for (const [intent, config] of Object.entries(patterns)) {
    for (const pattern of config.patterns) {
      if (content.includes(pattern) || contentLower.includes(pattern.toLowerCase())) {
        if (config.confidence > bestMatch.confidence) {
          bestMatch = { type: intent, confidence: config.confidence };
        }
      }
    }
  }
  
  return {
    type: bestMatch.type as any,
    confidence: bestMatch.confidence,
    action: getActionForIntent(bestMatch.type as any),
    params: { query: content }
  };
}

/**
 * 根据意图获取对应的 action
 */
function getActionForIntent(intent: string): string {
  const actions: Record<string, string> = {
    reasoning: 'think',
    learning: 'learn',
    emotional: 'feel',
    task: 'execute',
    perception: 'perceive',
    conversation: 'search'
  };
  return actions[intent] || 'search';
}

/**
 * 构建系统调用请求
 */
export function buildSystemCall(intent: IntentResult): { url: string; body: any } {
  const services: Record<string, string> = {
    think: 'http://127.0.0.1:9722/reason',
    learn: 'http://127.0.0.1:9723/learn',
    feel: 'http://127.0.0.1:9724/feel',
    execute: 'http://127.0.0.1:9726/execute',
    perceive: 'http://127.0.0.1:9727/perceive',
    search: 'http://127.0.0.1:9721/search'
  };
  
  const url = services[intent.action || 'search'];
  
  const body: any = { query: intent.params?.query || '' };
  
  if (intent.action === 'learn') {
    body.material = { title: '学习内容', content: intent.params?.query };
  } else if (intent.action === 'feel') {
    body.event = intent.params?.query;
  } else if (intent.action === 'execute') {
    body.goal = intent.params?.query;
  } else if (intent.action === 'perceive') {
    body.content = intent.params?.query;
    body.source = 'message';
  }
  
  return { url, body };
}
