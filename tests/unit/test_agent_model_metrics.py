import pytest

def evaluate_metrics(outputs, expected):
    # Handle list of outputs for consistency
    if isinstance(outputs, list):
        consistency = all(o == outputs[0] for o in outputs)
        # Evaluate metrics for the first output
        output = outputs[0] if outputs else {}
    else:
        output = outputs
        consistency = True
    # Handle malformed input
    if not isinstance(output, dict):
        return {
            'relevance': False,
            'accuracy': False,
            'completeness': False,
            'consistency': False,
        }
    # Relevance: all expected summary_keywords in summary
    summary = output.get('summary', '')
    summary_keywords = expected.get('summary_keywords', [])
    relevance = all(kw in summary for kw in summary_keywords)
    # Accuracy: timestamp and commit_hash match
    accuracy = (
        output.get('timestamp') == expected.get('timestamp') and
        output.get('commit_hash') == expected.get('commit_hash')
    )
    # Completeness: all required fields are non-empty
    required_fields = ['accomplishments', 'frustrations', 'summary', 'reflections']
    completeness = all(
        (isinstance(output.get(f), list) and output.get(f)) or
        (isinstance(output.get(f), str) and output.get(f).strip())
        for f in required_fields
    )
    return {
        'relevance': relevance,
        'accuracy': accuracy,
        'completeness': completeness,
        'consistency': consistency,
    }

# Sample outputs and expected values for metrics tests
sample_output = {
    'timestamp': '2:17 PM',
    'commit_hash': 'def456',
    'accomplishments': ['Implemented feature X', 'Fixed bug Y'],
    'frustrations': ['Spent hours debugging config'],
    'summary': 'A friendly, succinct summary that captures what was accomplished.',
    'reflections': ['This was a tough one!'],
}
expected = {
    'timestamp': '2:17 PM',
    'commit_hash': 'def456',
    'accomplishments': ['Implemented feature X', 'Fixed bug Y'],
    'frustrations': ['Spent hours debugging config'],
    'summary_keywords': ['summary', 'accomplished'],
    'reflections': ['tough'],
}

sample_output_incomplete = {
    'timestamp': '2:17 PM',
    'commit_hash': 'def456',
    'accomplishments': [],
    'frustrations': [],
    'summary': '',
    'reflections': [],
}

sample_output_malformed = 'not a dict'

sample_outputs_multiple = [sample_output, sample_output]


def test_metrics_relevance():
    metrics = evaluate_metrics(sample_output, expected)
    assert metrics['relevance'] is True

def test_metrics_accuracy():
    metrics = evaluate_metrics(sample_output, expected)
    assert metrics['accuracy'] is True

def test_metrics_completeness():
    metrics = evaluate_metrics(sample_output, expected)
    assert metrics['completeness'] is True

def test_metrics_consistency():
    metrics = evaluate_metrics(sample_outputs_multiple, expected)
    assert metrics['consistency'] is True

def test_metrics_handles_edge_cases():
    metrics = evaluate_metrics(sample_output_incomplete, expected)
    assert metrics['completeness'] is False
    metrics = evaluate_metrics(sample_output_malformed, expected)
    assert metrics['relevance'] is False 