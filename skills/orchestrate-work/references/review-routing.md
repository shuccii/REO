# Risk-based review planning

Use `python3 <plugin root>/tools/review_routing.py` or import `route_review(...)`
from that module to record an observable routing recommendation before review.
The tool uses only the standard library and makes no paid calls. Its JSON is a
planning artifact; v0.3 manifest/result schemas and validation gates are unchanged.
See `<plugin root>/docs/REVIEW_ROUTING.md` for the full API and input vocabulary.

1. Classify the actual scope. Only purely mechanical work without semantic risk
   takes `single_agent`; check its artifact directly. Code changes still require
   independent semantic review. Unknown scope routes conservatively to review.
2. Research, statistical design, leakage, interpretation, and central claims
   automatically retain `research_strict`, manifests and research contracts.
   Quick mode changes optional depth only. It never waives required gates.
3. Supply only observed independent reviewer identities, excluding implementers.
   Keep requested, proposed assigned, and actual reviewer identities distinct.
   One reviewer may cover several required gates when qualified; do not create
   agents solely to fill one role per gate. Preserve evidence for every gate.
4. With a hard budget, supply real observed usage in `tokens` or `llm_calls`,
   the limit and an estimate reserving remaining work plus review. Unknown usage
   or estimates block as `budget_unobservable`; insufficient remaining budget
   blocks as `budget_exceeded`. Never substitute turns/tool counts for either.
5. Unknown/unavailable independence blocks review as `resource_unavailable`.
   Attempt an unavailable spawn only once. Continue safe implementation separately
   if useful, but keep integration incomplete until an identifiable reviewer returns
   real evidence. Do not mark an implementation completed to avoid its review gate.

The plan includes exact rule `reasons`, `requested_reviewers`, proposed
`assigned_reviewers`, `actual_reviewers=[]`, `review_completed=False`, budget and
availability statuses, all blocking reasons, retry guidance and next actions.
`ready_for_review` means prerequisites appear available from supplied inputs;
it is not executed or passed review. The tool cannot verify caller assertions,
spawn agents, observe runtime cost, or approve integration.

When constraints bind, reduce optional scope or change the prerequisite/budget;
preserve all integrity checks and independent review. Never retry unchanged blocked
work. Use at most two repair/re-review rounds after the initial review, capped by
the smaller caller budget; stop immediately for critical integrity failures.
Retry rounds are workflow control, not token accounting. Follow
[execution, review and recovery](execution-control.md) for actual two-stage review,
finding resolution, current-artifact verification and completion evidence.
