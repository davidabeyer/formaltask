# Lens 5: Service Dependencies

Find external service requirements that may block users without specific accounts or API access.

## Search Patterns

```python
# API key patterns
Grep(pattern="API_KEY|api_key|apiKey|ANTHROPIC|OPENAI|OPENROUTER", output_mode="content")

# HTTP client usage
Grep(pattern="requests\\.(get|post|put)|httpx\\.|urllib\\.request", output_mode="content")

# Specific service URLs
Grep(pattern="api\\.openai|api\\.anthropic|openrouter\\.ai|api\\.github", output_mode="content")

# Database connection strings
Grep(pattern="postgres://|mysql://|mongodb://|redis://", output_mode="content")

# Cloud service SDKs
Grep(pattern="boto3|google\\.cloud|azure\\.", output_mode="content")
```

## Blocker Criteria

| Pattern | Severity | Rationale |
|---------|----------|-----------|
| API key required at import | Blocker | Fails before user can set up |
| External service call in init | Blocker | Network required to import |
| Paid API with no mock option | Warning | Users must pay to test |
| Undocumented service requirement | Blocker | Can't discover dependency |
| No offline/mock mode for tests | Warning | Tests require network |

## Service Dependency Audit

For each external service:
1. Is it documented in README?
2. Can code run without it (graceful degradation)?
3. Is there a mock/stub for testing?
4. Are rate limits/costs documented?
5. What happens on network failure?

## Acceptable Patterns

```python
# Good: Lazy initialization
class LLMClient:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise ConfigError("Set OPENROUTER_API_KEY for LLM features")
            cls._client = OpenRouter(api_key=api_key)
        return cls._client

# Good: Optional feature
def summarize_text(text):
    """Summarize text. Requires OPENROUTER_API_KEY."""
    if not os.environ.get("OPENROUTER_API_KEY"):
        return text[:500] + "..."  # Fallback: truncate
    return call_llm(text)

# Good: Mock support for tests
@pytest.fixture
def mock_llm(monkeypatch):
    def mock_call(*args, **kwargs):
        return {"response": "mocked"}
    monkeypatch.setattr("hooks.lib.llm.call_openrouter", mock_call)

# Good: Network error handling
def fetch_data(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.warning(f"Network error: {e}")
        return None  # Graceful degradation
```

## Service Documentation Template

Document each service in README:

```markdown
## External Services

### OpenRouter (LLM)
- **Required for:** Smart summaries, code analysis
- **Get API key:** https://openrouter.ai/keys
- **Env var:** `OPENROUTER_API_KEY`
- **Cost:** ~$0.01 per 1K tokens
- **Fallback:** Basic functionality works without it
```

## Output Fields

```json
{
  "id": "L5-001",
  "severity": "blocker",
  "category": "required_api",
  "service": "OpenRouter",
  "location": {"file": "hooks/lib/llm.py", "line": 5},
  "required_at": "import",
  "documented": false,
  "fallback_exists": false,
  "mock_available": false,
  "fix": "Move API key check to first use, add to README, create mock for tests"
}
```
