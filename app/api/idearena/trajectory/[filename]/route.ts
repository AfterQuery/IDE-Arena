import { NextRequest, NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";
import { getModelDisplayName } from "../../../../config/models";

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

interface TestResult {
  name: string;
  status: 'pass' | 'fail';
  fullName: string;
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
  duration?: string;
  steps: TrajectoryStep[];
  finalDiffs: any;
  testResults: TestResult[];
  labTrainingMetrics?: {
    testsPassed: boolean;
    agentSuccess: boolean;
    codeChangesMade: boolean;
    noSyntaxErrors: boolean;
    conversationLength: number;
    successfulEdits: number;
    finalCodeFiles: number;
  };
  nullagentBaseline?: Trajectory;
  oracleBaseline?: Trajectory;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ filename: string }> }
) {
  try {
    const { filename } = await params;
    const logsDir = path.join(process.cwd(), "logs");
    const filePath = path.join(logsDir, filename);

    // Check if file exists
    try {
      await fs.access(filePath);
    } catch {
      return NextResponse.json(
        { error: `File ${filename} not found` },
        { status: 404 }
      );
    }

    const content = await fs.readFile(filePath, "utf-8");
    const trajectory = parseLogFile(filename, content);

    // Check for baseline logs (nullagent and oracle)
    const taskName = extractTaskName(filename);
    if (taskName) {
      try {
        // Try to load nullagent baseline
        const nullagentFilename = `nullagent_${taskName}.log`;
        const nullagentPath = path.join(logsDir, nullagentFilename);
        const nullagentContent = await fs.readFile(nullagentPath, "utf-8");
        trajectory.nullagentBaseline = parseLogFile(nullagentFilename, nullagentContent);
      } catch {
        // Nullagent baseline not found, that's okay
      }

      try {
        // Try to load oracle (golden solution)
        const oracleFilename = `oracle_${taskName}.log`;
        const oraclePath = path.join(logsDir, oracleFilename);
        const oracleContent = await fs.readFile(oraclePath, "utf-8");
        trajectory.oracleBaseline = parseLogFile(oracleFilename, oracleContent);
      } catch {
        // Oracle baseline not found, that's okay
      }
    }

    return NextResponse.json(trajectory);
  } catch (error: any) {
    console.error("Error reading trajectory file:", error);
    return NextResponse.json(
      { error: "Failed to read trajectory", details: error.message },
      { status: 500 }
    );
  }
}


function parseOracleOrNullLog(trajectory: Trajectory, filename: string, content: string): Trajectory {
  const filenameWithoutExt = filename.replace(/\.log$/i, '');
  const parts = filenameWithoutExt.split('_');
  
  if (parts.length >= 3) {
    const modelRaw = parts[0];
    const dataset = parts[1];
    const task = parts.slice(2).join('_');
    
    trajectory.modelName = getModelDisplayName(modelRaw);
    trajectory.taskName = `${dataset} ${task}`.replace(/[_-]+/g, ' ')
      .trim()
      .split(' ')
      .filter(Boolean)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  } else if (parts.length >= 2) {
    trajectory.taskName = parts[parts.length - 1];
    trajectory.modelName = getModelDisplayName(parts[0]);
  }

  trajectory.steps.push({
    type: "oracle_null_run",
    content: trajectory.modelName === 'Oracle' 
      ? "Oracle run: Applied golden solution diff directly" 
      : "Nullagent run: No implementation attempted",
    iteration: 0,
    success: true,
    timestamp: extractTimestamp(content),
  });

  const testResults = parseTestResults(content);
  trajectory.testResults = testResults;
  trajectory.testsPassed = testResults.filter(t => t.status === 'pass').length;
  trajectory.totalTests = testResults.length;
  trajectory.labTrainingMetrics = parseLabTrainingMetrics(content);
  trajectory.finalSuccess = determineFinalSuccess(content);
  trajectory.duration = extractDuration(content);
  trajectory.finalDiffs = extractDiffs(content);

  return trajectory;
}

function parseLogFile(filename: string, content: string): Trajectory {
  const trajectory: Trajectory = {
    filename,
    taskName: "unknown",
    modelName: "unknown",
    totalIterations: 0,
    toolCalls: 0,
    errors: 0,
    testsPassed: 0,
    totalTests: 0,
    finalSuccess: false,
    steps: [],
    finalDiffs: null,
    testResults: [],
  };

  const isOracleOrNull = filename.startsWith('oracle_') || filename.startsWith('nullagent_') || !content.includes('HARNESS:');
  
  if (isOracleOrNull) {
    return parseOracleOrNullLog(trajectory, filename, content);
  }

  const filenameWithoutExt = filename.replace(/\.log$/i, '');
  const parts = filenameWithoutExt.split('_');
  
  if (parts.length >= 3) {
    const modelRaw = parts[0];
    const dataset = parts[1];
    const task = parts.slice(2).join('_');
    
    trajectory.modelName = getModelDisplayName(modelRaw);
    trajectory.taskName = `${dataset} ${task}`.replace(/[_-]+/g, ' ')
      .trim()
      .split(' ')
      .filter(Boolean)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  } else if (parts.length >= 2) {
    trajectory.taskName = parts[parts.length - 1];
    trajectory.modelName = getModelDisplayName(parts[0]);
  }

  const lines = content.split("\n");
  let currentIteration: number | null = null;
  let currentStep: TrajectoryStep | null = null;
  let collectingToolResult = false;
  let toolResultBuffer: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    if (line.includes("Starting benchmark run")) {
      const datePattern = /\d{4}-\d{2}-\d{2}/;
      const dateMatch = line.match(datePattern);
      const timestamp = dateMatch ? dateMatch[0] : extractTimestamp(line);

      trajectory.steps.push({
        type: "start",
        content: "Starting benchmark run",
        iteration: 0,
        success: true,
        timestamp: timestamp,
      });
    } else if (line.includes("Dataset:") && line.includes("Agent:") && line.includes("Model:")) {
      const parts = line.split(",");
      for (const part of parts) {
        if (part.includes("Model:")) {
          trajectory.modelName = part.split("Model:")[1].trim();
        } else if (part.includes("Task:")) {
          trajectory.taskName = part.split("Task:")[1].trim();
        }
      }
    } else if (line.includes("HARNESS: Iteration") && line.includes("making LLM call")) {
      const match = line.match(/Iteration (\d+)/);
      if (match) {
        currentIteration = parseInt(match[1], 10);
        trajectory.totalIterations = Math.max(
          trajectory.totalIterations,
          currentIteration
        );
      }
    } else if (line.includes("HARNESS: Tool call") && currentIteration !== null) {
      const toolMatch = line.match(/Tool call \d+: (\w+)/);
      if (toolMatch) {
        const toolName = toolMatch[1];
        trajectory.toolCalls += 1;

        currentStep = {
          type: "iteration",
          iteration: currentIteration,
          toolCall: toolName,
          success: null,
          content: `Executing ${toolName}`,
          error: null,
          toolDetails: {},
          toolResult: [],
          timestamp: extractTimestamp(line),
        };
        trajectory.steps.push(currentStep);
        collectingToolResult = false;
        toolResultBuffer = [];
      }
    } else if (currentStep && line.includes("HARNESS: Edit target:")) {
      const target = line.split("HARNESS: Edit target:")[1]?.trim();
      if (target) {
        currentStep.toolDetails = currentStep.toolDetails || {};
        currentStep.toolDetails.editTarget = target;
      }
    } else if (currentStep && line.includes("HARNESS: Edit instructions:")) {
      const instructions = line.split("HARNESS: Edit instructions:")[1]?.trim();
      if (instructions) {
        currentStep.toolDetails = currentStep.toolDetails || {};
        currentStep.toolDetails.editInstructions = instructions;
      }
    } else if (currentStep && line.includes("HARNESS: Line edits count:")) {
      const count = line.split("HARNESS: Line edits count:")[1]?.trim();
      if (count) {
        currentStep.toolDetails = currentStep.toolDetails || {};
        currentStep.toolDetails.lineEditsCount = count;
      }
    } else if (currentStep && line.match(/HARNESS: Edit \d+:/)) {
      const editInfo = line.split(/HARNESS: Edit \d+:/)[1]?.trim();
      if (editInfo) {
        currentStep.toolDetails = currentStep.toolDetails || {};
        currentStep.toolDetails.edits = currentStep.toolDetails.edits || [];
        currentStep.toolDetails.edits.push(editInfo);
      }
    } else if (currentStep && line.includes("HARNESS: Python syntax validation passed")) {
      currentStep.toolDetails = currentStep.toolDetails || {};
      currentStep.toolDetails.syntaxValidation = "passed";
    } else if (currentStep && line.includes("HARNESS: Python syntax error")) {
      const errorMsg = line.split("HARNESS: Python syntax error in")[1]?.trim();
      currentStep.toolDetails = currentStep.toolDetails || {};
      currentStep.toolDetails.syntaxValidation = "failed";
      currentStep.toolDetails.syntaxError = errorMsg || "Syntax error detected";
    } else if (currentStep && line.includes("HARNESS: SYNTAX ERROR at line")) {
      const errorDetail = line.split("HARNESS: SYNTAX ERROR at line")[1]?.trim();
      if (errorDetail) {
        currentStep.toolDetails = currentStep.toolDetails || {};
        currentStep.toolDetails.syntaxErrorDetail = errorDetail;
      }
    } else if (currentStep && line.includes("HARNESS: Changes applied:")) {
      const changes = line.split("HARNESS: Changes applied:")[1]?.trim();
      if (changes) {
        try {
          const parsed = JSON.parse(changes);
          currentStep.toolDetails = currentStep.toolDetails || {};
          currentStep.toolDetails.changesApplied = parsed;
        } catch {
          currentStep.toolDetails = currentStep.toolDetails || {};
          currentStep.toolDetails.changesApplied = changes;
        }
      }
    } else if (currentStep && line.includes("HARNESS: Changes that would have been applied:")) {
      const changes = line.split("HARNESS: Changes that would have been applied:")[1]?.trim();
      if (changes) {
        try {
          const parsed = JSON.parse(changes);
          currentStep.toolDetails = currentStep.toolDetails || {};
          currentStep.toolDetails.changesNotApplied = parsed;
        } catch {
          currentStep.toolDetails = currentStep.toolDetails || {};
          currentStep.toolDetails.changesNotApplied = changes;
        }
      }
    } else if (currentStep && line.includes("HARNESS: Attempted changes:")) {
      const changes = line.split("HARNESS: Attempted changes:")[1]?.trim();
      if (changes) {
        try {
          const parsed = JSON.parse(changes);
          currentStep.toolDetails = currentStep.toolDetails || {};
          currentStep.toolDetails.attemptedChanges = parsed;
        } catch {
          currentStep.toolDetails = currentStep.toolDetails || {};
          currentStep.toolDetails.attemptedChanges = changes;
        }
      }
    } else if (currentStep && line.includes("HARNESS: Writing") && line.includes("characters to")) {
      const match = line.match(/Writing (\d+) characters to (.+)/);
      if (match) {
        currentStep.toolDetails = currentStep.toolDetails || {};
        currentStep.toolDetails.bytesWritten = match[1];
        currentStep.toolDetails.filePath = match[2];
      }
    } else if (collectingToolResult && currentStep && line) {
      toolResultBuffer.push(line);
      currentStep.toolResult = [...toolResultBuffer];
    } else if (line.includes("Tool 0 result success:") && currentStep) {
      const successMatch = line.match(/Tool 0 result success: (\w+)/);
      if (successMatch) {
        const isSuccess = successMatch[1].toLowerCase() === "true";
        currentStep.success = isSuccess;
        if (!isSuccess) {
          trajectory.errors += 1;
        }
        collectingToolResult = true;
        toolResultBuffer = [];
      }
    } else if (line.toUpperCase().includes("ERROR") && currentStep) {
      if (!currentStep.error) {
        currentStep.error = line;
        trajectory.errors += 1;
      }
    }
  }

  const testResults = parseTestResults(content);
  trajectory.testResults = testResults;
  trajectory.testsPassed = testResults.filter(t => t.status === 'pass').length;
  trajectory.totalTests = testResults.length;
  trajectory.labTrainingMetrics = parseLabTrainingMetrics(content);
  trajectory.finalSuccess = determineFinalSuccess(content);
  trajectory.duration = extractDuration(content);
  trajectory.finalDiffs = extractDiffs(content);

  return trajectory;
}

function parseTestResults(content: string): TestResult[] {
  const testResults: TestResult[] = [];
  const lines = content.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

  
    const passMatch = line.match(/pass\s+(.+?)::(.+?):\s+PASSED/);
    const failMatch = line.match(/fail\s+(.+?)::(.+?):\s+FAILED/);

    const passStartMatch = line.match(/pass\s+(.+?)::(.+?):\s*$/);
    const failStartMatch = line.match(/fail\s+(.+?)::(.+?):\s*$/);
    const passOnlyMatch = line.match(/^pass\s*$/);
    const failOnlyMatch = line.match(/^fail\s*$/);

    if (passMatch) {
      const [, filePath, testName] = passMatch;
      testResults.push({
        name: testName,
        status: 'pass',
        fullName: `${filePath}::${testName}`
      });
    } else if (failMatch) {
      const [, filePath, testName] = failMatch;
      testResults.push({
        name: testName,
        status: 'fail',
        fullName: `${filePath}::${testName}`
      });
    } else if (passStartMatch && i + 1 < lines.length) {
      // Check if next line has PASSED
      const nextLine = lines[i + 1].trim();
      if (nextLine === 'PASSED') {
        const [, filePath, testName] = passStartMatch;
        testResults.push({
          name: testName,
          status: 'pass',
          fullName: `${filePath}::${testName}`
        });
        i++; // Skip the next line since we processed it
      }
    } else if (failStartMatch && i + 1 < lines.length) {
      const nextLine = lines[i + 1].trim();
      if (nextLine === 'FAILED') {
        const [, filePath, testName] = failStartMatch;
        testResults.push({
          name: testName,
          status: 'fail',
          fullName: `${filePath}::${testName}`
        });
        i++;
      }
    } else if (passOnlyMatch && i + 1 < lines.length) {
      let fullTestPath = '';
      let j = i + 1;
      let foundEnd = false;

      while (j < lines.length && j < i + 4) {
        const nextLine = lines[j].trim();

        if (nextLine === 'pass' || nextLine === 'fail') {
          break;
        }

        if (nextLine.includes(': PASSED')) {
          fullTestPath += nextLine.replace(': PASSED', '');
          foundEnd = true;
          break;
        } else if (nextLine === 'PASSED') {
          foundEnd = true;
          break;
        } else if (nextLine.includes('::')) {
          fullTestPath += nextLine;
        } else if (nextLine.length > 0 && !nextLine.includes('FAILED')) {
          fullTestPath += nextLine;
        }
        j++;
      }

      if (foundEnd && fullTestPath.includes('::')) {
        const parts = fullTestPath.split('::');
        if (parts.length >= 2) {
          const filePath = parts[0];
          const testName = parts.slice(1).join('::');
          testResults.push({
            name: testName,
            status: 'pass',
            fullName: `${filePath}::${testName}`
          });
          i = j;
        }
      }
    } else if (failOnlyMatch && i + 1 < lines.length) {
      // Look ahead to reconstruct the full test path across multiple lines
      let fullTestPath = '';
      let j = i + 1;
      let foundEnd = false;

      // Collect lines until we find ": FAILED" or hit another "pass"/"fail"
      while (j < lines.length && j < i + 4) { // Limit search to avoid infinite loop
        const nextLine = lines[j].trim();

        // Stop if we hit another pass/fail directive
        if (nextLine === 'pass' || nextLine === 'fail') {
          break;
        }

        if (nextLine.includes(': FAILED')) {
          fullTestPath += nextLine.replace(': FAILED', '');
          foundEnd = true;
          break;
        } else if (nextLine === 'FAILED') {
          // Found standalone FAILED, previous lines form the test path
          foundEnd = true;
          break;
        } else if (nextLine.includes('::')) {
          fullTestPath += nextLine;
        } else if (nextLine.length > 0 && !nextLine.includes('PASSED')) {
          fullTestPath += nextLine;
        }
        j++;
      }

      if (foundEnd && fullTestPath.includes('::')) {
        const parts = fullTestPath.split('::');
        if (parts.length >= 2) {
          const filePath = parts[0];
          const testName = parts.slice(1).join('::');
          testResults.push({
            name: testName,
            status: 'fail',
            fullName: `${filePath}::${testName}`
          });
          i = j;
        }
      }
    }
  }

  return testResults;
}

function parseLabTrainingMetrics(content: string): any {
  const metrics: any = {};
  const lines = content.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Parse Lab Training Metrics section
    if (line.includes('-- Lab Training Metrics --')) {
      // Parse the following lines for metrics
      for (let j = i + 1; j < Math.min(i + 20, lines.length); j++) {
        const metricLine = lines[j].trim();

        if (metricLine.includes('Tests Passed:')) {
          metrics.testsPassed = metricLine.includes('True');
        } else if (metricLine.includes('Agent Success:')) {
          metrics.agentSuccess = metricLine.includes('True');
        } else if (metricLine.includes('Code Changes Made:')) {
          metrics.codeChangesMade = metricLine.includes('True');
        } else if (metricLine.includes('No Syntax Errors:')) {
          metrics.noSyntaxErrors = metricLine.includes('True');
        } else if (metricLine.includes('Conversation Length:')) {
          const match = metricLine.match(/Conversation Length:\s*(\d+)/);
          if (match) metrics.conversationLength = parseInt(match[1], 10);
        } else if (metricLine.includes('Successful Edits:')) {
          const match = metricLine.match(/Successful Edits:\s*(\d+)/);
          if (match) metrics.successfulEdits = parseInt(match[1], 10);
        } else if (metricLine.includes('Final Code Files:')) {
          const match = metricLine.match(/Final Code Files:\s*(\d+)/);
          if (match) metrics.finalCodeFiles = parseInt(match[1], 10);
        } else if (metricLine.includes('-- Details --')) {
          break; // End of metrics section
        }
      }
      break;
    }
  }

  return Object.keys(metrics).length > 0 ? metrics : undefined;
}

function determineFinalSuccess(content: string): boolean {
  // Look for "Total tests: X/Y passed" pattern (use LAST occurrence)
  const totalTestsRegex = /Total\s+tests:\s*(\d+)\/(\d+)\s*passed/gi;
  let match;
  let lastPassed: number | null = null;
  let lastTotal: number | null = null;

  while ((match = totalTestsRegex.exec(content)) !== null) {
    lastPassed = parseInt(match[1], 10);
    lastTotal = parseInt(match[2], 10);
  }

  if (lastPassed !== null && lastTotal !== null) {
    if (lastTotal > 0) return lastPassed === lastTotal;
    return false;
  }

  // Fallback: look for "Passed X/Y tests" pattern
  const passedLineRegex = /Passed\s*(\d+)\/(\d+)\s*tests/gi;
  let pMatch;
  let pPassed: number | null = null;
  let pTotal: number | null = null;

  while ((pMatch = passedLineRegex.exec(content)) !== null) {
    pPassed = parseInt(pMatch[1], 10);
    pTotal = parseInt(pMatch[2], 10);
  }

  if (pPassed !== null && pTotal !== null) {
    if (pTotal > 0) return pPassed === pTotal;
    return false;
  }

  // If no test results found, default to false
  return false;
}

function extractDuration(content: string): string | undefined {
  // Look for "Total duration: XXm YYs" pattern
  const durationRegex = /Total\s+duration:\s*([^\n]+)/i;
  const match = content.match(durationRegex);
  if (match && match[1]) {
    return match[1].trim();
  }
  return undefined;
}

function extractDiffs(content: string): any {
  try {
    let agentDiff: string | null = null;
    let goldenDiff: string | null = null;
    let filesChanged: string[] = [];

    // Look for agent diff (using [\s\S] instead of . with /s flag)
    const agentDiffMatch = content.match(
      /'agent_diff':\s*'([^']*(?:\\'[^']*)*)'/
    );
    if (agentDiffMatch) {
      agentDiff = agentDiffMatch[1]
        .replace(/\\'/g, "'")
        .replace(/\\n/g, "\n")
        .replace(/\\t/g, "\t");
    }

    // Look for golden diff
    const goldenDiffMatch = content.match(
      /'golden_diff':\s*'([^']*(?:\\'[^']*)*)'/
    );
    if (goldenDiffMatch) {
      goldenDiff = goldenDiffMatch[1]
        .replace(/\\'/g, "'")
        .replace(/\\n/g, "\n")
        .replace(/\\t/g, "\t");
    }

    // Extract files changed
    if (agentDiff) {
      const fileMatches = agentDiff.matchAll(/--- a\/(.*?)\n\+\+\+ b\//g);
      filesChanged = Array.from(new Set(Array.from(fileMatches).map((m) => m[1])));
    }

    const diffStats = {
      agentFilesChanged: filesChanged.length,
      goldenFilesChanged: goldenDiff ? 1 : 0,
      agentLines: agentDiff ? agentDiff.split("\n").length : 0,
      goldenLines: goldenDiff ? goldenDiff.split("\n").length : 0,
    };

    return {
      agentDiff,
      goldenDiff,
      filesChanged,
      diffStats,
    };
  } catch (error) {
    console.error("Error extracting diffs:", error);
    return null;
  }
}

function extractTimestamp(line: string): string {
  const patterns = [
    /\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}/,
    /\d{2}:\d{2}:\d{2}/,
  ];

  for (const pattern of patterns) {
    const match = line.match(pattern);
    if (match) {
      return match[0];
    }
  }

  return "N/A";
}

function extractTaskName(filename: string): string | null {
  // Extract task name from universal filename format: model_dataset_task.log
  const filenameWithoutExt = filename.replace(/\.log$/i, '');
  const parts = filenameWithoutExt.split('_');
  
  if (parts.length >= 3) {
    // Format: model_dataset_task -> return dataset_task
    return parts.slice(1).join('_');
  } else if (parts.length >= 2) {
    // Fallback: model_task -> return task
    return parts[1];
  }
  
  return null;
}
