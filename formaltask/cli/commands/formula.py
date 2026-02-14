"""Formula CLI commands for template management.

Provides:
- list: List available formulas from .claude/formulas/
- cook: Generate YAML from template with variable substitution
- batch: Generate multiple YAMLs from config file
"""

from pathlib import Path

import yaml

COMMAND_NAME = "formula"
COMMAND_HELP = "Manage formula templates for epic generation"


def setup_parser(subparser):
    """Set up argument parser for formula command with subcommands."""
    subparsers = subparser.add_subparsers(dest="subcommand", help="Formula subcommands")

    # List subcommand
    list_parser = subparsers.add_parser("list", help="List available formulas")
    list_parser.add_argument(
        "--formulas-dir",
        default=".claude/formulas",
        help="Directory containing formulas (default: .claude/formulas)",
    )

    # Cook subcommand
    cook_parser = subparsers.add_parser("cook", help="Generate YAML from formula")
    cook_parser.add_argument("formula", help="Formula name or path")
    cook_parser.add_argument(
        "--set",
        action="append",
        dest="variables",
        metavar="VAR=value",
        help="Set variable (can be repeated)",
    )
    cook_parser.add_argument(
        "--output",
        required=True,
        help="Output file path",
    )
    cook_parser.add_argument(
        "--formulas-dir",
        default=".claude/formulas",
        help="Directory containing formulas (default: .claude/formulas)",
    )

    # Batch subcommand
    batch_parser = subparsers.add_parser("batch", help="Generate multiple YAMLs from config")
    batch_parser.add_argument("config", help="Batch config YAML file")
    batch_parser.add_argument(
        "--output",
        required=True,
        help="Output directory",
    )


def execute(args) -> int:
    """Execute the formula command."""
    if args.subcommand == "list":
        return _execute_list(args)
    if args.subcommand == "cook":
        return _execute_cook(args)
    if args.subcommand == "batch":
        return _execute_batch(args)
    print("Error: No subcommand specified. Use --help for usage.")
    return 1


def _execute_list(args) -> int:
    """Execute the list subcommand."""
    formulas = list_formulas(args.formulas_dir)
    if not formulas:
        print("No formulas found")
        return 0

    print("Available formulas:")
    for name in sorted(formulas):
        print(f"  {name}")
    return 0


def _execute_cook(args) -> int:
    """Execute the cook subcommand."""
    # Parse variables from --set VAR=value
    variables = {}
    if args.variables:
        for var_str in args.variables:
            if "=" not in var_str:
                print(f"Error: Invalid variable format: {var_str}")
                print("Expected format: VAR=value")
                return 1
            name, value = var_str.split("=", 1)
            variables[name] = value

    # Resolve formula path
    formula_path = args.formula
    if not Path(formula_path).exists():
        # Try as name in formulas directory
        formulas_dir = Path(args.formulas_dir)
        potential_path = formulas_dir / f"{args.formula}.yaml"
        if potential_path.exists():
            formula_path = str(potential_path)
        else:
            print(f"Error: Formula not found: {args.formula}")
            return 1

    try:
        cook_formula(formula_path, variables, args.output)
        print(f"Generated: {args.output}")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1


def _execute_batch(args) -> int:
    """Execute the batch subcommand."""
    try:
        result = batch_cook(args.config, args.output)
        print(f"Generated {len(result)} files in {args.output}")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except ValueError as e:
        print(f"Error: {e}")
        return 1


def list_formulas(formulas_dir: str) -> list[str]:
    """List available formulas in the given directory.

    Args:
        formulas_dir: Path to directory containing formula YAML files

    Returns:
        List of formula names (without .yaml extension)
    """
    path = Path(formulas_dir)
    if not path.exists():
        return []

    formulas = []
    for file in path.iterdir():
        if file.suffix in (".yaml", ".yml"):
            formulas.append(file.stem)

    return formulas


def cook_formula(formula_path: str, variables: dict, output_path: str) -> None:
    """Cook a formula with variable substitution and write to output.

    Args:
        formula_path: Path to the formula YAML file
        variables: Dict mapping variable names to values
        output_path: Path to write the output YAML

    Raises:
        FileNotFoundError: If formula_path doesn't exist
    """
    from formaltask.epics.templates import load_template

    if not Path(formula_path).exists():
        raise FileNotFoundError(f"Formula not found: {formula_path}")

    template = load_template(formula_path)

    # Recursively substitute variables in all string values
    cooked = _substitute_recursive(template, variables)

    # Ensure parent directory exists
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w") as f:
        yaml.safe_dump(cooked, f, default_flow_style=False)


def _substitute_recursive(data, variables: dict):
    """Recursively substitute variables in nested data structures."""
    from formaltask.epics.templates import substitute_variables

    if isinstance(data, str):
        return substitute_variables(data, variables)
    if isinstance(data, dict):
        return {k: _substitute_recursive(v, variables) for k, v in data.items()}
    if isinstance(data, list):
        return [_substitute_recursive(item, variables) for item in data]
    return data


def batch_cook(config_path: str, output_dir: str) -> list[str]:
    """Batch cook multiple entities from a config file.

    Args:
        config_path: Path to the batch config YAML file
        output_dir: Directory to write output files

    Returns:
        List of generated file paths

    Raises:
        FileNotFoundError: If config_path doesn't exist
        ValueError: If config is missing required keys
    """
    if not Path(config_path).exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    if "formula" not in config:
        raise ValueError("Config must contain 'formula' key")

    formula_path = config["formula"]
    entities = config.get("entities", [])

    # Create output directory
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    generated = []
    for entity in entities:
        # Use NAME variable as filename, or generate one
        name = entity.get("NAME", f"entity-{len(generated)}")
        output_path = output / f"{name}.yaml"

        cook_formula(formula_path, entity, str(output_path))
        generated.append(str(output_path))

    return generated
