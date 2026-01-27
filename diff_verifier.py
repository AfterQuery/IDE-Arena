#!/usr/bin/env python3
"""
SWE-bench style diff comparison verifier.
Compares agent code changes against golden solutions in task_diff.txt files.
"""

import difflib
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json


class DiffVerifier:
    """Compares agent changes against golden task_diff.txt solutions."""

    def __init__(self, task_dir: Path):
        self.task_dir = Path(task_dir)
        self.golden_diff_path = self.task_dir / "task_diff.txt"

    def load_golden_diff(self) -> Optional[str]:
        """Load the golden solution diff from task_diff.txt."""
        if not self.golden_diff_path.exists():
            return None
        return self.golden_diff_path.read_text(encoding='utf-8')

    def get_agent_diff(self, repo_path: Path, before_commit: str = None, after_commit: str = "HEAD") -> str:
        """Get the diff of changes made by the agent."""
        try:
            if before_commit:
                cmd = ["git", "diff", before_commit, after_commit]
            else:
                # Get diff of all uncommitted changes
                cmd = ["git", "diff", "HEAD"]

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            if result.returncode != 0:
                # Try getting diff of staged and unstaged changes
                result = subprocess.run(
                    ["git", "diff", "--cached"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )

                if result.returncode != 0:
                    return ""

            return result.stdout

        except Exception as e:
            print(f"Error getting agent diff: {e}")
            return ""

    def normalize_diff(self, diff_text: str) -> List[str]:
        """Normalize diff text for comparison by extracting meaningful changes."""
        lines = []
        for line in diff_text.split('\n'):
            line = line.strip()
            # Skip diff metadata lines
            if line.startswith('diff --git') or line.startswith('index ') or line.startswith('@@'):
                continue
            # Skip empty lines
            if not line:
                continue
            # Keep added/removed content lines
            if line.startswith('+') or line.startswith('-'):
                # Remove the +/- prefix for comparison
                content = line[1:].strip()
                if content:  # Skip empty content
                    lines.append(content)
        return lines

    def extract_code_changes(self, diff_text: str) -> Dict[str, List[str]]:
        """Extract actual code changes (additions/deletions) from diff."""
        changes = {"additions": [], "deletions": []}

        for line in diff_text.split('\n'):
            line = line.strip()
            if line.startswith('+') and not line.startswith('+++'):
                code = line[1:].strip()
                if code and not code.startswith('//') and not code.startswith('#'):
                    changes["additions"].append(code)
            elif line.startswith('-') and not line.startswith('---'):
                code = line[1:].strip()
                if code and not code.startswith('//') and not code.startswith('#'):
                    changes["deletions"].append(code)

        return changes

    def compute_similarity_score(self, agent_diff: str, golden_diff: str,
                               agent_execution_success: bool = True,
                               agent_syntax_errors: int = 0) -> Dict[str, float]:
        """
        Compute similarity between agent and golden diffs with RL-optimized scoring.

        Key improvements for RL training:
        - Separate penalties for syntax errors vs implementation quality
        - Higher weighting for exact matches
        - Adaptive thresholds based on content complexity
        - Better discrimination between success levels
        """
        if not golden_diff:
            return {"overall": 0.0, "details": "No golden diff available", "quality_tier": "no_reference"}

        if not agent_diff:
            return {"overall": 0.0, "details": "No agent changes detected", "quality_tier": "no_changes"}

        # Extract normalized changes
        agent_changes = self.extract_code_changes(agent_diff)
        golden_changes = self.extract_code_changes(golden_diff)

        print(f"DIFF_VERIFIER: Agent additions: {len(agent_changes['additions'])} lines")
        print(f"DIFF_VERIFIER: Golden additions: {len(golden_changes['additions'])} lines")
        print(f"DIFF_VERIFIER: Agent deletions: {len(agent_changes['deletions'])} lines")
        print(f"DIFF_VERIFIER: Golden deletions: {len(golden_changes['deletions'])} lines")
        print(f"DIFF_VERIFIER: Agent execution success: {agent_execution_success}")
        print(f"DIFF_VERIFIER: Agent syntax errors: {agent_syntax_errors}")

        # CRITICAL: Heavy penalty for syntax errors (bad for RL training signal)
        if not agent_execution_success or agent_syntax_errors > 0:
            syntax_penalty = 1.0 - min(0.8, agent_syntax_errors * 0.2)  # Max 80% penalty
            print(f"DIFF_VERIFIER: Applying syntax error penalty: {syntax_penalty:.2f}")
        else:
            syntax_penalty = 1.0

        # Compute enhanced similarity for additions and deletions
        addition_result = self._compute_enhanced_line_similarity(
            agent_changes["additions"], golden_changes["additions"], "additions"
        )
        deletion_result = self._compute_enhanced_line_similarity(
            agent_changes["deletions"], golden_changes["deletions"], "deletions"
        )

        # Weighted combination with emphasis on additions (new functionality)
        if golden_changes["additions"] and golden_changes["deletions"]:
            # Weight additions higher (70%) as they represent new functionality
            base_score = (addition_result["score"] * 0.7 + deletion_result["score"] * 0.3)
        elif golden_changes["additions"]:
            base_score = addition_result["score"]
        elif golden_changes["deletions"]:
            base_score = deletion_result["score"]
        else:
            base_score = 0.0

        # Apply syntax penalty
        overall_score = base_score * syntax_penalty

        # Determine quality tier for RL training categorization
        quality_tier = self._determine_quality_tier(
            overall_score,
            addition_result["exact_matches"],
            deletion_result["exact_matches"],
            agent_execution_success,
            agent_syntax_errors
        )

        print(f"DIFF_VERIFIER: Base similarity: {base_score:.3f}")
        print(f"DIFF_VERIFIER: Final score (with penalties): {overall_score:.3f}")
        print(f"DIFF_VERIFIER: Quality tier: {quality_tier}")

        return {
            "overall": overall_score,
            "base_score": base_score,
            "syntax_penalty": syntax_penalty,
            "additions": addition_result["score"],
            "deletions": deletion_result["score"],
            "exact_matches": addition_result["exact_matches"] + deletion_result["exact_matches"],
            "quality_tier": quality_tier,
            "details": {
                "agent_additions": len(agent_changes["additions"]),
                "agent_deletions": len(agent_changes["deletions"]),
                "golden_additions": len(golden_changes["additions"]),
                "golden_deletions": len(golden_changes["deletions"]),
                "addition_exact_matches": addition_result["exact_matches"],
                "deletion_exact_matches": deletion_result["exact_matches"],
                "addition_fuzzy_matches": addition_result["fuzzy_matches"],
                "deletion_fuzzy_matches": deletion_result["fuzzy_matches"]
            }
        }

    def compute_strict_binary_score(self, agent_diff: str, golden_diff: str) -> Dict[str, float]:
        """
        Strict binary comparison: returns 1.0 if the agent's added/removed code lines exactly
        match the golden diff's added/removed code lines (after normalization); otherwise 0.0.
        Order and counts must match.
        """
        if not golden_diff:
            return {"overall": 0.0, "details": "No golden diff available"}

        if not agent_diff:
            return {"overall": 0.0, "details": "No agent changes detected"}

        agent_changes = self.extract_code_changes(agent_diff)
        golden_changes = self.extract_code_changes(golden_diff)

        def normalize_list(lines: List[str]) -> List[str]:
            return [self._normalize_code_line(l) for l in lines]

        agent_add_norm = normalize_list(agent_changes["additions"])
        agent_del_norm = normalize_list(agent_changes["deletions"])
        golden_add_norm = normalize_list(golden_changes["additions"])
        golden_del_norm = normalize_list(golden_changes["deletions"])

        perfect_add = agent_add_norm == golden_add_norm
        perfect_del = agent_del_norm == golden_del_norm

        overall = 1.0 if (perfect_add and perfect_del) else 0.0

        print(f"DIFF_VERIFIER (STRICT): Perfect additions match: {perfect_add}")
        print(f"DIFF_VERIFIER (STRICT): Perfect deletions match: {perfect_del}")
        print(f"DIFF_VERIFIER (STRICT): Overall result: {overall}")

        return {
            "overall": overall,
            "details": {
                "agent_additions": len(agent_add_norm),
                "agent_deletions": len(agent_del_norm),
                "golden_additions": len(golden_add_norm),
                "golden_deletions": len(golden_del_norm),
                "perfect_additions": perfect_add,
                "perfect_deletions": perfect_del,
            }
        }

    def _compute_enhanced_line_similarity(self, agent_lines: List[str], golden_lines: List[str],
                                        change_type: str) -> Dict[str, float]:
        """
        Enhanced similarity computation optimized for RL training.

        Returns detailed scoring with separate tracking of exact vs fuzzy matches.
        Uses adaptive thresholds based on line complexity.
        """
        if not golden_lines:
            return {
                "score": 1.0 if not agent_lines else 0.0,
                "exact_matches": 0,
                "fuzzy_matches": 0,
                "total_agent_lines": len(agent_lines)
            }

        if not agent_lines:
            return {
                "score": 0.0,
                "exact_matches": 0,
                "fuzzy_matches": 0,
                "total_agent_lines": 0
            }

        exact_matches = 0
        fuzzy_matches = 0
        match_scores = []

        # Determine adaptive threshold based on average line complexity
        avg_golden_length = sum(len(line.strip()) for line in golden_lines) / len(golden_lines)
        # More complex lines (longer) get lower thresholds for fuzzy matching
        # Simple lines (short) need higher similarity to count as matches
        if avg_golden_length < 20:  # Short lines (imports, simple statements)
            fuzzy_threshold = 0.85
        elif avg_golden_length < 50:  # Medium lines
            fuzzy_threshold = 0.75
        else:  # Long/complex lines
            fuzzy_threshold = 0.65

        print(f"DIFF_VERIFIER: {change_type} adaptive threshold: {fuzzy_threshold:.2f} (avg length: {avg_golden_length:.1f})")

        # Match each agent line against all golden lines
        for agent_line in agent_lines:
            agent_normalized = self._normalize_code_line(agent_line)
            best_similarity = 0.0
            best_match_type = "none"

            for golden_line in golden_lines:
                golden_normalized = self._normalize_code_line(golden_line)

                # Check for exact matches (heavily weighted)
                if agent_normalized == golden_normalized:
                    best_similarity = 1.0
                    best_match_type = "exact"
                    break

                # Check for high-quality fuzzy matches
                line_similarity = difflib.SequenceMatcher(None, agent_normalized, golden_normalized).ratio()
                if line_similarity > best_similarity:
                    best_similarity = line_similarity
                    if line_similarity >= fuzzy_threshold:
                        best_match_type = "fuzzy"

            # Score the match
            if best_match_type == "exact":
                exact_matches += 1
                match_scores.append(1.0)  # Perfect score for exact matches
                print(f"DIFF_VERIFIER: EXACT match '{agent_line[:50]}...'")
            elif best_match_type == "fuzzy":
                fuzzy_matches += 1
                # Fuzzy matches get partial credit, weighted by similarity
                fuzzy_score = best_similarity * 0.7  # Max 70% credit for fuzzy matches
                match_scores.append(fuzzy_score)
                print(f"DIFF_VERIFIER: FUZZY match '{agent_line[:50]}...' (sim: {best_similarity:.2f})")
            else:
                match_scores.append(0.0)  # No credit for poor matches

        # Calculate weighted score
        # Exact matches get full weight, fuzzy matches get reduced weight
        if match_scores:
            weighted_score = sum(match_scores) / len(agent_lines)
        else:
            weighted_score = 0.0

        print(f"DIFF_VERIFIER: {change_type} results: {exact_matches} exact, {fuzzy_matches} fuzzy, {len(agent_lines)} total")
        print(f"DIFF_VERIFIER: {change_type} weighted score: {weighted_score:.3f}")

        return {
            "score": weighted_score,
            "exact_matches": exact_matches,
            "fuzzy_matches": fuzzy_matches,
            "total_agent_lines": len(agent_lines)
        }

    def _determine_quality_tier(self, overall_score: float, addition_exact_matches: int,
                               deletion_exact_matches: int, execution_success: bool,
                               syntax_errors: int) -> str:
        """
        Determine quality tier for RL training categorization.

        This provides clear categories that RL algorithms can use to understand
        the quality of different implementations.
        """
        total_exact_matches = addition_exact_matches + deletion_exact_matches

        # Syntax errors get bottom tier regardless of other factors
        if not execution_success or syntax_errors > 0:
            if syntax_errors > 2:
                return "syntax_failure_severe"  # Multiple syntax errors
            else:
                return "syntax_failure_minor"   # Few syntax errors, might be recoverable

        # Perfect or near-perfect implementations
        if overall_score >= 0.95 and total_exact_matches >= 3:
            return "excellent"                   # Near-perfect implementation
        elif overall_score >= 0.85 and total_exact_matches >= 2:
            return "very_good"                   # High quality with some exact matches

        # Good implementations
        elif overall_score >= 0.70 and total_exact_matches >= 1:
            return "good"                        # Solid implementation, some exact matches
        elif overall_score >= 0.60:
            return "acceptable"                  # Reasonable attempt, mostly fuzzy matches

        # Poor but attempted implementations
        elif overall_score >= 0.30:
            return "poor_attempt"                # Low quality but shows understanding
        elif overall_score >= 0.10:
            return "minimal_attempt"             # Very low quality, minimal understanding

        # Failed implementations
        else:
            return "failed"                      # No meaningful implementation

    def _normalize_code_line(self, line: str) -> str:
        """Normalize a code line for comparison."""
        # Remove extra whitespace and convert to lowercase for comparison
        return ' '.join(line.strip().split()).lower()

    def verify_implementation(self, repo_path: Path, before_commit: str = None) -> Dict:
        """Main verification method that compares agent changes to golden diff."""
        golden_diff = self.load_golden_diff()
        if not golden_diff:
            return {
                "score": 0.0,
                "passed": False,
                "error": "No golden diff found",
                "method": "diff_comparison"
            }

        agent_diff = self.get_agent_diff(repo_path, before_commit)
        similarity_scores = self.compute_similarity_score(agent_diff, golden_diff)

        # Consider passed if overall similarity > 0.8 (80%)
        passed = similarity_scores["overall"] >= 0.8

        return {
            "score": similarity_scores["overall"],
            "passed": passed,
            "similarity_breakdown": similarity_scores,
            "method": "diff_comparison",
            "golden_diff_length": len(golden_diff.split('\n')),
            "agent_diff_length": len(agent_diff.split('\n')) if agent_diff else 0
        }


def main():
    """CLI interface for testing the diff verifier."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python diff_verifier.py <task_dir> <repo_path> [before_commit]")
        sys.exit(1)

    task_dir = Path(sys.argv[1])
    repo_path = Path(sys.argv[2])
    before_commit = sys.argv[3] if len(sys.argv) > 3 else None

    verifier = DiffVerifier(task_dir)
    result = verifier.verify_implementation(repo_path, before_commit)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
