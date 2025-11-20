export interface ModelConfig {
  pattern: string;
  display: string;
  key?: string;
}

export const MODEL_CONFIGS: ModelConfig[] = [
  { pattern: 'openrouter_x-ai_grok-4-fast', display: 'Grok 4', key: 'grok-4' },
  { pattern: 'grok-4-fast', display: 'Grok 4', key: 'grok-4' },

  { pattern: 'claude-sonnet-4-5-20250929', display: 'Claude Sonnet 4.5', key: 'claude-sonnet-4.5' },
  { pattern: 'claude-sonnet-4.5', display: 'Claude Sonnet 4.5', key: 'claude-sonnet-4.5' },
  { pattern: 'claude-sonnet-4-5', display: 'Claude Sonnet 4.5', key: 'claude-sonnet-4.5' },
  { pattern: 'claude', display: 'Claude Sonnet 4.5', key: 'claude-sonnet-4.5' },

  { pattern: 'gemini-2.5-pro', display: 'Gemini 2.5 Pro', key: 'gemini-2.5-pro' },
  { pattern: 'gemini_gemini-2.5-pro', display: 'Gemini 2.5 Pro', key: 'gemini-2.5-pro' },
  { pattern: 'gemini-2-5-pro', display: 'Gemini 2.5 Pro', key: 'gemini-2.5-pro' },
  { pattern: 'openrouter_gemini_3_pro_preview', display: 'Gemini 3 Pro Preview', key: 'gemini-3-pro' },
  { pattern: 'openrouter_gemini-3-pro-preview', display: 'Gemini 3 Pro Preview', key: 'gemini-3-pro' },
  { pattern: 'gemini-3-pro', display: 'Gemini 3 Pro Preview', key: 'gemini-3-pro' },
  { pattern: 'gemini', display: 'Gemini 2.5 Pro', key: 'gemini-2.5-pro' },

  { pattern: 'gpt-5.1', display: 'GPT-5.1', key: 'gpt-5.1' },
  { pattern: 'gpt-5-1', display: 'GPT-5.1', key: 'gpt-5.1' },
  { pattern: 'gpt 5.1', display: 'GPT-5.1', key: 'gpt-5.1' },

  { pattern: 'gpt-4o', display: 'GPT-4o', key: 'gpt-4o' },
  { pattern: 'gpt4o', display: 'GPT-4o', key: 'gpt-4o' },
  { pattern: 'gpt_4o', display: 'GPT-4o', key: 'gpt-4o' },

  { pattern: 'gpt-4', display: 'GPT-4', key: 'gpt-4' },
  { pattern: 'gpt4', display: 'GPT-4', key: 'gpt-4' },

  { pattern: 'o1-preview', display: 'O1 Preview', key: 'o1-preview' },
  { pattern: 'o1_preview', display: 'O1 Preview', key: 'o1-preview' },
  { pattern: 'o1', display: 'O1', key: 'o1' },

  { pattern: 'oracle', display: 'Oracle', key: 'oracle' },
  { pattern: 'nullagent', display: 'Nullagent', key: 'nullagent' },
];

export const MODEL_DISPLAY_ORDER = ['Grok 4', 'GPT-5.1', 'Claude Sonnet 4.5', 'Gemini 2.5 Pro'];

export function getModelDisplayName(raw: string): string {
  if (!raw) return 'Unknown';
  const lower = raw.toLowerCase();

  for (const config of MODEL_CONFIGS) {
    if (lower.includes(config.pattern.toLowerCase())) {
      return config.display;
    }
  }

  return raw;
}

export function getModelConfigs(): ModelConfig[] {
  return MODEL_CONFIGS;
}

export function getUniqueModels(): { key: string; display: string }[] {
  const seen = new Set<string>();
  const unique: { key: string; display: string }[] = [];

  for (const config of MODEL_CONFIGS) {
    if (config.key && !seen.has(config.key)) {
      seen.add(config.key);
      unique.push({ key: config.key, display: config.display });
    }
  }

  return unique;
}

