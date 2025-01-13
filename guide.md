# A Practical Guide to Writing SpecForge YAML Specifications

This guide demonstrates how to write effective YAML specifications for SpecForge through practical examples and proven patterns. Let's build a specification step by step.

## Basic Structure

Every SpecForge specification starts with metadata and builds up in complexity. Here's a minimal working structure:

```yaml
metadata:
  name: "Project Name"
  version: "1.0.0"
  description: "A concise description of what this implements"
  language: "asm"  # or other target language
  authors: ["Your Name"]
  date_created: "2024-01-14T10:00:00"

header_format:
  border_line: ";============================================================================="
  file_name_line: "; example.asm"
  description_line: "; Implementation description"
  blank_comment: ";"
```

## Building Block 1: Data Structures

When defining data structures, be explicit about every field and constraint:

```yaml
structures:
  input_buffer:
    fields:
      - name: "buffer"
        type: "byte array"
        description: "Main input buffer"
        constraints: 
          - "Must be BUF_SIZE bytes"
          - "Must be aligned to 8 bytes"
    documentation: "Primary input buffer structure"
    complexity:
      space: "O(1)"
      access: "O(1)"
```

## Building Block 2: Algorithm Requirements

Algorithms need clear, ordered steps and explicit requirements:

```yaml
algorithms:
  main_process:
    description: "Core processing algorithm"
    implementation_requirements:
      memory_operations:
        - "Must use byte-by-byte moves for buffer operations"
        - "Must increment pointers explicitly"
      register_requirements:
        - "Must preserve caller-saved registers around syscalls"
        - "Must use rcx for all counted loops"
    steps:
      initialization:
        - "Clear all working registers"
        - "Set up initial buffer pointers"
      main_loop:
        - "Read input chunk"
        - "Process each byte"
        - "Write output"
      cleanup:
        - "Handle any remaining data"
        - "Release resources"
```

## Building Block 3: Error Handling

Error handling must cover all cases explicitly:

```yaml
error_handling:
  strategies:
    syscall_errors:
      - "Check return value < 0 for errors"
      - "Preserve error code in rdi"
      - "Jump to error handler"
    buffer_overflow:
      - "Check remaining space before writes"
      - "Exit with error if insufficient"
  error_types:
    - name: "read_error"
      description: "Error reading input"
      handling:
        - "Set error code 1"
        - "Clean up buffers"
        - "Exit through common path"
```

## Building Block 4: Testing Requirements

Define comprehensive test cases:

```yaml
testing:
  unit_tests:
    - name: "empty_input"
      input: ""
      expected_output: ""
      validation:
        - "Must exit cleanly"
        - "Must not write output"
    - name: "normal_case"
      input: "test data"
      expected_output: "expected result"
      validation:
        - "Must process all input"
        - "Must match output exactly"
  integration_tests:
    - name: "pipe_test"
      command: "echo 'test' | ./program"
      expected: "expected output"
```

## Common Patterns

### Register Usage Pattern
```yaml
register_usage:
  general_purpose:
    - name: "r8-r11"
      purpose: "Temporary calculation"
      constraints:
        - "Must save around syscalls"
    - name: "rsi/rdi"
      purpose: "Buffer addressing"
      constraints:
        - "Must use as pairs"
```

### Memory Operation Pattern
```yaml
section_requirements:
  data:
    - "Must declare constants read-only"
    - "Must align to natural boundaries"
  bss:
    variables:
      - name: "work_buffer"
        size: "BUF_SIZE"
        align: 8
        purpose: "Temporary workspace"
```

### Performance Pattern
```yaml
performance:
  time_complexity: "O(n)"
  space_complexity: "O(1)"
  constraints:
    - "Must process input in single pass"
    - "Must use fixed buffer sizes"
  register_usage:
    - "Minimize register spills"
    - "Use dedicated registers for hot paths"
```

## Best Practices

1. Always specify explicit sizes for buffers and data structures
2. Define register usage patterns completely
3. List all error cases and their handling
4. Include both success and failure test cases
5. Document performance requirements quantitatively
6. Specify alignment requirements for all data structures
7. Define initialization requirements explicitly
8. Include cleanup and resource handling requirements

## Validation

Your specification should pass these checks:

1. All referenced registers are defined in register_usage
2. All error paths have defined handling
3. All buffers have explicit sizes
4. All algorithms have clear entry and exit conditions
5. All test cases have defined inputs and outputs

## Common Mistakes to Avoid

1. Implicit register allocation without constraints
2. Undefined behavior for error cases
3. Missing initialization requirements
4. Incomplete test coverage
5. Ambiguous performance requirements
6. Unspecified alignment requirements
7. Missing cleanup specifications

Remember: The goal is to be explicit enough that an LLM can generate working code consistently, but not so rigid that the specification becomes unmaintainable. Find the balance that works for your project's complexity level.
