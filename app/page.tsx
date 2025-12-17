'use client';

import { useEffect, useState } from 'react';
import { getModelDisplayName, getModelConfigs, MODEL_CONFIGS, MODEL_DISPLAY_ORDER } from './config/models';

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
      const trimmed = line.trim();
      const harnessPattern = /^.?\s*HARNESS:/;
      const gitAddErrorPattern = /HARNESS:\s*Git add failed:\s*Unknown error/i;
      return !harnessPattern.test(trimmed) && !gitAddErrorPattern.test(trimmed);
    });
  };

  const extractGradingMetrics = (lines: string[]) => {
    const gradingPatterns = [
      /Total tests:\s*\d+\/\d+\s*passed/i,
      /Total duration:\s*.+/i,
      /Lab Training Outcome:\s*(FAILURE|SUCCESS)\s*\(binary\)/i,
      /GRADER:\s*Agent diff length:\s*\d+\s*chars/i
    ];

    return lines.filter(line => {
      return gradingPatterns.some(pattern => pattern.test(line.trim()));
    });
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


  const NUM_TURNS = 60

  const isOracle = trajectory.modelName === 'oracle';
  const isNullAgent = trajectory.modelName === 'nullagent';


  if (isNullAgent) {
    return (
      <div className="space-y-6">
        <div className="text-center p-6 text-gray-600">
          <h3 className="text-lg font-medium">Null Agent (Baseline)</h3>
          <p className="text-sm mt-2">Baseline agent (1 test for dependencies and version check).</p>
          <div className="mt-4 inline-flex items-center space-x-4 text-xs">
            <span className="bg-gray-100 px-3 py-1 rounded">Tests: {trajectory.testsPassed}/{trajectory.totalTests}</span>
            <span className={`px-3 py-1 rounded ${trajectory.finalSuccess ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              {trajectory.finalSuccess ? 'PASS' : 'FAIL'}
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="font-semibold text-lg mb-3">Execution Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="text-center p-3 bg-white rounded border">
            <div className="text-lg font-bold">{trajectory.totalIterations}/{NUM_TURNS}</div>
            <div className="text-xs text-gray-600">Turns</div>
          </div>
          <div className="text-center p-3 bg-white rounded border">
            <div className="text-lg font-bold">{trajectory.errors}</div>
            <div className="text-xs text-gray-600">Errors</div>
          </div>
          {trajectory.duration && (
            <div className="text-center p-3 bg-white rounded border">
              <div className="text-lg font-bold">{trajectory.duration}</div>
              <div className="text-xs text-gray-600">Duration</div>
            </div>
          )}
          <div className="text-center p-3 bg-white rounded border">
            <div className={`text-lg font-bold ${
              trajectory.testResults.length > 0
                ? (trajectory.testsPassed === trajectory.totalTests && trajectory.totalTests > 0 ? 'text-green-600' : 'text-red-600')
                : (finalTests && finalTests.passed === finalTests.total && finalTests.total > 0 ? 'text-green-600' : 'text-red-600')
            }`}>
              {trajectory.testResults.length > 0 ? `${trajectory.testsPassed}/${trajectory.totalTests}` : (finalTests ? `${finalTests.passed}/${finalTests.total}` : 'N/A')}
            </div>
            <div className="text-xs text-gray-600">Tests</div>
          </div>
          <div className="text-center p-3 bg-white rounded border">
            <div className={`text-lg font-bold ${(trajectory.testResults.length > 0 ? trajectory.testsPassed === trajectory.totalTests : trajectory.finalSuccess) ? 'text-green-600' : 'text-red-600'}`}>
              {(trajectory.testResults.length > 0 ? trajectory.testsPassed === trajectory.totalTests : trajectory.finalSuccess) ? 'PASS' : 'FAIL'}
            </div>
            <div className="text-xs text-gray-600">Result</div>
          </div>
        </div>
      </div>

      {trajectory.testResults && trajectory.testResults.length > 0 && (
        <div>
          <h3 className="font-semibold text-lg mb-3">Test Results</h3>
          <div className="grid gap-2">
            {trajectory.testResults.map((test, index) => (
              <div key={index} className={`p-3 rounded-lg border flex items-center justify-between ${
                test.status === 'pass'
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}>
                <div className="flex items-center space-x-3">
                  {test.status === 'pass' ? (
                    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  )}
                  <div>
                    <div className={`font-medium ${test.status === 'pass' ? 'text-green-800' : 'text-red-800'}`}>
                      {test.name}
                    </div>
                  </div>
                </div>
                <span className={`px-3 py-1 text-xs font-semibold rounded-full ${
                  test.status === 'pass'
                    ? 'bg-green-500 text-white'
                    : 'bg-red-500 text-white'
                }`}>
                  {test.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {((trajectory.testResults.length === 0 && finalTests && finalTests.passed === 0 && finalTests.total === 1) ||
        (trajectory.testResults.length === 0 && trajectory.testsPassed === 0 && trajectory.totalTests === 1)) && (
        <div>
          <h3 className="font-semibold text-lg mb-3">Test Collection Error (0/1)</h3>
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start space-x-3">
              <div>
                <div className="font-medium text-amber-800 mb-1">Import Error During Test Collection</div>
                <div className="text-sm text-amber-700">
                  When parser tries to import the test file, it hits a ModuleNotFoundError before it can discover any of the test functions,
                  so parser reports "1 error during collection" (the import failure itself) instead of collecting the individual tests.
                  The "0/1" means 0 passed out of 1 collected item (the collection error) because the tests were never
                  successfully loaded into parser's test collection. <strong>This is considered a fail.</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {trajectory.labTrainingMetrics && (
        <div>
          <h3 className="font-semibold text-lg mb-3">Binary Metrics</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="text-center p-3 bg-white rounded border">
              <div className={`text-lg font-bold ${trajectory.labTrainingMetrics.testsPassed ? 'text-green-600' : 'text-red-600'}`}>
                {trajectory.labTrainingMetrics.testsPassed ? 'YES' : 'NO'}
              </div>
              <div className="text-xs text-gray-600">Tests Passed</div>
            </div>
            <div className="text-center p-3 bg-white rounded border">
              <div className={`text-lg font-bold ${trajectory.labTrainingMetrics.agentSuccess ? 'text-green-600' : 'text-red-600'}`}>
                {trajectory.labTrainingMetrics.agentSuccess ? 'YES' : 'NO'}
              </div>
              <div className="text-xs text-gray-600">Agent Success</div>
            </div>
            <div className="text-center p-3 bg-white rounded border">
              <div className={`text-lg font-bold ${trajectory.labTrainingMetrics.codeChangesMade ? 'text-green-600' : 'text-red-600'}`}>
                {trajectory.labTrainingMetrics.codeChangesMade ? 'YES' : 'NO'}
              </div>
              <div className="text-xs text-gray-600">Code Changes</div>
            </div>
            <div className="text-center p-3 bg-white rounded border">
              <div className={`text-lg font-bold ${trajectory.labTrainingMetrics.noSyntaxErrors ? 'text-green-600' : 'text-red-600'}`}>
                {trajectory.labTrainingMetrics.noSyntaxErrors ? 'YES' : 'NO'}
            </div>
              <div className="text-xs text-gray-600">No Syntax Errors</div>
          </div>
            {trajectory.labTrainingMetrics.conversationLength && (
              <div className="text-center p-3 bg-white rounded border">
                <div className="text-lg font-bold">{trajectory.labTrainingMetrics.conversationLength}</div>
                <div className="text-xs text-gray-600">Conversation Length</div>
            </div>
            )}
            {trajectory.labTrainingMetrics.successfulEdits && (
              <div className="text-center p-3 bg-white rounded border">
                <div className="text-lg font-bold">{trajectory.labTrainingMetrics.successfulEdits}</div>
                <div className="text-xs text-gray-600">Successful Edits</div>
              </div>
                )}
            {trajectory.labTrainingMetrics.finalCodeFiles && (
              <div className="text-center p-3 bg-white rounded border">
                <div className="text-lg font-bold">{trajectory.labTrainingMetrics.finalCodeFiles}</div>
                <div className="text-xs text-gray-600">Final Code Files</div>
              </div>
            )}
              </div>
        </div>
      )}

      {stepsToShow && stepsToShow.length > 0 && (
        <div>
          <h3 className="font-semibold text-lg mb-3">Execution Steps</h3>
          <div className="space-y-3 max-h-[48rem] overflow-y-auto">
             {stepsToShow.map((step, index) => {
               const hasUsefulToolResult = step.toolResult && step.toolResult.length > 0 && (() => {
                 const isLastStep = index === stepsToShow.length - 1;
                 if (isLastStep) {
                   const gradingLines = extractGradingMetrics(step.toolResult);
                   return gradingLines.length > 0;
                 } else {
                   const filteredLines = filterHarnessMessages(step.toolResult);
                   return filteredLines.length > 0;
                 }
               })();

               const hasMeaningfulError = step.error &&
                 !step.error.toString().includes('HARNESS: Git add failed: Unknown error');

               const hasExpandableContent =
                 (step.toolDetails && Object.keys(step.toolDetails).length > 0) ||
                 hasUsefulToolResult ||
                 hasMeaningfulError;

               return (
              <div key={index} className="border rounded-lg bg-white">
                <div
                   className={`flex items-center justify-between p-3 ${hasExpandableContent ? 'cursor-pointer hover:bg-gray-50' : ''}`}
                   onClick={() => hasExpandableContent && toggleStep(index)}
                >
                  <div className="flex items-center space-x-3">
                     {hasExpandableContent && (
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
                     )}
                     {!hasExpandableContent && <div className="w-4" />}
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

                {hasExpandableContent && expandedSteps.has(index) && (
                  <div className="p-4 bg-gray-50 border-t">
                    {step.toolDetails && step.toolDetails.editTarget && (
                      <div className="mb-4 bg-white rounded-lg border border-gray-200 overflow-hidden">
                        <div className="bg-gradient-to-r from-blue-50 to-blue-100 px-4 py-2 border-b border-blue-200">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                              </svg>
                              <span className="font-semibold text-sm text-blue-900">File Edit</span>
                        </div>
                            {step.toolDetails.syntaxValidation && (
                              <span className={`text-xs px-2 py-1 rounded-full font-semibold ${
                                step.toolDetails.syntaxValidation === 'passed'
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-red-100 text-red-700'
                              }`}>
                                {step.toolDetails.syntaxValidation === 'passed' ? '✓ Valid' : '✗ Syntax Error'}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="p-4 space-y-4">
                          <div>
                            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Target File</div>
                            <div className="text-sm font-mono text-blue-700 bg-blue-50 px-2 py-1 rounded">{step.toolDetails.editTarget}</div>
                          </div>

                          {step.toolDetails.editInstructions && (
                            <div>
                              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Instructions</div>
                              <div className="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded">{step.toolDetails.editInstructions}</div>
                      </div>
                    )}

                          {step.toolDetails.lineEditsCount && (
                            <div className="flex items-center space-x-4">
                              <div>
                                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Line Edits</div>
                                <div className="text-sm font-bold text-gray-900">{step.toolDetails.lineEditsCount}</div>
                              </div>
                              {step.toolDetails.bytesWritten && (
                                <div>
                                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Bytes Written</div>
                                  <div className="text-sm font-bold text-gray-900">{step.toolDetails.bytesWritten}</div>
                                </div>
                              )}
                      </div>
                    )}

                          {step.toolDetails.edits && step.toolDetails.edits.length > 0 && (
                            <div>
                              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Operations</div>
                              <div className="space-y-1">
                                {step.toolDetails.edits.map((edit: string, i: number) => (
                                  <div key={i} className="text-xs font-mono text-gray-700 bg-gray-100 px-2 py-1 rounded border border-gray-200">
                                    {edit}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {step.toolDetails.syntaxErrorDetail && (
                            <div className="bg-red-50 border border-red-200 rounded p-3">
                              <div className="text-xs font-semibold text-red-700 mb-1">Syntax Error</div>
                              <div className="text-xs font-mono text-red-800">{step.toolDetails.syntaxErrorDetail}</div>
                            </div>
                          )}

                          {step.toolDetails.changesApplied && (
                            <div className="bg-green-50 border border-green-300 rounded p-3">
                              <div className="text-xs font-semibold text-green-700 mb-2 flex items-center">
                                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                Changes Applied
                              </div>
                              <div className="space-y-1">
                                {Array.isArray(step.toolDetails.changesApplied) ? (
                                  step.toolDetails.changesApplied.map((change: string, i: number) => (
                                    <div key={i} className="text-xs font-mono text-green-800 bg-white px-2 py-1 rounded border border-green-200">
                                      {change}
                                    </div>
                                  ))
                                ) : (
                                  <div className="text-xs font-mono text-green-800">{step.toolDetails.changesApplied}</div>
                                )}
                              </div>
                            </div>
                          )}

                          {step.toolDetails.changesNotApplied && (
                            <div className="bg-amber-50 border border-amber-300 rounded p-3">
                              <div className="text-xs font-semibold text-amber-700 mb-2">Changes Not Applied</div>
                              <div className="space-y-1">
                                {Array.isArray(step.toolDetails.changesNotApplied) ? (
                                  step.toolDetails.changesNotApplied.map((change: string, i: number) => (
                                    <div key={i} className="text-xs font-mono text-amber-800 bg-white px-2 py-1 rounded border border-amber-200">
                                      {change}
                                    </div>
                                  ))
                                ) : (
                                  <div className="text-xs font-mono text-amber-800">{step.toolDetails.changesNotApplied}</div>
                                )}
                              </div>
                            </div>
                          )}

                          {step.toolDetails.attemptedChanges && (
                            <div className="bg-red-50 border border-red-300 rounded p-3">
                              <div className="text-xs font-semibold text-red-700 mb-2">Attempted Changes (Failed)</div>
                              <div className="space-y-1">
                                {Array.isArray(step.toolDetails.attemptedChanges) ? (
                                  step.toolDetails.attemptedChanges.map((change: string, i: number) => (
                                    <div key={i} className="text-xs font-mono text-red-800 bg-white px-2 py-1 rounded border border-red-200">
                                      {change}
                                    </div>
                                  ))
                                ) : (
                                  <div className="text-xs font-mono text-red-800">{step.toolDetails.attemptedChanges}</div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {step.toolResult && step.toolResult.length > 0 && (() => {
                      const isLastStep = index === stepsToShow.length - 1;

                      let linesToShow;
                      if (isLastStep) {
                        linesToShow = extractGradingMetrics(step.toolResult);
                      } else {
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

                    {step.error && !step.error.toString().includes('HARNESS: Git add failed: Unknown error') && (
                      <div className="mb-4">
                        <h4 className="font-medium text-sm mb-2 text-red-600">Error:</h4>
                        <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                          <pre className="whitespace-pre-wrap">
                            {typeof step.error === 'string' ? step.error : JSON.stringify(step.error, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}

                    {!step.toolDetails && !step.toolResult && !(step.error && !step.error.toString().includes('HARNESS: Git add failed: Unknown error')) && (
                      <div className="text-gray-500 text-sm">No additional details</div>
                    )}
                  </div>
                )}
              </div>
              );
            })}
          </div>
        </div>
      )}

      {trajectory.finalDiffs && trajectory.finalDiffs.agentDiff && (
        <div>
          <h3 className="font-semibold text-lg mb-3">Agent Solution</h3>

          <div className="grid grid-cols-1 gap-3 mb-4">
            <div className="text-center p-3 bg-white rounded border">
              <div className="text-lg font-bold text-blue-600">{trajectory.finalDiffs.diffStats.agentLines}</div>
              <div className="text-xs text-gray-600">Agent Diff Lines</div>
            </div>
          </div>

          <div className="border rounded-lg overflow-hidden bg-white">
            <div className="bg-blue-600 text-white p-3 text-center font-semibold">Agent Implementation</div>
            <div className="p-4 bg-gray-50 overflow-auto max-h-96">
              <pre className="text-xs font-mono whitespace-pre-wrap">{formatDiff(trajectory.finalDiffs.agentDiff)}</pre>
            </div>
          </div>

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

export default function IdeArenaPage() {
  const [logs, setLogs] = useState<LogFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modelPassRates, setModelPassRates] = useState<Map<string, ModelCounts>>(new Map());
  const [modelTestCaseRates, setModelTestCaseRates] = useState<Map<string, ModelCounts>>(new Map());
  const [metricsViewMode, setMetricsViewMode] = useState<'tasks' | 'testcases'>('tasks');
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [trajectories, setTrajectories] = useState<Map<string, any>>(new Map());
  const [selectedModelByTaskId, setSelectedModelByTaskId] = useState<Map<string, string>>(new Map());
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());

  function toggleFileExpanded(filename: string) {
    const newExpanded = new Set(expandedFiles);
    if (expandedFiles.has(filename)) {
      newExpanded.delete(filename);
    } else {
      newExpanded.add(filename);
    }
    setExpandedFiles(newExpanded);
  }

  useEffect(() => {
    loadLogFiles();
  }, []);

  async function loadLogFiles() {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/idearena/logs');

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to load logs: ${response.status} - ${errorText}`);
      }

      const logsData: LogFile[] = await response.json();

      setLogs(logsData);
      await computeModelPassRates(logsData);
      try {
        await computeModelTestCaseRates(logsData);
      } catch (error) {
        console.error('Error computing test case rates:', error);
      }
      setLoading(false);
    } catch (err: any) {
      console.error('Error loading logs:', err);
      setError(err.message);
      setLoading(false);
    }
  }

  async function computeModelPassRates(logsData: LogFile[]) {
    const discoveredModels = new Set<string>();
    logsData.forEach(log => {
      const parsed = parseTrajectoryFilename(log.filename);
      discoveredModels.add(parsed.model);
    });

    const counts = new Map(
      Array.from(discoveredModels).map(m => [m, { pass: 0, fail: 0, total: 0 }])
    );

    const mainAgentLogs = logsData;

    const results = await Promise.all(
      mainAgentLogs.map(async (log) => {
        try {
          // Use trajectory API to get accurate test parsing
          const res = await fetch(`/api/idearena/trajectory/${encodeURIComponent(log.filename)}`);
          if (!res.ok) {
            return null;
          }
          const trajectory = await res.json();

          let taskSuccess = false;
          if (trajectory.testResults && trajectory.testResults.length > 0) {
            taskSuccess = trajectory.testsPassed === trajectory.totalTests && trajectory.totalTests > 0;
          } else {
            taskSuccess = trajectory.finalSuccess === true;
          }

          return { filename: log.filename, taskSuccess };
        } catch (error) {
          console.error(`Error processing ${log.filename}:`, error);
          return null;
        }
      })
    );

    for (const r of results) {
      if (!r) continue;
      const parsed = parseTrajectoryFilename(r.filename);
      if (!counts.has(parsed.model)) continue;
      const entry = counts.get(parsed.model)!;
      entry.total += 1;
      if (r.taskSuccess) entry.pass += 1;
      else entry.fail += 1;
    }

    setModelPassRates(counts);
  }

  async function computeModelTestCaseRates(logsData: LogFile[]) {
    // First pass: collect all models present in the logs
    const discoveredModels = new Set<string>();
    logsData.forEach(log => {
      const parsed = parseTrajectoryFilename(log.filename);
      discoveredModels.add(parsed.model);
    });

    const counts = new Map(
      Array.from(discoveredModels).map(m => [m, { pass: 0, fail: 0, total: 0 }])
    );

    const mainAgentLogs = logsData; // Include all logs, not just main agents

    console.log(`Computing test case rates for ${mainAgentLogs.length} main agent log files...`);

    const results = await Promise.all(
      mainAgentLogs.map(async (log) => {
        try {
          const res = await fetch(`/api/idearena/trajectory/${encodeURIComponent(log.filename)}`);
          if (!res.ok) {
            return null;
          }
          const trajectory = await res.json();

          let adjustedPassed = 0;
          let adjustedTotal = 0;
          if (trajectory.testResults && trajectory.testResults.length > 0) {
            adjustedPassed = Math.max(0, trajectory.testsPassed - 1);
            adjustedTotal = Math.max(1, trajectory.totalTests - 1);
          } else if (trajectory.finalSuccess !== undefined) {
            adjustedPassed = 0;
            adjustedTotal = 1;
          }

          return { filename: log.filename, adjustedPassed, adjustedTotal };
        } catch (error) {
          console.error(`Error processing ${log.filename}:`, error);
          return null;
        }
      })
    );

    for (const r of results) {
      if (!r) continue;
      const parsed = parseTrajectoryFilename(r.filename);
      if (!counts.has(parsed.model)) continue;
      const entry = counts.get(parsed.model)!;
      entry.pass += r.adjustedPassed;
      entry.fail += (r.adjustedTotal - r.adjustedPassed);
      entry.total += r.adjustedTotal;
    }

    setModelTestCaseRates(counts);
  }

  function parseTrajectoryFilename(filename: string) {
    // Universal parsing for format: model_dataset_task.log
    // Examples: gpt-4o_counsellor-chat_task-1.log, oracle_counsellor-chat_task-2.log

    const filenameWithoutExt = filename.replace(/\.log$/i, '');
    const parts = filenameWithoutExt.split('_');

    if (parts.length >= 3) {
      // Format: model_dataset_task
      const modelRaw = parts[0];
      const dataset = parts[1];
      const task = parts.slice(2).join('_'); // Handle multi-part task names

      const model = getModelDisplayName(modelRaw);
      const taskDisplay = `${dataset} ${task}`.replace(/[_-]+/g, ' ')
        .trim()
        .split(' ')
        .filter(Boolean)
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');

      return { model, task: taskDisplay };
    }

    // Fallback for non-standard formats
    let model = 'Unknown';
    let taskRaw = filename;

    // Try to extract known model patterns from config
    const modelConfigs = getModelConfigs();
    for (const config of modelConfigs) {
      const idx = filename.toLowerCase().indexOf(config.pattern.toLowerCase());
      if (idx !== -1) {
        model = config.display;
        taskRaw = filename.substring(idx + config.pattern.length);
        break;
      }
    }

    taskRaw = taskRaw.replace(/^[-_.]+/, '').replace(/\.log$/i, '');

    if (!taskRaw) {
      taskRaw = filename.replace(/\.log$/i, '');
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

  function getPreferredModel(entries: GroupedEntry[]): string | undefined {
    // Try to find models in preferred order, then fallback to first available
    const availableModels = entries.map(e => e.model);

    for (const preferred of MODEL_DISPLAY_ORDER) {
      if (availableModels.includes(preferred)) {
        return preferred;
      }
    }

    return availableModels[0];
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
    let taskRaw = filename;
    for (const config of MODEL_CONFIGS) {
      const idx = filename.indexOf(config.pattern);
      if (idx !== -1) {
        taskRaw = filename.substring(idx + config.pattern.length);
        break;
      }
    }
    taskRaw = taskRaw.replace(/^[-_.]+/, '').replace(/\.log$/i, '');
    return taskRaw;
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
          const response = await fetch(`/api/idearena/trajectory/${encodeURIComponent(filename)}`);
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
    const filteredLogs = logsList.filter(log =>
      !log.filename.startsWith('nullagent_') &&
      !log.filename.startsWith('oracle_')
    );

    return filteredLogs.reduce((acc, log) => {
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
      const response = await fetch(`/api/idearena/trajectory/${encodeURIComponent(filename)}`);
      if (!response.ok) return;
      const trajectory = await response.json();
      const newTrajectories = new Map(trajectories);
      newTrajectories.set(filename, trajectory);
      setTrajectories(newTrajectories);
    } catch {}
  }

  useEffect(() => {
    if (!logs || logs.length === 0) return;
    const grouped = buildGroupedMap(logs);
    const nextSelected = new Map(selectedModelByTaskId);
    for (const [taskId, entries] of Array.from(grouped.entries())) {
      if (!nextSelected.has(taskId)) {
        const available = getPreferredModel(entries);
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
        <div className="relative w-full bg-[#ECF3FE] rounded-2xl overflow-hidden isolate mb-6">
          <div
            className="absolute inset-0 w-full h-full"
            style={{
              backgroundImage: `linear-gradient(rgba(7, 92, 182, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(7, 92, 182, 0.08) 1px, transparent 1px)`,
              backgroundSize: '40px 40px, 40px 40px',
              backgroundPosition: '0 0, 0 0',
              minHeight: '100%'
            }}
          />
          <svg className="absolute top-0 left-0 w-full h-full pointer-events-none" style={{ opacity: 0.3 }} width="100%" height="100%">
            <defs>
              <pattern id="idearena-plus-pattern" x="40" y="80" width="200" height="200" patternUnits="userSpaceOnUse">
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
            <rect x="0" y="0" width="100%" height="100%" fill="url(#idearena-plus-pattern)" />
          </svg>
          <div className="absolute left-1/2 -translate-x-1/2 bottom-0 translate-y-1/2 w-[800px] h-[800px] bg-[#80CCF5] rounded-full opacity-100" style={{ filter: 'blur(257px)' }} />

          <div className="relative z-10 px-6 py-10 sm:px-12 lg:px-16">
            <h1 className="mt-6 text-4xl sm:text-4xl lg:text-5xl font-normal tracking-tight text-[#1A1A1A] leading-tight">
              <span>AfterQuery IDE Arena</span>
              <br />
          </h1>
            <p className="mt-3 text-gray-700">
              Parsed from local log files
          </p>
          </div>
        </div>

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

        <div className="bg-white rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">All Evaluation Runs</h2>

          {(() => {
            if (logs.length === 0) {
              return <p className="text-gray-500 text-center py-8">No log files found</p>;
            }

            return (
              <div className="space-y-4">
                {logs
                  .sort((a, b) => a.filename.localeCompare(b.filename))
                  .map((log) => {
                    const parsed = parseTrajectoryFilename(log.filename);
                    const isExpanded = expandedFiles.has(log.filename);
                    return (
                    <div key={log.filename} className="border border-gray-200 rounded-lg">
                      <div
                        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
                        onClick={() => {
                          toggleFileExpanded(log.filename);
                          void ensureTrajectory(log.filename);
                        }}
                      >
                        <div>
                          <div className="font-semibold text-gray-900">{parsed.task}</div>
                          <div className="text-sm text-gray-600">Model: {parsed.model}</div>
                          <div className="text-xs text-gray-500">{log.filename}</div>
                        </div>
                        <svg
                          className={`w-4 h-4 transform transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>

                      {isExpanded && (
                        <div className="border-t p-4">
                          <div className="mb-4">
                            <div className="text-sm text-gray-600">
                              <strong>Filename:</strong> {log.filename} <br/>
                              <strong>Size:</strong> {(log.size / 1024).toFixed(1)} KB <br/>
                              <strong>Model:</strong> {parsed.model} <br/>
                              <strong>Task:</strong> {parsed.task}
                            </div>
                          </div>
                          {(() => {
                            const trajectory = trajectories.get(log.filename);
                            if (!trajectory) {
                              return <p className="text-gray-600">Loading trajectory data...</p>;
                            }
                            return <TrajectoryDetails trajectory={trajectory} />;
                          })()}
                        </div>
                      )}
                    </div>
                    );
                  })}
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
