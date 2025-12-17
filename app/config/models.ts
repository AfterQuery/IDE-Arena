export interface ModelConfig {
  pattern: string;
  display: string;
  key?: string;
}

export const MODEL_CONFIGS: ModelConfig[] = [
  { pattern: 'oracle', display: 'Oracle', key: 'oracle' },
  { pattern: 'nullagent', display: 'Nullagent', key: 'nullagent' },
  { pattern: '', display: 'Unknown Model', key: 'unknown' },
];

export const MODEL_DISPLAY_ORDER = ['Grok 4', 'GPT-5.1', 'Claude Sonnet 4.5', 'Gemini 2.5 Pro'];

export function getModelDisplayName(raw: string): string {
  if (!raw) return 'Unknown';
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

