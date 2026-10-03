# AGENTS.md

## Documentation

- **Always keep `docs/README.ru.md` in sync with `README.md`.** Any change to one must be mirrored in the other in the same commit: same features, same sections, same links, same code blocks. The English README is the source; the Russian one is a full translation, never a summary. New sections must be added to both, and version numbers, engine names and commands must match exactly.

## Tests

- Every behavioural change needs tests. Run the fast suite with `python -m pytest`.
- The end-to-end suite needs an engine binary and is opt-in: `DEEPSIGHT_RUN_ENGINE_TESTS=1 python -m pytest`.