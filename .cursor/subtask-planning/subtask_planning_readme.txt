# Subtask Planning Documentation

This directory contains templates and examples for creating detailed subtask plans that work well with Cursor AI and follow TDD principles.

## Files

- **`template.md`** - Reusable template for creating new subtask plans
- **`task-8-example.md`** - Concrete example showing the template in action
- **`README.md`** - This file

## How to Use

### 1. Copy the Template
Start with `template.md` and fill in the specifics for your task.

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

The key is maintaining the TDD cycle and clear approval points while adapting to your specific domain.