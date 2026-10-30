# Risk-based review routing (0.16)

`tools/review_routing.py` provides a deterministic, standard-library-only review
plan. It does not call an LLM, start an agent, validate a scientific result, or
prove that review happened. Keep its output separate from v0.3 manifest/result
contracts: it introduces no replacement result status or schema fields.

## Routing rules

| Observed task/risk | Route | Assurance |
| --- | --- | --- |
| Mechanical transformation/check, no risk flags and no requested reviewer | Single agent; perform direct artifact checks | Standard |
| Implementation change, external fact, security-sensitive work, job claim | Independent semantic review | Standard unless another rule requires strict |
| Research, statistical design, leakage, central claim, research conclusion, interpretation | Independent semantic review | Research strict |
| Unknown task scope | Independent semantic review; resolve uncertain scope | Standard unless research applies |
| Explicit research strict assurance | Independent semantic review, manifest and research contract | Research strict |
| Explicit named reviewers | Independent semantic review; preserve requested identities | Determined by task/risk |

Only an explicitly mechanical task takes the direct path. A short code change is
still an implementation change. Mechanical checks or a small diff do not establish
semantic safety. Quick mode may reduce optional narrative, reading depth, and
delegation overhead; it cannot change mandatory review, scientific validity,
leakage, approval, or provenance requirements. All modes use the same risk rules.

The planner recommends one independent reviewer by default; research strict does
not automatically require a separate agent for each research gate. One suitably
qualified independent reviewer may cover the required scope, recording each gate
and its evidence. More reviewers can be explicitly requested. Existing mandatory
review coverage and two-stage requirements/integrity checks still apply.

## API

```python
from review_routing import route_review

plan = route_review(
    task_kind='implementation',
    risks=['implementation_change'],
    mode='quick',
    assurance='standard',
    requested_reviewers=None,
    available_reviewers=['observed-independent-agent-id'],
    budget={'metric': 'tokens', 'limit': 12000, 'used': 2000,
            'required': 5000, 'observable': True, 'retry_limit': 1},
)
```

All arguments are keyword-only and optional. `task_kind` defaults to `unknown`,
`risks` to `[]`, `mode` and `assurance` to `standard`. Supported task/risk names are
exported as `TASK_KINDS` and `RISK_KINDS`; risk names include the existing v0.3
manifest risk tags plus `central_claim` and `interpretation` as planner inputs.
These two planner labels must not be inserted into the manifest risk-tag enum.
Duplicate risks are sorted/deduplicated; duplicate reviewer identities and invalid
inputs raise `ValueError`. The caller remains responsible for accurate scope/risk
classification, reviewer independence, identity observation and runtime enforcement.

`requested_reviewers=None` requests the default independent reviewer role when
needed. A supplied list requests those exact identities, all of which must be
available. An explicit empty list is preserved in the output but cannot remove
mandatory review. `available_reviewers=None` means availability is unknown;
`[]` means no independent reviewer is available. The caller must exclude the
implementer from that pool. Preserve tool-returned identities verbatim.

Outputs include:

- `route`: `single_agent` or `independent_semantic_review`.
- `reasons`: exact rule codes, ordered as task, sorted risks, strict assurance,
  then explicit request; `mechanical_only` is the direct-route reason.
- `status`: `ready_for_direct_checks`, `ready_for_review`, or `blocked`. None
  of these is a completed v0.3 task result.
- `requested_reviewers`, `required_reviewer_count` and `assigned_reviewers`:
  requested roles/identities and proposed assignments from the supplied pool.
- `actual_reviewers=[]`, `review_completed=False` and `plan_only=True`: fixed
  reminders that this helper has not performed or observed a review.
- `availability_status`: `not_required`, `unknown`, `unavailable`, or `available`.
- `budget_status`, full `budget`, ordered `blocked_reasons` and a primary
  `blocked_reason` compatible with existing blocked-reason names.
- Required gate flags, retry guidance, limitations and concrete `next_actions`.

A proposed assigned identity is not an actual spawned reviewer. After a real
spawn, preserve its returned identity in the execution record and retain observed
review artifacts. Integration requires actual checks and independent review
evidence; do not transform this recommendation into a passing semantic-review
check. If spawning is unavailable/fails, attempt it once, record the reviewer task
as blocked/resource unavailable, and leave integration incomplete. Safe local
implementation may continue separately within its authorization and budget.

## Budget and retries

Without `limit` there is no hard budget constraint. With `limit`, supply `metric`
(`tokens` or `llm_calls`), observed `used` and estimated `required` reservation for
the remaining planned work including review. Supplying numeric usage asserts it
was observed unless `observable=False` is explicitly supplied. Missing measurement,
missing estimate or explicitly unobservable usage blocks with `budget_unobservable`.
Turns/tool counts are rejected as budget metrics and cannot stand in for tokens
or LLM calls. LLM-call values must be whole counts; numbers must be finite and
nonnegative. `remaining = limit - used`; exact equality with `required` is sufficient.
Insufficient remaining budget blocks with `budget_exceeded`. Runtime expenditure
must still be measured separately; an estimate never guarantees future usage.

When budget and reviewer availability both fail, retain both blocking reasons.
Do not silently switch a scientific method, remove an integrity check, waive
independence, or label pending work complete to fit the budget. Reduce optional
scope, reuse immutable evidence only after provenance inspection, or revise the
budget/prerequisite. Never retry unchanged blocked work.

`retry_limit` counts repair/re-review rounds after the initial review; it is not
token accounting. It defaults to two, is capped at two, and respects a smaller
nonnegative integer limit, including zero. Critical integrity failures stop the
loop immediately. The caller tracks attempts and stops when the limit is reached;
this stateless helper does not run or count retries.

## CLI

```sh
python3 /path/to/plugin/tools/review_routing.py --task-kind mechanical
python3 /path/to/plugin/tools/review_routing.py --task-kind research \
  --mode quick --risks statistical_design data_leakage \
  --available-reviewers observed-agent-id \
  --budget-json '{"metric":"llm_calls","limit":8,"used":2,"required":3,"observable":true}'
```

Reviewer/risk flags accept space-separated lists. Omitting available reviewers
leaves them unknown; passing `--available-reviewers` with no names records known
unavailability. Output is JSON. Exit 0 means the plan has no identified prerequisite
block; it does not mean the work passed review. Exit 2 means a blocked plan or
invalid CLI input (invalid input prints argparse diagnostics rather than a plan).

## Unified entrypoint

`python3 <plugin root>/tools/reo.py plan --mode quick --task peer_review --available-reviewer reviewer-1` combines the reading plan and research-strict review route. Omit the reviewer if unavailable; the planner explicitly returns the pending gate (exit 2). This does not block safe reading or preliminary lead-only feedback, but it cannot certify integration.

`python3 <plugin root>/tools/reo.py route --task-kind mechanical` plans direct deterministic checks. `--risk` may be repeated; `--available-reviewer` and `--budget-json` use the same contract. A manually supplied classification is not independently verified by the tool.
