'use client';

import { useEffect, useState } from 'react';


interface LogFile {
  filename: string;
  size: number;
}

interface ModelCounts {
  pass: number;
  fail: number;
  total: number;
}

interface GroupedEntry {
  log: LogFile;
  model: string;
}

interface TrajectoryStep {
  type: string;
  content: string;
  iteration: number;
  success?: boolean | null;
  timestamp?: string;
  toolCall?: string;
  error?: string | null;
  toolDetails?: Record<string, any>;
  toolResult?: string[];
}

interface Trajectory {
  filename: string;
  taskName: string;
  modelName: string;
  totalIterations: number;
  toolCalls: number;
  errors: number;
  testsPassed: number;
  totalTests: number;
  finalSuccess: boolean;
  steps: TrajectoryStep[];
  finalDiffs: {
    agentDiff: string | null;
    goldenDiff: string | null;
    filesChanged: string[];
    diffStats: {
      agentFilesChanged: number;
      goldenFilesChanged: number;
      agentLines: number;
      goldenLines: number;
    };
  } | null;
}

function TrajectoryDetails({ trajectory }: { trajectory: Trajectory }) {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  const filterHarnessMessages = (lines: string[]) => {
    return lines.filter(line => {
      const harnessPattern = /^.?\s*HARNESS:/;
      return !harnessPattern.test(line.trim());
    });
  };

  const extractGradingMetrics = (lines: string[]) => {
    const gradingPatterns = [
      /🧪\s*Total tests:\s*\d+\/\d+\s*passed/i,
      /⏱️\s*Total duration:\s*.+/i,
      /Lab Training Outcome:\s*(FAILURE|SUCCESS)\s*\(binary\)/i,
      /🔍\s*GRADER:\s*Agent diff length:\s*\d+\s*chars/i
    ];

    return lines.filter(line => {
      return gradingPatterns.some(pattern => pattern.test(line.trim()));
    });
  };

  const extractDurationFromLastStep = () => {
    if (!trajectory.steps || trajectory.steps.length === 0) return null;

    const lastStep = trajectory.steps[trajectory.steps.length - 1];

    // Check in toolResult for duration pattern
    if (lastStep.toolResult) {
      for (const line of lastStep.toolResult) {
        const durationMatch = line.match(/⏱️.*Total duration:\s*(.+)/i);
        if (durationMatch) {
          return durationMatch[1].trim();
        }
      }
    }

    // Check in content for duration pattern
    if (lastStep.content) {
      const durationMatch = lastStep.content.match(/⏱️.*Total duration:\s*(.+)/i);
      if (durationMatch) {
        return durationMatch[1].trim();
      }
    }

    return null;
  };

  const extractTestsFromLastStep = () => {
    if (!trajectory.steps || trajectory.steps.length === 0) return null;
    const lastStep = trajectory.steps[trajectory.steps.length - 1];

    const parseFromString = (source: string) => {
      const m = source.match(/Total\s*tests:\s*(\d+)\/(\d+)\s*passed/i);
      if (m) {
        return { passed: parseInt(m[1], 10), total: parseInt(m[2], 10) };
      }
      return null;
    };

    if (lastStep.toolResult) {
      for (const line of lastStep.toolResult) {
        const r = parseFromString(line);
        if (r) return r;
      }
    }

    if (lastStep.content) {
      const r = parseFromString(lastStep.content);
      if (r) return r;
    }

    return null;
  };

  // Get the duration and filter out the last step
  const duration = extractDurationFromLastStep();
  const finalTests = extractTestsFromLastStep();

  const stepsToShow = trajectory.steps || [];

  const toggleStep = (index: number) => {
    const newExpanded = new Set(expandedSteps);
    if (expandedSteps.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSteps(newExpanded);
  };

  const formatDiff = (diffText: string) => {
    return diffText.split('\n').map((line, i) => {
      let className = 'text-gray-700';
      if (line.startsWith('+++') || line.startsWith('---')) {
        className = 'text-blue-600 font-semibold';
      } else if (line.startsWith('@@')) {
        className = 'text-cyan-600 font-semibold bg-cyan-50';
      } else if (line.startsWith('+')) {
        className = 'text-green-700 bg-green-50';
      } else if (line.startsWith('-')) {
        className = 'text-red-700 bg-red-50';
      }
      return (
        <div key={i} className={className}>
          {line}
        </div>
      );
    });
  };

  const getStatusIcon = (step: TrajectoryStep) => {
    if (step.success === true) {
      return (
        <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    } else if (step.success === false) {
      return (
        <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    }
    return (
      <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    );
  };

  const getStatusBadge = (step: TrajectoryStep) => {
    if (step.success === true) {
      return <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-500 text-white">Success</span>;
    } else if (step.success === false) {
      return <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-500 text-white">Error</span>;
    }
    return <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-500 text-white">Info</span>;
  };

  const formatModelName = (raw: string) => {
    if (!raw) return 'Unknown';
    const lower = raw.toLowerCase();
    if (lower.includes('claude')) return 'Claude Sonnet 4.5';
    if (lower.includes('gemini')) return 'Gemini 2.5 Pro';
    if (lower.includes('gpt-5') || lower.includes('gpt 5')) return 'GPT 5';
    return raw;
  };

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div>
        <h3 className="font-semibold text-lg mb-3">Execution Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <div className="text-center p-3 bg-white rounded border">
            <div className="text-lg font-bold">{trajectory.totalIterations}</div>
            <div className="text-xs text-gray-600">Turns</div>
          </div>
          <div className="text-center p-3 bg-white rounded border">
            <div className="text-lg font-bold">{trajectory.errors}</div>
            <div className="text-xs text-gray-600">Errors</div>
          </div>
          {duration && (
            <div className="text-center p-3 bg-white rounded border">
              <div className="text-lg font-bold">{duration}</div>
              <div className="text-xs text-gray-600">Duration</div>
            </div>
          )}
          <div className="text-center p-3 bg-white rounded border">
            <div className="text-lg font-bold">{formatModelName(trajectory.modelName)}</div>
            <div className="text-xs text-gray-600">Model</div>
          </div>
          <div className="text-center p-3 bg-white rounded border">
            <div className="text-lg font-bold">{finalTests ? `${finalTests.passed}/${finalTests.total}` : 'N/A'}</div>
            <div className="text-xs text-gray-600">Tests</div>
          </div>
          <div className="text-center p-3 bg-white rounded border">
            <div className={`text-lg font-bold ${trajectory.finalSuccess ? 'text-green-600' : 'text-red-600'}`}>
              {trajectory.finalSuccess ? 'PASS' : 'FAIL'}
            </div>
            <div className="text-xs text-gray-600">Result</div>
          </div>
        </div>
      </div>

      {/* Execution Steps */}
      {stepsToShow && stepsToShow.length > 0 && (
        <div>
          <h3 className="font-semibold text-lg mb-3">Execution Steps</h3>
          <div className="space-y-3 max-h-[48rem] overflow-y-auto">
            {stepsToShow.map((step, index) => (
              <div key={index} className="border rounded-lg bg-white">
                <div
                  className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => toggleStep(index)}
                >
                  <div className="flex items-center space-x-3">
                    <svg
                      className={`w-4 h-4 transform transition-transform ${
                        expandedSteps.has(index) ? 'rotate-90' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    {getStatusIcon(step)}
                    <div>
                      <div className="font-medium text-sm">
                        {step.type === 'iteration' ? `Turn ${step.iteration}: ` : ''}
                        {step.content}
                      </div>
                      {step.toolCall && <div className="text-xs text-gray-600">Tool: {step.toolCall}</div>}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {step.timestamp && step.timestamp !== 'N/A' && (
                      <span className="text-xs text-gray-500">{step.timestamp}</span>
                    )}
                    {getStatusBadge(step)}
                  </div>
                </div>

                {expandedSteps.has(index) && (
                  <div className="p-3 bg-gray-50 border-t">
                    {step.toolDetails && Object.keys(step.toolDetails).length > 0 && (
                      <div className="mb-4">
                        <h4 className="font-medium text-sm mb-2">Tool Details:</h4>
                        <div className="bg-white p-2 rounded border text-xs">
                          <pre className="whitespace-pre-wrap">{JSON.stringify(step.toolDetails, null, 2)}</pre>
                        </div>
                      </div>
                    )}

                    {step.toolResult && step.toolResult.length > 0 && (() => {
                      // Check if this is the last step
                      const isLastStep = index === stepsToShow.length - 1;

                      let linesToShow;
                      if (isLastStep) {
                        // For the last step, show only grading metrics
                        linesToShow = extractGradingMetrics(step.toolResult);
                      } else {
                        // For other steps, filter out HARNESS messages
                        linesToShow = filterHarnessMessages(step.toolResult);
                      }

                      return linesToShow.length > 0 && (
                        <div className="mb-4">
                          <h4 className="font-medium text-sm mb-2">
                            {isLastStep ? "Grading Metrics:" : "Tool Result:"}
                          </h4>
                          <div className="space-y-2">
                            {linesToShow.map((line, lineIndex) => (
                              <div key={lineIndex} className="p-2 bg-white border rounded text-xs overflow-x-auto">
                                <pre className="whitespace-pre-wrap">{line}</pre>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })()}

                    {step.error && (
                      <div className="mb-4">
                        <h4 className="font-medium text-sm mb-2 text-red-600">Error:</h4>
                        <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                          <pre className="whitespace-pre-wrap">
                            {typeof step.error === 'string' ? step.error : JSON.stringify(step.error, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}

                    {!step.toolDetails && !step.toolResult && !step.error && (
                      <div className="text-gray-500 text-sm">No additional details</div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Final Diff Comparison */}
      {trajectory.finalDiffs && (trajectory.finalDiffs.agentDiff || trajectory.finalDiffs.goldenDiff) && (
        <div>
          <h3 className="font-semibold text-lg mb-3">Agent vs Golden Solution</h3>

          {/* Diff Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div className="text-center p-3 bg-white rounded border">
              <div className="text-lg font-bold">{trajectory.finalDiffs.diffStats.agentFilesChanged}</div>
              <div className="text-xs text-gray-600">Agent Files Changed</div>
            </div>
            <div className="text-center p-3 bg-white rounded border">
              <div className="text-lg font-bold">{trajectory.finalDiffs.diffStats.goldenFilesChanged}</div>
              <div className="text-xs text-gray-600">Golden Files Changed</div>
            </div>
            <div className="text-center p-3 bg-white rounded border">
              <div className="text-lg font-bold text-blue-600">{trajectory.finalDiffs.diffStats.agentLines}</div>
              <div className="text-xs text-gray-600">Agent Diff Lines</div>
            </div>
            <div className="text-center p-3 bg-white rounded border">
              <div className="text-lg font-bold text-green-600">{trajectory.finalDiffs.diffStats.goldenLines}</div>
              <div className="text-xs text-gray-600">Golden Diff Lines</div>
            </div>
          </div>

          {/* Side-by-side diff viewer */}
          <div className="border rounded-lg overflow-hidden bg-white">
            <div className="grid grid-cols-2">
              <div className="bg-blue-600 text-white p-3 text-center font-semibold">Agent Implementation</div>
              <div className="bg-green-600 text-white p-3 text-center font-semibold">Golden Solution</div>
            </div>
            <div className="grid grid-cols-2 min-h-96">
              <div className="p-4 bg-gray-50 border-r overflow-auto max-h-96">
                {trajectory.finalDiffs.agentDiff ? (
                  <pre className="text-xs font-mono whitespace-pre-wrap">{formatDiff(trajectory.finalDiffs.agentDiff)}</pre>
                ) : (
                  <div className="text-gray-500 italic">No agent changes detected</div>
                )}
              </div>
              <div className="p-4 bg-gray-50 overflow-auto max-h-96">
                {trajectory.finalDiffs.goldenDiff ? (
                  <pre className="text-xs font-mono whitespace-pre-wrap">{formatDiff(trajectory.finalDiffs.goldenDiff)}</pre>
                ) : (
                  <div className="text-gray-500 italic">No golden solution available</div>
                )}
              </div>
            </div>
          </div>

          {/* Files Changed */}
          {trajectory.finalDiffs.filesChanged && trajectory.finalDiffs.filesChanged.length > 0 && (
            <div className="mt-4">
              <h4 className="font-semibold text-gray-700 mb-2">Files Modified by Agent:</h4>
              <div className="flex flex-wrap gap-2">
                {trajectory.finalDiffs.filesChanged.map((file, i) => (
                  <span key={i} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-mono">
                    {file}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function IDEArenaPage() {
  const [logs, setLogs] = useState<LogFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modelPassRates, setModelPassRates] = useState<Map<string, ModelCounts>>(new Map());
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [trajectories, setTrajectories] = useState<Map<string, any>>(new Map());
  const [selectedModelByTaskId, setSelectedModelByTaskId] = useState<Map<string, string>>(new Map());
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadLogFiles();
  }, []);

  async function loadLogFiles() {
    try {
      setLoading(true);
      setError(null);
      // console.log('Fetching logs from /api/ide-arena/logs');

      const response = await fetch('/api/sweagent/logs');
      // console.log('Response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to load logs: ${response.status} - ${errorText}`);
      }

      const logsData: LogFile[] = await response.json();
      // console.log('Loaded logs:', logsData.length);

      setLogs(logsData);
      await computeModelPassRates(logsData);
      setLoading(false);
    } catch (err: any) {
      console.error('Error loading logs:', err);
      setError(err.message);
      setLoading(false);
    }
  }

  async function computeModelPassRates(logsData: LogFile[]) {
    const counts = new Map<string, ModelCounts>();

    const results = await Promise.all(
      logsData.map(async (log) => {
        try {
          const res = await fetch(`/api/sweagent/raw-logs/${encodeURIComponent(log.filename)}`);
          if (!res.ok) return null;
          const text = await res.text();
          const verdict = parsePassFailFromLogText(text);
          return { filename: log.filename, finalSuccess: verdict === true };
        } catch {
          return null;
        }
      })
    );

    // Dynamically collect all models found in the data
    for (const r of results) {
      if (!r) continue;
      const parsed = parseTrajectoryFilename(r.filename);

      // Initialize model in counts if not already present
      if (!counts.has(parsed.model)) {
        counts.set(parsed.model, { pass: 0, fail: 0, total: 0 });
      }

      const entry = counts.get(parsed.model)!;
      entry.total += 1;
      if (r.finalSuccess) entry.pass += 1;
      else entry.fail += 1;
    }

    setModelPassRates(counts);
  }

  function parseTrajectoryFilename(filename: string) {
    const knownModels = [
      { pattern: 'claude-sonnet-4-5-20250929', display: 'Claude Sonnet 4.5' },
      { pattern: 'gemini_gemini-2.5-pro', display: 'Gemini 2.5 Pro' },
      { pattern: 'gpt-5', display: 'GPT-5' }
    ];

    let model = 'Unknown';
    let taskRaw = filename;

    // First try known models with specific display names
    for (const modelInfo of knownModels) {
      const idx = filename.indexOf(modelInfo.pattern);
      if (idx !== -1) {
        model = modelInfo.display;
        taskRaw = filename.substring(idx + modelInfo.pattern.length);
        break;
      }
    }

    // If no known model found, try to extract any model pattern
    if (model === 'Unknown') {
      // Look for common model patterns in filenames
      const modelPatterns = [
        /^(.+?)[-_](.+?)\.(log|txt)$/i, // model-task.log
        /^(.+?)[-_](.+)$/i, // model-task or model_task
        /^([^-_]+)[-_](.+)$/ // basic model_rest pattern
      ];

      for (const pattern of modelPatterns) {
        const match = filename.match(pattern);
        if (match) {
          const potentialModel = match[1];
          // Check if this looks like a model name (has letters and possibly numbers/dashes)
          if (/^[a-zA-Z]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$/.test(potentialModel)) {
            model = potentialModel.replace(/[_]/g, ' ').replace(/[-]/g, ' ');
            // Capitalize each word
            model = model.split(' ').map(word =>
              word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
            ).join(' ');
            taskRaw = match[2] || filename;
            break;
          }
        }
      }
    }

    // Clean up task name
    taskRaw = taskRaw.replace(/^[-_.]+/, '').replace(/\.(log|txt)$/i, '');

    if (!taskRaw) {
      taskRaw = filename.replace(/\.(log|txt)$/i, '');
    }

    const task = taskRaw
      .replace(/[_-]+/g, ' ')
      .trim()
      .split(' ')
      .filter(Boolean)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');

    return { model, task };
  }

  function parsePassFailFromLogText(text: string): boolean | null {
    if (!text) return null;

    const totalTestsRegex = /Total\s+tests:\s*(\d+)\/(\d+)\s*passed/gi;
    let match;
    let lastPassed: number | null = null;
    let lastTotal: number | null = null;
    while ((match = totalTestsRegex.exec(text)) !== null) {
      lastPassed = parseInt(match[1], 10);
      lastTotal = parseInt(match[2], 10);
    }

    if (lastPassed !== null && lastTotal !== null) {
      if (lastTotal > 0) return lastPassed === lastTotal;
      return false;
    }

    const passedLineRegex = /Passed\s*(\d+)\/(\d+)\s*tests/gi;
    let pMatch;
    let pPassed: number | null = null;
    let pTotal: number | null = null;
    while ((pMatch = passedLineRegex.exec(text)) !== null) {
      pPassed = parseInt(pMatch[1], 10);
      pTotal = parseInt(pMatch[2], 10);
    }
    if (pPassed !== null && pTotal !== null) {
      if (pTotal > 0) return pPassed === pTotal;
      return false;
    }

    return null;
  }

  function getTaskIdFromFilename(filename: string): string {
    const knownModels = [
      'claude-sonnet-4-5-20250929',
      'gemini_gemini-2.5-pro',
      'gpt-5'
    ];

    let taskRaw = filename;

    // First try known model patterns
    for (const pattern of knownModels) {
      const idx = filename.indexOf(pattern);
      if (idx !== -1) {
        taskRaw = filename.substring(idx + pattern.length);
        break;
      }
    }

    // If no known pattern found, try to find any model-task pattern
    if (taskRaw === filename) {
      const modelPatterns = [
        /^(.+?)[-_](.+?)\.(log|txt)$/i, // model-task.log
        /^(.+?)[-_](.+)$/i, // model-task or model_task
        /^([^-_]+)[-_](.+)$/ // basic model_rest pattern
      ];

      for (const pattern of modelPatterns) {
        const match = filename.match(pattern);
        if (match && match[2]) {
          taskRaw = match[2];
          break;
        }
      }
    }

    taskRaw = taskRaw.replace(/^[-_.]+/, '').replace(/\.(log|txt)$/i, '');
    return taskRaw || filename.replace(/\.(log|txt)$/i, '');
  }

  function formatTaskIdToTitle(taskId: string): string {
    return taskId
      .replace(/[_-]+/g, ' ')
      .trim()
      .split(' ')
      .filter(Boolean)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  async function toggleTrajectory(filename: string) {
    const newExpanded = new Set(expandedFiles);

    if (expandedFiles.has(filename)) {
      newExpanded.delete(filename);
    } else {
      newExpanded.add(filename);

      if (!trajectories.has(filename)) {
        try {
          const response = await fetch(`/api/sweagent/trajectory/${encodeURIComponent(filename)}`);
          if (!response.ok) throw new Error('Failed to load trajectory');
          const trajectory = await response.json();

          const newTrajectories = new Map(trajectories);
          newTrajectories.set(filename, trajectory);
          setTrajectories(newTrajectories);
        } catch (err: any) {
          console.error('Error loading trajectory:', err);
        }
      }
    }

    setExpandedFiles(newExpanded);
  }

  function buildGroupedMap(logsList: LogFile[]) {
    return logsList.reduce((acc, log) => {
      const id = getTaskIdFromFilename(log.filename);
      const parsed = parseTrajectoryFilename(log.filename);
      const list = acc.get(id) || [];
      list.push({ log, model: parsed.model });
      acc.set(id, list);
      return acc;
    }, new Map<string, GroupedEntry[]>());
  }

  async function ensureTrajectory(filename: string) {
    if (trajectories.has(filename)) return;
    try {
      const response = await fetch(`/api/sweagent/trajectory/${encodeURIComponent(filename)}`);
      if (!response.ok) return;
      const trajectory = await response.json();
      const newTrajectories = new Map(trajectories);
      newTrajectories.set(filename, trajectory);
      setTrajectories(newTrajectories);
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    if (!logs || logs.length === 0) return;
    const grouped = buildGroupedMap(logs);

    // Get all available models dynamically and create preferred order
    const allModels = new Set<string>();
    Array.from(grouped.values()).forEach(entries => {
      entries.forEach(entry => allModels.add(entry.model));
    });

    // Preferred order - known models first, then alphabetically sorted unknown models
    const preferredOrder = ['GPT-5', 'Claude Sonnet 4.5', 'Gemini 2.5 Pro'];
    const unknownModels = Array.from(allModels)
      .filter(model => !preferredOrder.includes(model))
      .sort();
    const modelDisplayOrder = [...preferredOrder.filter(model => allModels.has(model)), ...unknownModels];

    const nextSelected = new Map(selectedModelByTaskId);
    for (const [taskId, entries] of Array.from(grouped.entries())) {
      if (!nextSelected.has(taskId)) {
        const available = modelDisplayOrder.find((m) => entries.some((e) => e.model === m)) || entries[0]?.model;
        if (available) {
          nextSelected.set(taskId, available);
          const filename = entries.find((e) => e.model === available)!.log.filename;
          void ensureTrajectory(filename);
        }
      }
    }
    if (nextSelected.size !== selectedModelByTaskId.size) {
      setSelectedModelByTaskId(nextSelected);
    }
  }, [logs]);

  const toggleTaskExpanded = (taskId: string) => {
    const newSet = new Set(expandedTasks);
    if (newSet.has(taskId)) {
      newSet.delete(taskId);
    } else {
      newSet.add(taskId);
    }
    setExpandedTasks(newSet);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <h1 className="text-2xl text-gray-400 tracking-wide">Loading...</h1>
      </div>
    );
  }

  return (
    <div className="bg-gray-100 min-h-screen">
      <div className="container mx-auto px-4 py-8">
        {/* Hero Header */}
        <div className="relative w-full bg-[#ECF3FE] rounded-2xl overflow-hidden isolate mb-6">
          {/* Grid background */}
          <div
            className="absolute inset-0 w-full h-full"
            style={{
              backgroundImage: `linear-gradient(rgba(7, 92, 182, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(7, 92, 182, 0.08) 1px, transparent 1px)`,
              backgroundSize: '40px 40px, 40px 40px',
              backgroundPosition: '0 0, 0 0',
              minHeight: '100%'
            }}
          />
          {/* Plus pattern */}
          <svg className="absolute top-0 left-0 w-full h-full pointer-events-none" style={{ opacity: 0.3 }} width="100%" height="100%">
            <defs>
              <pattern id="ide-arena-plus-pattern" x="40" y="80" width="200" height="200" patternUnits="userSpaceOnUse">
                <line x1="0.5" y1="0.5" x2="0.5" y2="10.5" stroke="rgba(7, 92, 182, 1)" strokeWidth="1" />
                <line x1="0.5" y1="0.5" x2="10.5" y2="0.5" stroke="rgba(7, 92, 182, 1)" strokeWidth="1" />
                <line x1="200.5" y1="0.5" x2="200.5" y2="10.5" stroke="rgba(7, 92, 182, 1)" strokeWidth="1" />
                <line x1="190.5" y1="0.5" x2="200.5" y2="0.5" stroke="rgba(7, 92, 182, 1)" strokeWidth="1" />
                <line x1="0.5" y1="190.5" x2="0.5" y2="200.5" stroke="rgba(7, 92, 182, 1)" strokeWidth="1" />
                <line x1="0.5" y1="200.5" x2="10.5" y2="200.5" stroke="rgba(7, 92, 182, 1)" strokeWidth="1" />
                <line x1="200.5" y1="190.5" x2="200.5" y2="200.5" stroke="rgba(7, 92, 182, 1)" strokeWidth="1" />
                <line x1="190.5" y1="200.5" x2="200.5" y2="200.5" stroke="rgba(7, 92, 182, 1)" strokeWidth="1" />
              </pattern>
            </defs>
            <rect x="0" y="0" width="100%" height="100%" fill="url(#ide-arena-plus-pattern)" />
          </svg>
          {/* Blur ellipse */}
          <div className="absolute left-1/2 -translate-x-1/2 bottom-0 translate-y-1/2 w-[800px] h-[800px] bg-[#80CCF5] rounded-full opacity-100" style={{ filter: 'blur(257px)' }} />

          <div className="relative z-10 px-6 py-10 sm:px-12 lg:px-16">

            {/* Heading */}
            <h1 className="mt-6 text-4xl sm:text-4xl lg:text-5xl font-normal tracking-tight text-[#1A1A1A] leading-tight">
              <span style={{ fontFamily: 'Gambarino, var(--font-heading, system-ui)' }}>IDE Arena Trajectories</span>
              <br />
            </h1>
            <p className="mt-3 text-gray-700">
              You are viewing the local version of the IDE Arena Trajectories, pulling from /logs. View coding agent performance and execution traces.
            </p>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
            <p className="text-red-700">Error: {error}</p>
            <button
              onClick={loadLogFiles}
              className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        )}

        {/* Pass Rate by Model */}
        <div className="bg-white rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Pass Rate by Model</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Array.from(modelPassRates.entries()).map(([model, data]) => {
              const passPct = data.total ? (data.pass / data.total) : 0;
              const failPct = data.total ? (data.fail / data.total) : 0;
              const passH = Math.round(passPct * 128);
              const failH = Math.round(failPct * 128);

              return (
                 <div key={model} className="border rounded-lg overflow-hidden bg-red">
                   <div className="bg-gradient-to-r from-[#ECF3FE] to-[#DDEFFF] text-[#1A1A1A] text-center font-medium py-2 border-b border-[#cfdff5] mb-5">{model}</div>
                   <div className="p-4 pt-4">
                  <div className="flex items-end justify-center space-x-12 h-32">
                    <div className="flex flex-col items-center text-center">
                      <div className="text-xs font-semibold text-green-600 mb-1">{data.pass}</div>
                      <div className="w-10 bg-green-500 rounded" style={{ height: `${passH}px`, maxHeight: '100px' }} />
                      <div className="text-xs mt-2 text-gray-700">Correct ({Math.round(passPct * 100)}%)</div>
                    </div>
                    <div className="flex flex-col items-center text-center">
                      <div className="text-xs font-semibold text-red-600 mb-1">{data.fail}</div>
                      <div className="w-10 bg-red-500 rounded" style={{ height: `${failH}px`, maxHeight: '100px' }} />
                      <div className="text-xs mt-2 text-gray-700">Incorrect ({Math.round(failPct * 100)}%)</div>
                    </div>
                  </div>
                  {/* <div className="text-xs text-gray-500 mt-3 text-center">
                    Total Questions: {data.total}
                  </div> */}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Trajectory Files List */}
        <div className="bg-white rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Coding Agent Trajectories</h2>

          {(() => {
            if (logs.length === 0) {
              return <p className="text-gray-500 text-center py-8">No trajectory files found</p>;
            }

            const grouped = buildGroupedMap(logs);

            // Get all available models dynamically and create preferred order
            const allModels = new Set<string>();
            Array.from(grouped.values()).forEach(entries => {
              entries.forEach(entry => allModels.add(entry.model));
            });

            const preferredOrder = ['GPT-5', 'Claude Sonnet 4.5', 'Gemini 2.5 Pro'];
            const unknownModels = Array.from(allModels)
              .filter(model => !preferredOrder.includes(model))
              .sort();
            const modelDisplayOrder = [...preferredOrder.filter(model => allModels.has(model)), ...unknownModels];

            return (
              <div className="space-y-4">
                {Array.from(grouped.entries())
                  .sort((a, b) => formatTaskIdToTitle(a[0]).localeCompare(formatTaskIdToTitle(b[0])))
                  .map(([taskId, entries]) => (
                    <div key={taskId} className="border border-gray-200 rounded-lg">
                      <div
                        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
                        onClick={() => {
                          toggleTaskExpanded(taskId);
                          const selectedModel = selectedModelByTaskId.get(taskId) || modelDisplayOrder.find((m) => entries.some((e) => e.model === m)) || entries[0]?.model;
                          if (selectedModel) {
                            const filename = entries.find((e) => e.model === selectedModel)!.log.filename;
                            void ensureTrajectory(filename);
                          }
                        }}
                      >
                        <div className="flex items-center space-x-3">
                          <svg
                            className={`w-4 h-4 transform transition-transform ${expandedTasks.has(taskId) ? 'rotate-90' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                          <div className="font-semibold text-gray-900">{formatTaskIdToTitle(taskId)}</div>
                        </div>
                      </div>

                      {expandedTasks.has(taskId) && (
                        <div className="border-t p-4">
                          <div className="flex justify-center">
                            <div className="inline-flex items-center gap-1 bg-gray-100 rounded-full p-1 shadow-inner">
                              {modelDisplayOrder
                                .filter((model) => entries.some((e) => e.model === model))
                                .map((model) => {
                                  const isSelected = selectedModelByTaskId.get(taskId) === model;
                                  return (
                                    <button
                                      key={model}
                                      className={`px-5 py-2 rounded-full text-sm font-medium transition-colors ${
                                        isSelected ? 'bg-white shadow text-gray-900' : 'text-gray-700 hover:text-gray-900'
                                      }`}
                                      onClick={() => {
                                        const next = new Map(selectedModelByTaskId);
                                        next.set(taskId, model);
                                        setSelectedModelByTaskId(next);
                                        const filename = entries.find((e) => e.model === model)!.log.filename;
                                        void ensureTrajectory(filename);
                                      }}
                                    >
                                      {model}
                                    </button>
                                  );
                                })}
                            </div>
                          </div>
                          <div className="mt-6">
                            {(() => {
                              const selectedModel = selectedModelByTaskId.get(taskId) || modelDisplayOrder.find((m) => entries.some((e) => e.model === m)) || entries[0]?.model;
                              if (!selectedModel) return null;
                              const filename = entries.find((e) => e.model === selectedModel)!.log.filename;
                              const trajectory = trajectories.get(filename);
                              if (!trajectory) {
                                return <p className="text-gray-600">Loading trajectory data...</p>;
                              }
                              return <TrajectoryDetails trajectory={trajectory} />;
                            })()}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
