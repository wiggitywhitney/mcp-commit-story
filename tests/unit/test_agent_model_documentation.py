import pytest

sample_results = [
    {'name': 'Parse Daily Note', 'status': 'success', 'output': {'timestamp': '2:17 PM'}},
    {'name': 'Parse Reflection', 'status': 'exception', 'exception': 'NotImplementedError'},
    {'name': 'Generate Summary', 'status': 'success', 'output': 'Today was a productive day.'},
]
sample_metrics = {
    'relevance': True,
    'accuracy': False,
    'completeness': True,
    'consistency': True,
}

empty_results = []
empty_metrics = {}

def generate_documentation(results, metrics):
    if not results:
        return 'No test results to document'
    doc = ['# Test Results Summary']
    # Successes
    successes = [r for r in results if r['status'] == 'success']
    doc.append('## Successes')
    if successes:
        for s in successes:
            doc.append(f"- {s['name']}")
    else:
        doc.append('None')
    # Failures
    failures = [r for r in results if r['status'] != 'success']
    doc.append('## Failures')
    if failures:
        for f in failures:
            doc.append(f"- {f['name']}: {f.get('exception', f.get('status'))}")
    else:
        doc.append('None')
    # Recommendations
    doc.append('## Recommendations')
    recs = []
    if not metrics.get('accuracy', True):
        recs.append('- Improve accuracy')
    if not metrics.get('relevance', True):
        recs.append('- Improve relevance')
    if not metrics.get('completeness', True):
        recs.append('- Improve completeness')
    if not metrics.get('consistency', True):
        recs.append('- Improve consistency')
    if recs:
        doc.extend(recs)
    else:
        doc.append('No major recommendations')
    return '\n'.join(doc)

def test_documentation_generates_markdown_summary():
    doc = generate_documentation(sample_results, sample_metrics)
    assert doc.startswith('# Test Results Summary')
    assert 'Parse Daily Note' in doc
    assert 'Parse Reflection' in doc
    assert 'Generate Summary' in doc

def test_documentation_includes_sections():
    doc = generate_documentation(sample_results, sample_metrics)
    assert '## Successes' in doc
    assert '## Failures' in doc
    assert '## Recommendations' in doc

def test_documentation_recommendations_are_actionable():
    doc = generate_documentation(sample_results, sample_metrics)
    assert '- Improve accuracy' in doc or 'accuracy' in doc

def test_documentation_handles_empty_results():
    doc = generate_documentation(empty_results, empty_metrics)
    assert 'No test results to document' in doc or doc.strip() == '' 