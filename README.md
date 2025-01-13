# SpecForge

SpecForge is an experimental system for transforming software specifications into implementation through Large Language Models (LLMs). This project represents ongoing research into reliable code generation through precise specification.

## Introduction

The fundamental challenge in programming isn't syntax - it's the precise communication of intent. While LLMs can generate code, their output varies in reliability. SpecForge addresses this by providing them with unambiguous, structured specifications that consistently produce working implementations.

We have validated this approach with x86-64 assembly language, demonstrating that properly constrained LLMs can generate complex, working code. The Base64 encoder example included in this repository shows a complete implementation with streaming input, proper padding, and comprehensive error handling - all generated from a SpecForge specification.

## Core Architecture

The system processes YAML-based specifications through a hierarchical compiler that enforces completeness and consistency. Each specification captures the full implementation requirements:

Register allocation constraints define exactly how registers must be used, preventing conflicts and ensuring efficiency. Memory operations and data structures are specified with byte-level precision. Algorithms are broken down into unambiguous steps with explicit requirements for each operation. Error handling paths are fully defined, ensuring robust recovery from all error conditions.

The specification compiler enforces cross-cutting constraints, ensuring that register usage remains consistent across sections and that memory operations maintain proper alignment. Performance requirements are tracked and validated against the implementation details.

## Current Limitations

As experimental software, SpecForge has important limitations. The specification language is still evolving as we discover new requirements. Code generation reliability varies across different domains and complexity levels. The validation system cannot yet verify all constraints automatically.

These limitations reflect the research nature of the project. Users should approach SpecForge as a tool for exploring specification-driven code generation rather than a production-ready system.

## Technical Usage

Create a YAML specification following the included schema:

```bash
python specforge.py forge your-project.yaml
```

The compiler produces a formal specification suitable for LLM code generation. We recommend using Claude with the specification, as our testing has focused on its capabilities.

## Research Goals

This project explores several key questions:

Can we make code generation reliable through specification rather than natural language processing?
What level of detail is necessary in specifications to ensure consistent results?
How can we validate specifications automatically?
What tools can help developers write precise specifications efficiently?

## Future Directions

Current development focuses on specification validation and compiler robustness. We aim to expand language support while maintaining generation reliability. Feedback and contributions are welcome, particularly in areas of specification design and validation.

## License

Released under GPL v3 License - experiment, learn, contribute.

---

The code and specifications in this repository demonstrate current capabilities. They work as shown but may need adaptation for different use cases. We encourage experimentation while maintaining awareness of the system's experimental nature.

For technical discussion or to report findings, please open an issue.
