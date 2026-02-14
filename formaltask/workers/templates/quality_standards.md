<quality_standards>
## Testing Anti-Patterns to Avoid

- **Mock abuse**: Only mock external deps (APIs, DB, network)
- **Use real objects** for validators, business logic, internal code
- **Test behavior**, not implementation details
- **One behavior per test** - keep tests under 20 lines
- **Descriptive names**: test_<component>_<scenario>_<expected>
</quality_standards>
