# EventProcessor tutorial verification

The published tutorial is in `{zh,en,ja}/plugin/dev/components/event-processor.mdx`.
All three translations contain identical executable Python and component YAML.
Run the example checks with the SDK used by your LangBot installation.

## Repeatable checks

The API references in `{zh,en,ja}/plugin/dev/apis/` are also checked against the
installed SDK. Run `python scripts/verify-plugin-api-examples.py` to execute
the examples, validate method arguments, and check translated code parity.
The Host transport is mocked; this does not verify external delivery.

With the matching SDK installed in the active Python environment:

```bash
python scripts/verify-event-processor-tutorial.py
```

This extracts the actual MDX examples, compares all translations, loads the
component, applies YAML defaults, and executes ten cases. They cover member names
and ID fallback, private/group commands, disabled replies, ordinary/empty/image
messages, and a failed delivery that must retain its logs without completing.
Its tool API is mocked; it does not claim platform delivery.

With Node.js 24 or later:

```bash
npm ci
npm test
npm run typecheck
npm run build
```

The build also checks static HTML, Markdown exports, navigation, canonical URLs,
alternate languages, and preservation of legacy documentation routes.

The companion `langbot-plugin-demo/EventProcessorDemo` repository contains
`examples/event-matrix.json` and `scripts/event_matrix.py`. See its README for
authenticated Host checks covering all 17 event types and invalid payloads.
Use a dedicated observer instance with payload logging enabled and no Bot binding.

## Verified development snapshot: 2026-09-09

Documentation work started from the updated `langbot-app/langbot-docs` main commit
`a86ecb4`, on branch `docs/4.11-event-processor`. The local directory still uses
the previous name `langbot-wiki`.

The tested SDK was `dev/4.11.x` at
`f82b3ce935f9a33afee389fb39fe8dc29a45b615`, both as a freshly built wheel and via
a Git installation from the matching SDK branch in an isolated Python 3.12 environment.
The Host was `dev/4.11.x` at `ea3e32c` with local processor UI refinements.

| Layer | Observed result |
| --- | --- |
| Documentation | 36 Node tests, 6 Python tests, TypeScript check and full build passed; all 30 post-build static checks passed |
| SDK CLI, packaging and event tests | 246 passed, including 92 new event-matrix cases and packaged CLI execution of generated EventProcessor/AgentRunner components |
| Host processor service and run ledger | 73 passed |
| Platform EBA conversion, routing and run-log authorization | 212 passed |
| EventProcessorDemo unit tests | 8 passed, including scenario subtests, lookup errors and instance isolation |
| Installed observer through HTTP → Host → Runtime | 48 passed: 42 valid cases and 6 rejected inputs; one completed run per valid input |
| Tutorial via developer Runtime and installed package | Both workflows passed; final installed checks cover 9 valid cases plus unsupported-event rejection |
| Python extracted from all three tutorial pages | 10 passed, also using the SDK installed from Git |
| Local OneBot transport → adapter → binding → installed processor | 5 passed: unbound, bound, disabled, higher priority and equal-priority order |
| Authenticated browser tutorial | Selected member joined, entered Alice/alice/tutorial-group, clicked once; one reply trace, one completed run, and automatic switch to Logs |

The generated AgentRunner was also connected with `lbp run` and invoked through
the real Host, producing its expected echo. The tutorial EventProcessor was built
and uploaded as `tutorial-WelcomeEvents-0.1.0.lbpkg`; it continued to work after
the developer process stopped and the Host restarted.

The localhost OneBot peer received exactly one `send_group_msg` in the bound and
equal-priority cases. Other cases sent none. It exercised normal routing, not the
debug Mock, but the remote platform was simulated locally: this is not evidence
of delivery through QQ or every other third-party service. Original QA Bot
bindings and the local extension limit were restored after testing.

Python hot reload worked during development. Component YAML and manifest changes
required restarting `lbp run`; the tutorial explicitly documents that boundary.

This matrix covers the registered event model and representative data, failure,
concurrency and routing branches. Arbitrary plugin business logic and every real
platform/account combination require their own integration checks. Local passes
are not a CI, publication or deployment result.
