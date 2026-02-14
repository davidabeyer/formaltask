# ft formula

Manage formula templates for epic generation

## formula batch

```
ft formula batch [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `config` | Batch config YAML file **(required)** | - |
| `--output` | Output directory **(required)** | - |

## formula cook

```
ft formula cook [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `formula` | Formula name or path **(required)** | - |
| `--set` | Set variable (can be repeated) | - |
| `--output` | Output file path **(required)** | - |
| `--formulas-dir` | Directory containing formulas (default: .claude/formulas) | `.claude/formulas` |

## formula list

```
ft formula list [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `--formulas-dir` | Directory containing formulas (default: .claude/formulas) | `.claude/formulas` |
