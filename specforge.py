#!/usr/bin/env python3
"""
SpecForge: Experimental Specification Generator
-------------------------------------------------
A tool for generating language-agnostic specifications from YAML-based DSL.
Tries to support multiple programming languages, paradigms, and complex requirements.

Features:
- Rich YAML-based specification language
- Comprehensive language support
- Extensible architecture
- Built-in validation
- Detailed error reporting
- Multiple output formats
- Template support
- Version control integration

Author: Ciphernom
License: GPLv3
Version: 1.0.0
"""

import sys
import os
import yaml
import json
import logging
import argparse
import re
import hashlib
import datetime
from typing import Dict, List, Any, Optional, Union, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from contextlib import contextmanager
import tempfile
import shutil
import importlib.util
from concurrent.futures import ThreadPoolExecutor
import threading
from functools import wraps
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('specforge.log')
    ]
)
logger = logging.getLogger(__name__)

class SpecForgeError(Exception):
    """Base exception for all SpecForge errors"""
    pass

class ValidationError(SpecForgeError):
    """Raised when specification validation fails"""
    pass

class ParsingError(SpecForgeError):
    """Raised when YAML parsing fails"""
    pass

class LanguageError(SpecForgeError):
    """Raised when language-specific operations fail"""
    pass

@dataclass
class HeaderFormat:
    """Represents header format requirements"""
    border_line: str
    file_name_line: str
    description_line: str
    blank_comment: str
    assembly_lines: List[str]
    directives: List[str]

@dataclass
class RegisterInfo:
    """Information about a register"""
    name: str
    purpose: str
    byte_regs: Optional[List[str]] = None
    constraints: List[str] = field(default_factory=list)

@dataclass
class RegisterUsage:
    """Register usage requirements"""
    general_purpose: List[RegisterInfo]

@dataclass
class Field:
    """Represents a field in a data structure"""
    name: str
    type: str
    description: str
    constraints: List[str] = field(default_factory=list)

@dataclass
class DataStructure:
    """Represents a data structure specification"""
    name: str
    fields: List[Field]
    documentation: str
    constraints: List[str]
    examples: List[str]
    complexity: Dict[str, str]

@dataclass
class PaddingRules:
    """Represents padding rules for encoding"""
    one_byte: List[str]
    two_bytes: List[str]

@dataclass
class ImplementationRequirements:
    """Detailed implementation requirements"""
    memory_operations: List[str]
    encoding_requirements: List[str]
    leftover_handling: List[str]
    padding_rules: PaddingRules

@dataclass
class AlgorithmStep:
    """Represents a structured algorithm step"""
    name: str
    actions: List[str]

@dataclass
class Algorithm:
    """Represents an algorithm specification"""
    name: str
    description: str
    implementation_requirements: ImplementationRequirements
    steps: Dict[str, List[str]]  # Changed to Dict for structured steps
    complexity: Dict[str, str]
    edge_cases: List[str]
    preconditions: List[str]
    postconditions: List[str]
    invariants: List[str]
    examples: List[Dict[str, Any]]

@dataclass
class ErrorType:
    """Represents an error type"""
    name: str
    description: str
    handling: List[str]

@dataclass
class ErrorHandling:
    """Error handling specifications"""
    strategies: Dict[str, List[str]]  # Changed to Dict for structured strategies
    error_types: List[ErrorType]
    syscall_requirements: List[str]

@dataclass
class BssVariable:
    """Represents a BSS section variable"""
    name: str
    size: Union[str, int]
    align: int
    purpose: str

@dataclass
class SectionRequirements:
    """Section-specific requirements"""
    data: List[str]
    bss: List[BssVariable]
    text: Dict[str, List[str]]

@dataclass
class Benchmark:
    """Performance benchmark specification"""
    name: str
    input_size: str
    expected_time: Optional[str]
    requirements: List[str]

@dataclass
class Performance:
    """Performance requirements"""
    time_complexity: str
    space_complexity: str
    constraints: List[str]
    register_usage: List[str]
    memory_access: List[str]
    benchmarks: List[Benchmark]

@dataclass
class TestCase:
    """Individual test case"""
    name: str
    input: Any
    expected_output: Any
    validation: List[str]

@dataclass
class Testing:
    """Complete test specifications"""
    unit_tests: List[TestCase]
    integration_tests: List[Dict[str, Any]]
    conformance_tests: List[Dict[str, Any]]

@dataclass
class CodeStyle:
    """Code style requirements"""
    indentation: List[str]
    comments: List[str]
    naming: List[str]
    organization: List[str]

@dataclass
class Specification:
    """Complete specification container"""
    metadata: Dict[str, Any]
    header_format: HeaderFormat
    register_usage: RegisterUsage
    structures: Dict[str, DataStructure]
    algorithms: Dict[str, Algorithm]
    error_handling: ErrorHandling
    section_requirements: SectionRequirements
    performance: Performance
    testing: Testing
    code_style: CodeStyle

class Cache:
    """Thread-safe cache for specification processing"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def get_lock(self, key: str):
        """Get lock for specific cache key"""
        with self._lock:
            yield
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        with self._lock:
            self._cache[key] = value
    
    def clear(self) -> None:
        """Clear entire cache"""
        with self._lock:
            self._cache.clear()

class SpecificationProcessor:
    """Processes raw YAML data into structured specification"""
    
    @staticmethod
    def process_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
        """Process metadata section"""
        return data.get('metadata', {})

    @staticmethod
    def process_header_format(data: Dict[str, Any]) -> HeaderFormat:
        """Process header format requirements"""
        header = data.get('header_format', {})
        return HeaderFormat(
            border_line=header.get('border_line', ''),
            file_name_line=header.get('file_name_line', ''),
            description_line=header.get('description_line', ''),
            blank_comment=header.get('blank_comment', ''),
            assembly_lines=header.get('assembly_lines', []),
            directives=header.get('directives', [])
        )

    @staticmethod
    def process_register_usage(data: Dict[str, Any]) -> RegisterUsage:
        """Process register usage requirements"""
        usage = data.get('register_usage', {})
        general_purpose = [
            RegisterInfo(
                name=reg['name'],
                purpose=reg['purpose'],
                byte_regs=reg.get('byte_regs'),
                constraints=reg.get('constraints', [])
            )
            for reg in usage.get('general_purpose', [])
        ]
        return RegisterUsage(general_purpose=general_purpose)

    @staticmethod
    def process_data_structures(data: Dict[str, Any]) -> Dict[str, DataStructure]:
        """Process data structure definitions"""
        structures = {}
        for name, struct in data.get('structures', {}).items():
            fields = [
                Field(
                    name=field['name'],
                    type=field['type'],
                    description=field.get('description', ''),
                    constraints=field.get('constraints', [])
                )
                for field in struct.get('fields', [])
            ]
            structures[name] = DataStructure(
                name=name,
                fields=fields,
                documentation=struct.get('documentation', ''),
                constraints=struct.get('constraints', []),
                examples=struct.get('examples', []),
                complexity=struct.get('complexity', {})
            )
        return structures

    @staticmethod
    def process_algorithms(data: Dict[str, Any]) -> Dict[str, Algorithm]:
        """Process algorithm specifications"""
        algorithms = {}
        for name, algo in data.get('algorithms', {}).items():
            impl_req = algo.get('implementation_requirements', {})
            padding_rules = impl_req.get('padding_rules', {})
            
            implementation_requirements = ImplementationRequirements(
                memory_operations=impl_req.get('memory_operations', []),
                encoding_requirements=impl_req.get('encoding_requirements', []),
                leftover_handling=impl_req.get('leftover_handling', []),
                padding_rules=PaddingRules(
                    one_byte=padding_rules.get('one_byte', []),
                    two_bytes=padding_rules.get('two_bytes', [])
                )
            )
            
            algorithms[name] = Algorithm(
                name=name,
                description=algo.get('description', ''),
                implementation_requirements=implementation_requirements,
                steps=algo.get('steps', {}),  # Now expecting Dict[str, List[str]]
                complexity=algo.get('complexity', {}),
                edge_cases=algo.get('edge_cases', []),
                preconditions=algo.get('preconditions', []),
                postconditions=algo.get('postconditions', []),
                invariants=algo.get('invariants', []),
                examples=algo.get('examples', [])
            )
        return algorithms

    @staticmethod
    def process_error_handling(data: Dict[str, Any]) -> ErrorHandling:
        """Process error handling specifications"""
        err_handling = data.get('error_handling', {})
        error_types = []
        strategies = {}

        # Process error types
        error_types_raw = err_handling.get('error_types', [])
        for err in error_types_raw:
            if isinstance(err, str):
                error_types.append(ErrorType(
                    name=err,
                    description=f"Handle {err}",
                    handling=["Detect", "Log", "Handle"]
                ))
            elif isinstance(err, dict):
                error_types.append(ErrorType(
                    name=err['name'],
                    description=err.get('description', f"Handle {err['name']}"),
                    handling=err.get('handling', ["Detect", "Log", "Handle"])
                ))

        # Process strategies
        strategies_raw = err_handling.get('strategies', {})
        if isinstance(strategies_raw, list):
            # If strategies is a list, use it as the "general" category
            strategies = {"general": strategies_raw}
        elif isinstance(strategies_raw, dict):
            strategies = strategies_raw

        return ErrorHandling(
            strategies=strategies,
            error_types=error_types,
            syscall_requirements=err_handling.get('syscall_requirements', [])
        )

    @staticmethod
    def process_section_requirements(data: Dict[str, Any]) -> SectionRequirements:
        """Process section requirements"""
        reqs = data.get('section_requirements', {})
        bss_vars = [
            BssVariable(
                name=var['name'],
                size=var['size'],
                align=var['align'],
                purpose=var['purpose']
            )
            for var in reqs.get('bss', {}).get('variables', [])
        ]
        return SectionRequirements(
            data=reqs.get('data', []),
            bss=bss_vars,
            text=reqs.get('text', {})
        )

    @staticmethod
    def process_performance(data: Dict[str, Any]) -> Performance:
        """Process performance requirements"""
        perf = data.get('performance', {})
        benchmarks = [
            Benchmark(
                name=bench['name'],
                input_size=bench['input_size'],
                expected_time=bench.get('expected_time'),
                requirements=bench.get('requirements', [])
            )
            for bench in perf.get('benchmarks', [])
        ]
        return Performance(
            time_complexity=perf.get('time_complexity', ''),
            space_complexity=perf.get('space_complexity', ''),
            constraints=perf.get('constraints', []),
            register_usage=perf.get('register_usage', []),
            memory_access=perf.get('memory_access', []),
            benchmarks=benchmarks
        )

    @staticmethod
    def process_testing(data: Dict[str, Any]) -> Testing:
        """Process testing specifications"""
        test_data = data.get('testing', {})
        unit_tests = []
        
        # Handle both string and dictionary test cases
        for test in test_data.get('unit_tests', []):
            if isinstance(test, str):
                # Simple string test case
                unit_tests.append(TestCase(
                    name=test,
                    input="TBD",
                    expected_output="TBD",
                    validation=[]
                ))
            else:
                # Full test case dictionary
                unit_tests.append(TestCase(
                    name=test['name'],
                    input=test.get('input', 'TBD'),
                    expected_output=test.get('expected_output', 'TBD'),
                    validation=test.get('validation', [])
                ))
        
        # Handle integration and conformance tests similarly
        integration_tests = []
        for test in test_data.get('integration_tests', []):
            if isinstance(test, str):
                integration_tests.append({"name": test})
            else:
                integration_tests.append(test)
                
        conformance_tests = []
        for test in test_data.get('conformance_tests', []):
            if isinstance(test, str):
                conformance_tests.append({"standard": test})
            else:
                conformance_tests.append(test)

        return Testing(
            unit_tests=unit_tests,
            integration_tests=integration_tests,
            conformance_tests=conformance_tests
        )

    @staticmethod
    def process_code_style(data: Dict[str, Any]) -> CodeStyle:
        """Process code style requirements"""
        style = data.get('code_style', {})
        return CodeStyle(
            indentation=style.get('indentation', []),
            comments=style.get('comments', []),
            naming=style.get('naming', []),
            organization=style.get('organization', [])
        )

class OutputFormatter:
    """Formats specification for output"""
    
    @staticmethod
    def format_text(spec: Specification) -> str:
        """Format specification as text"""
        lines = []
        
        # Metadata
        lines.append("=== SPECIFICATION ===")
        lines.append(f"Name: {spec.metadata['name']}")
        lines.append(f"Version: {spec.metadata['version']}")
        lines.append(f"Description: {spec.metadata['description']}")
        lines.append("")
        
        # Header Format
        lines.append("=== HEADER FORMAT ===")
        lines.append(f"Border Line: {spec.header_format.border_line}")
        lines.append("Assembly Lines:")
        for line in spec.header_format.assembly_lines:
            lines.append(f"  {line}")
        lines.append("Directives:")
        for directive in spec.header_format.directives:
            lines.append(f"  {directive}")
        lines.append("")
        
        # Register Usage
        lines.append("=== REGISTER USAGE ===")
        for reg in spec.register_usage.general_purpose:
            lines.append(f"Register: {reg.name}")
            lines.append(f"Purpose: {reg.purpose}")
            if reg.byte_regs:
                lines.append(f"Byte Registers: {', '.join(reg.byte_regs)}")
            if reg.constraints:
                lines.append("Constraints:")
                for constraint in reg.constraints:
                    lines.append(f"  - {constraint}")
            lines.append("")
        
        # Data Structures
        lines.append("=== DATA STRUCTURES ===")
        for name, struct in spec.structures.items():
            lines.append(f"Structure: {name}")
            lines.append(f"Documentation: {struct.documentation}")
            lines.append("Fields:")
            for field in struct.fields:
                lines.append(f"  {field.name} ({field.type}): {field.description}")
            if struct.constraints:
                lines.append("Constraints:")
                for constraint in struct.constraints:
                    lines.append(f"  - {constraint}")
            lines.append("")
        
        # Algorithms
        lines.append("=== ALGORITHMS ===")
        for name, algo in spec.algorithms.items():
            lines.append(f"Algorithm: {name}")
            lines.append(f"Description: {algo.description}")
            
            # Implementation Requirements
            lines.append("Implementation Requirements:")
            lines.append("  Memory Operations:")
            for op in algo.implementation_requirements.memory_operations:
                lines.append(f"    - {op}")
            lines.append("  Encoding Requirements:")
            for req in algo.implementation_requirements.encoding_requirements:
                lines.append(f"    - {req}")
            lines.append("  Leftover Handling:")
            for handling in algo.implementation_requirements.leftover_handling:
                lines.append(f"    - {handling}")
            lines.append("  Padding Rules:")
            lines.append("    One Byte:")
            for rule in algo.implementation_requirements.padding_rules.one_byte:
                lines.append(f"      - {rule}")
            lines.append("    Two Bytes:")
            for rule in algo.implementation_requirements.padding_rules.two_bytes:
                lines.append(f"      - {rule}")
            
            # Steps
            lines.append("Steps:")
            for step_name, step_actions in algo.steps.items():
                lines.append(f"  {step_name}:")
                for action in step_actions:
                    lines.append(f"    - {action}")
            
            # Additional Info
            if algo.edge_cases:
                lines.append("Edge Cases:")
                for case in algo.edge_cases:
                    lines.append(f"  - {case}")
            if algo.preconditions:
                lines.append("Preconditions:")
                for pre in algo.preconditions:
                    lines.append(f"  - {pre}")
            if algo.postconditions:
                lines.append("Postconditions:")
                for post in algo.postconditions:
                    lines.append(f"  - {post}")
            if algo.invariants:
                lines.append("Invariants:")
                for inv in algo.invariants:
                    lines.append(f"  - {inv}")
            lines.append("")
        
        # Error Handling
        lines.append("=== ERROR HANDLING ===")
        lines.append("Strategies:")
        if isinstance(spec.error_handling.strategies, dict):
            for strategy_name, strategy_steps in spec.error_handling.strategies.items():
                lines.append(f"  {strategy_name}:")
                for step in strategy_steps:
                    lines.append(f"    - {step}")
        elif isinstance(spec.error_handling.strategies, list):
            for step in spec.error_handling.strategies:
                lines.append(f"  - {step}")
        
        lines.append("Error Types:")
        for error in spec.error_handling.error_types:
            lines.append(f"  {error.name}:")
            lines.append(f"    Description: {error.description}")
            lines.append("    Handling:")
            for handle in error.handling:
                lines.append(f"      - {handle}")
        
        lines.append("Syscall Requirements:")
        for req in spec.error_handling.syscall_requirements:
            lines.append(f"  - {req}")
        lines.append("")
        
        # Section Requirements
        lines.append("=== SECTION REQUIREMENTS ===")
        lines.append("Data Section:")
        for req in spec.section_requirements.data:
            lines.append(f"  - {req}")
        
        lines.append("BSS Section:")
        for var in spec.section_requirements.bss:
            lines.append(f"  {var.name}:")
            lines.append(f"    Size: {var.size}")
            lines.append(f"    Align: {var.align}")
            lines.append(f"    Purpose: {var.purpose}")
        
        lines.append("Text Section:")
        for category, reqs in spec.section_requirements.text.items():
            lines.append(f"  {category}:")
            for req in reqs:
                lines.append(f"    - {req}")
        lines.append("")
        
        # Performance
        lines.append("=== PERFORMANCE ===")
        lines.append(f"Time Complexity: {spec.performance.time_complexity}")
        lines.append(f"Space Complexity: {spec.performance.space_complexity}")
        
        lines.append("Constraints:")
        for constraint in spec.performance.constraints:
            lines.append(f"  - {constraint}")
        
        lines.append("Register Usage:")
        for usage in spec.performance.register_usage:
            lines.append(f"  - {usage}")
        
        lines.append("Memory Access:")
        for access in spec.performance.memory_access:
            lines.append(f"  - {access}")
        
        lines.append("Benchmarks:")
        for bench in spec.performance.benchmarks:
            lines.append(f"  {bench.name}:")
            lines.append(f"    Input Size: {bench.input_size}")
            if bench.expected_time:
                lines.append(f"    Expected Time: {bench.expected_time}")
            if bench.requirements:
                lines.append("    Requirements:")
                for req in bench.requirements:
                    lines.append(f"      - {req}")
        lines.append("")
        
        # Testing
        lines.append("=== TESTING ===")
        lines.append("Unit Tests:")
        for test in spec.testing.unit_tests:
            lines.append(f"  {test.name}:")
            lines.append(f"    Input: {test.input}")
            lines.append(f"    Expected Output: {test.expected_output}")
            if test.validation:
                lines.append("    Validation:")
                for val in test.validation:
                    lines.append(f"      - {val}")
        
        lines.append("Integration Tests:")
        for test in spec.testing.integration_tests:
            lines.append(f"  {test['name']}:")
            for key, value in test.items():
                if key != 'name':
                    if isinstance(value, list):
                        lines.append(f"    {key}:")
                        for item in value:
                            lines.append(f"      - {item}")
                    else:
                        lines.append(f"    {key}: {value}")
        
        lines.append("Conformance Tests:")
        for test in spec.testing.conformance_tests:
            lines.append(f"  Standard: {test['standard']}")
            if 'test_vectors' in test:
                lines.append("  Test Vectors:")
                for vector in test['test_vectors']:
                    lines.append(f"    Input: {vector['input']}")
                    lines.append(f"    Output: {vector['output']}")
        lines.append("")
        
        # Code Style
        lines.append("=== CODE STYLE ===")
        lines.append("Indentation:")
        for ind in spec.code_style.indentation:
            lines.append(f"  - {ind}")
        
        lines.append("Comments:")
        for comment in spec.code_style.comments:
            lines.append(f"  - {comment}")
        
        lines.append("Naming:")
        for name in spec.code_style.naming:
            lines.append(f"  - {name}")
        
        lines.append("Organization:")
        for org in spec.code_style.organization:
            lines.append(f"  - {org}")
        
        return "\n".join(lines)
        


class SpecForge:
    """Main class for handling specification generation"""
    
    def __init__(self, 
                 template_dir: Optional[Path] = None,
                 languages_dir: Optional[Path] = None,
                 cache_enabled: bool = True):
        self.template_dir = template_dir or Path("templates")
        self.languages_dir = languages_dir or Path("languages")
        self.processor = SpecificationProcessor()
        self.cache = Cache() if cache_enabled else None
    
    def process_spec(self, spec_data: Dict[str, Any], output_format: str = 'text') -> str:
        """Process specification data and generate output"""
        try:
            # Create specification object
            spec = self._create_specification(spec_data)
            
            # Generate output
            return OutputFormatter.format_text(spec)
            
        except Exception as e:
            logger.error(f"Error processing specification: {e}")
            raise SpecForgeError(f"Failed to process specification: {str(e)}")
    
    def _create_specification(self, data: Dict[str, Any]) -> Specification:
        """Create Specification object from raw data"""
        try:
            return Specification(
                metadata=self.processor.process_metadata(data),
                header_format=self.processor.process_header_format(data),
                register_usage=self.processor.process_register_usage(data),
                structures=self.processor.process_data_structures(data),
                algorithms=self.processor.process_algorithms(data),
                error_handling=self.processor.process_error_handling(data),
                section_requirements=self.processor.process_section_requirements(data),
                performance=self.processor.process_performance(data),
                testing=self.processor.process_testing(data),
                code_style=self.processor.process_code_style(data)
            )
        except KeyError as e:
            raise ValidationError(f"Missing required field: {e}")
        except Exception as e:
            raise SpecForgeError(f"Error creating specification: {str(e)}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="SpecForge: Production-Quality Specification Generator"
    )
    parser.add_argument(
        "command",
        choices=["forge"],
        help="Command to execute"
    )
    parser.add_argument(
        "spec_file",
        type=Path,
        help="Path to the .specforge.yaml file"
    )
    parser.add_argument(
        "--format",
        choices=['text'],  # Currently only supporting text format
        default="text",
        help="Output format"
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        help="Custom template directory"
    )
    parser.add_argument(
        "--languages-dir",
        type=Path,
        help="Custom languages directory"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Ensure spec file exists
        if not args.spec_file.exists():
            logger.error(f"Specification file not found: {args.spec_file}")
            sys.exit(1)

        # Load specification
        try:
            with open(args.spec_file, 'r', encoding='utf-8') as f:
                spec_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML: {e}")
            sys.exit(1)

        # Initialize SpecForge
        specforge = SpecForge(
            template_dir=args.template_dir,
            languages_dir=args.languages_dir,
            cache_enabled=not args.no_cache
        )

        # Process specification
        output = specforge.process_spec(
            spec_data,
            output_format=args.format
        )

        # Print output
        print(output)

    except SpecForgeError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            logger.exception("Detailed error information:")
        sys.exit(1)

if __name__ == "__main__":
    main()
