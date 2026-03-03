# Fixes Implemented in StarHTML Checker

## Original Problem

The checker was reporting false positives for valid code:

1. **E003** in `post(f"/todos2/toggle/{todo_id}")` - where `todo_id` is a function parameter
2. **E003** in `data.get(f"completed_{todo_id}")` - Python dict method
3. **W024** in `signal.then(get(...))` - valid pattern for conditional execution

## Fixes Implemented

### 1. E003 - Differentiate between object method and HTTP function

**Before:**
```python
if func_name in HTTP_ACTIONS:
    if node.args and isinstance(node.args[0], ast.JoinedStr):
        self.issues.append(Issue(...))  # Always reported!
```

**After:**
```python
if func_name in HTTP_ACTIONS:
    if node.args and isinstance(node.args[0], ast.JoinedStr):
        # Check if this is a method call (e.g., data.get()) vs standalone function
        is_method_call = isinstance(node.func, ast.Attribute)
        
        if is_method_call:
            # data.get() is a dict method - skip (false positive)
            pass
        else:
            # Standalone HTTP action - check if f-string uses a Signal
            fstring_var_names = self._extract_fstring_variables(node.args[0])
            uses_signal = any(var_name in self._defined_signals for var_name in fstring_var_names)
            
            if uses_signal:
                # Variable IS a Signal - real error
                self.issues.append(Issue(...))
            # else: variable is NOT a Signal (e.g., function parameter) - skip (false positive)
```

### 2. E003 - Detect if variable in f-string is a Signal

**New method added:**
```python
def _extract_fstring_variables(self, node: ast.JoinedStr) -> list[str]:
    """Extract variable names from an f-string."""
    var_names = []
    for elt in node.values:
        if isinstance(elt, ast.FormattedValue):
            if isinstance(elt.value, ast.Name):
                var_names.append(elt.value.id)
            elif isinstance(elt.value, ast.Attribute):
                if isinstance(elt.value.value, ast.Name):
                    var_names.append(elt.value.value.id)
    return var_names
```

### 3. W024 - Recognize `.then()` as valid pattern

**Before:**
```python
if ".set(" not in line:
    issues.append(Issue(...))
```

**After:**
```python
# Check lines containing data_effect and next few lines
context_lines = []
for i in range(lineno, min(lineno + 5, len(analyzer.lines) + 1)):
    context_lines.append(analyzer._get_line(i))
context = "\n".join(context_lines)

has_valid_pattern = ".set(" in context or ".then(" in context

if not has_valid_pattern:
    issues.append(Issue(...))
```

## Result

### Before fixes:
```
ERRORS (2):
  L21 [E003] f-string URL in HTTP action
  L33 [E003] f-string URL in HTTP action
  L83 [W024] data_effect without .set()
  ...plus more in app.py (2 more E003)
```

### After fixes:
```
ERRORS (0):
WARNINGS (7):  # only valid warnings
```

### app.py before:
```
ERRORS (2):
  L102 [E003]  - data.get() in backend
  L136 [E003]  - data.get() in backend
```

### app.py after:
```
ERRORS (0):
WARNINGS (4):  # only valid warnings (W016, W025)
```

### Remaining warnings (all valid):
- `W016`: `theme` used but never defined as Signal (real bug!)
- `W025`: Components without `**kwargs`
- `W029`: Frontend-only signals without `_` prefix

## Documentation Updated

The HELP_LLM documentation was updated:

- **E003**: Now explains it doesn't flag function parameters or `dict.get()`
- **W024**: Now explains `.then()` is a valid pattern

## Files Modified

1. `/Users/cali/Developmet/poc-starhtml-todo-canvas/starhtml_check.py` (full)
2. `/Users/cali/Developmet/starhtml_check_github.py` (E003 fix only)