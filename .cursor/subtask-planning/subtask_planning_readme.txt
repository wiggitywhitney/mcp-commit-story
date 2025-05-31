# Subtask Planning Documentation

This directory contains templates and examples for creating detailed subtask plans that work well with Cursor AI and follow TDD principles.

## Files

- **`subtask_template.txt`** - Reusable template for creating new subtask plans
- **`task_4_telemetry_system_plan.txt`** - Concrete example showing the template in action
- **`subtask_planning_readme.txt`** - This file

## How to Use

### 1. Copy the Template
Start with `subtask_template.txt` and fill in the specifics for your task.

### 2. Plan Your Subtasks
Break down the main task into logical, testable chunks. Each subtask should:
- Have a clear, single objective
- Be implementable in 1-2 hours
- Build on previous subtasks
- Have obvious success criteria

### 3. Identify Approval Points
Include "GET APPROVAL FOR DESIGN CHOICES" sections when:
- Multiple valid approaches exist
- Architectural decisions affect future work
- Integration points need clarification
- You need human judgment on trade-offs

### 4. Use with Cursor Rules
These plans work with the Cursor Rules defined in `../.cursor/rules`:
- Cursor will execute each subtask completely without pausing
- Cursor will pause at explicit approval points
- Cursor will auto-document and mark subtasks complete

## TDD Cycle

Each subtask follows strict Test-Driven Development:

```
Write Tests → Run (Fail) → Implement → Run (Pass) → Document → Complete
```

This ensures:
- ✅ Requirements are clear before implementation
- ✅ Implementation is driven by actual needs
- ✅ Regression protection for future changes
- ✅ Code quality and maintainability

## Documentation and Verification

Each subtask includes comprehensive completion verification:

### Three-Place Documentation Rule
When completing subtasks, add documentation IF NEEDED in three places:
1. **Docs directory**: User guides, API documentation, or technical explanations
2. **PRD**: Product requirements and user-facing feature descriptions  
3. **Engineering Spec**: Technical implementation details and architecture

### Completion Verification Checklist
Before marking any subtask complete:
- ✅ **Run the entire test suite** - ensure all tests pass
- ✅ **Check pyproject.toml** - verify dependencies are up to date
- ✅ **Review subtask requirements** - confirm all objectives met
- ✅ **Update documentation** - apply three-place rule as needed

### Documentation Guidelines
- **No approval needed** - make documentation edits directly using best judgment
- **Don't remove existing information** unless it's factually incorrect
- **Ask yourself**: "Do users or future developers need this explained?"
- **Skip documentation** if the answer is clearly no

## Best Practices

### Subtask Sizing
- **Too big**: Hard to test, multiple objectives, takes >2 hours
- **Too small**: Overhead of TDD cycle outweighs value
- **Just right**: Single clear objective, 30min-2hr implementation

### Test Planning
Consider all three categories:
- **Success cases**: Normal operation with valid inputs
- **Error cases**: Invalid inputs, missing dependencies
- **Edge cases**: Boundary conditions, empty/large data

### Approval Point Guidelines
- **Include**: When human judgment is needed on approach
- **Skip**: For straightforward implementation details
- **Be specific**: What exactly needs approval?

## Template Customization

Feel free to adapt the template for different types of work:
- **API development**: Add request/response validation
- **UI components**: Add accessibility and responsive testing
- **Data processing**: Add performance and memory testing
- **Integration work**: Add compatibility and fallback testing

The key principles to maintain:
- **TDD cycle**: Write tests → implement → verify
- **Clear approval points**: When human judgment is needed
- **Comprehensive verification**: Test suite + dependency checks + documentation
- **Quality documentation**: Three-place rule applied thoughtfully