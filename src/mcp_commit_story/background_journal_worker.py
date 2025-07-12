#!/usr/bin/env python3
"""
Background journal worker for detached journal generation.

This script runs as a detached background process spawned by git hooks
to generate journal entries without blocking git operations.

Implements Task 57.4 approved design decisions:
- 30-second max delay (generous since background)
- Silent failure with telemetry capture
- Detached process execution
- Graceful error handling

Architecture Decision: Background Execution Model (2025-06-27)
Journal generation now runs in detached background processes to ensure
git operations complete immediately without waiting for AI generation.
"""

import os
import sys
import argparse
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add src to path for imports when run as standalone script
if __name__ == '__main__':
    script_dir = Path(__file__).parent
    src_dir = script_dir.parent.parent
    sys.path.insert(0, str(src_dir))

from mcp_commit_story.journal_orchestrator import orchestrate_journal_generation
from mcp_commit_story.journal_generate import get_journal_file_path, append_to_journal_file
from mcp_commit_story.telemetry import get_mcp_metrics
from mcp_commit_story.config import load_config

# Configure logging for background worker
logger = logging.getLogger(__name__)


def setup_background_logging(repo_path: str) -> None:
    """Set up logging for background journal worker.
    
    Args:
        repo_path: Path to the git repository
    """
    try:
        log_file = os.path.join(repo_path, '.git', 'hooks', 'mcp-background-journal.log')
        
        # Ensure hooks directory exists
        hooks_dir = os.path.dirname(log_file)
        os.makedirs(hooks_dir, exist_ok=True)
        
        # Keep log file reasonable size (truncate if > 5MB)
        if os.path.exists(log_file) and os.path.getsize(log_file) > 5 * 1024 * 1024:
            old_log = log_file + '.old'
            if os.path.exists(old_log):
                os.unlink(old_log)
            os.rename(log_file, old_log)
        
        # Set up file handler
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] [PID:%(process)d] %(message)s')
        file_handler.setFormatter(formatter)
        
        # Configure logger
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        logger.addHandler(file_handler)
        
    except Exception:
        # If logging setup fails, continue without logging
        # This maintains the graceful degradation principle
        pass


def record_background_telemetry(operation: str, success: bool, duration: float = None, error_type: str = None) -> None:
    """Record telemetry for background operations.
    
    Args:
        operation: Name of the operation
        success: Whether the operation succeeded
        duration: Operation duration in seconds
        error_type: Type of error if operation failed
    """
    try:
        metrics = get_mcp_metrics()
        if metrics:
            # Record operation counter
            metrics.record_counter(
                f'background_journal_{operation}_total',
                attributes={
                    'success': str(success).lower(),
                    'error_type': error_type or 'none'
                }
            )
            
            # Record duration if provided
            if duration is not None:
                metrics.record_histogram(
                    f'background_journal_{operation}_duration_seconds',
                    duration,
                    attributes={
                        'success': str(success).lower()
                    }
                )
    except Exception:
        # Silent failure for telemetry - don't let telemetry issues block operations
        pass


def generate_journal_entry_background(commit_hash: str, repo_path: str) -> Dict[str, Any]:
    """
    Generate journal entry in background with comprehensive error handling.
    
    Args:
        commit_hash: Git commit hash to generate journal entry for
        repo_path: Path to git repository
        
    Returns:
        Dict with generation results and telemetry data
    """
    start_time = time.time()
    operation_start = datetime.now()
    
    try:
        logger.info(f"Starting background journal generation for commit {commit_hash[:8]}")
        
        # Change to repo directory for proper git operations
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        try:
            # Get journal file path for today
            date_str = operation_start.strftime("%Y-%m-%d")
            journal_path = get_journal_file_path(date_str, "daily")
            
            logger.info(f"Journal will be written to: {journal_path}")
            
            # Run journal generation orchestration
            result = orchestrate_journal_generation(commit_hash, str(journal_path))
            
            execution_time = time.time() - start_time
            
            if result.get('success'):
                logger.info(f"Background journal generation completed successfully in {execution_time:.2f}s")
                
                # Record successful telemetry
                record_background_telemetry('generation', True, execution_time)
                
                return {
                    'status': 'success',
                    'execution_time': execution_time,
                    'journal_path': str(journal_path),
                    'commit_hash': commit_hash,
                    'telemetry': result.get('telemetry', {})
                }
            else:
                error_msg = result.get('error', 'Unknown orchestration error')
                logger.error(f"Background journal generation failed: {error_msg}")
                
                # Record failed telemetry
                record_background_telemetry('generation', False, execution_time, 'orchestration_error')
                
                return {
                    'status': 'error',
                    'error': error_msg,
                    'execution_time': execution_time,
                    'commit_hash': commit_hash,
                    'phase': result.get('phase', 'unknown')
                }
                
        finally:
            # Always restore original working directory
            os.chdir(original_cwd)
            
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"Background journal generation failed with exception: {str(e)}"
        logger.error(error_msg)
        
        # Record failed telemetry
        record_background_telemetry('generation', False, execution_time, 'exception')
        
        return {
            'status': 'error',
            'error': error_msg,
            'execution_time': execution_time,
            'commit_hash': commit_hash,
            'exception': str(e)
        }


def main():
    """Main entry point for background journal worker."""
    parser = argparse.ArgumentParser(description='Background journal generation worker')
    parser.add_argument('--commit-hash', required=True, help='Git commit hash to generate journal for')
    parser.add_argument('--repo-path', required=True, help='Path to git repository')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout in seconds (default: 30)')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_background_logging(args.repo_path)
    
    # Log worker startup
    logger.info(f"Background journal worker started for commit {args.commit_hash[:8]} in {args.repo_path}")
    
    try:
        # Set timeout alarm (Unix only)
        if hasattr(os, 'alarm'):
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Background journal generation timed out after {args.timeout} seconds")
            
            import signal
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(args.timeout)
        
        # Generate journal entry
        result = generate_journal_entry_background(args.commit_hash, args.repo_path)
        
        # Cancel timeout alarm
        if hasattr(os, 'alarm'):
            signal.alarm(0)
        
        # Log final result
        if result['status'] == 'success':
            logger.info(f"Background journal worker completed successfully in {result['execution_time']:.2f}s")
            sys.exit(0)
        else:
            logger.error(f"Background journal worker failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except TimeoutError as e:
        logger.error(f"Background journal worker timed out: {str(e)}")
        record_background_telemetry('generation', False, args.timeout, 'timeout')
        sys.exit(2)
        
    except KeyboardInterrupt:
        logger.info("Background journal worker interrupted")
        record_background_telemetry('generation', False, None, 'interrupted')
        sys.exit(3)
        
    except Exception as e:
        logger.error(f"Background journal worker failed with unexpected error: {str(e)}")
        record_background_telemetry('generation', False, None, 'unexpected_error')
        sys.exit(4)


if __name__ == '__main__':
    main() 