import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../tests/unit')))
from test_agent_model_validation import (
    agent_model_parse,
    agent_model_generate_summary,
    DAILY_NOTE_MD,
    REFLECTION_MD,
    SUMMARY_MD,
    EMPTY_MD,
    MALFORMED_MD,
)

def run_test_case(name, func, *args):
    print(f'--- {name} ---')
    try:
        result = func(*args)
        print('Result:', result)
    except Exception as e:
        print('Exception:', type(e).__name__, str(e))
    print()

def main():
    run_test_case('Parse Daily Note', agent_model_parse, DAILY_NOTE_MD)
    run_test_case('Parse Reflection', agent_model_parse, REFLECTION_MD)
    run_test_case('Generate Summary', agent_model_generate_summary, SUMMARY_MD)
    run_test_case('Handle Empty Entry', agent_model_parse, EMPTY_MD)
    run_test_case('Handle Malformed Entry', agent_model_parse, MALFORMED_MD)

if __name__ == '__main__':
    main() 