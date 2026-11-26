# PD-SPEC-REVIEW

**Agent**: `product-director`  
**Phase**: requirements  
**Lean**: yes  
**Trigger**: A functional spec is drafted or revised  
**Context to pass**: The spec path and the product vision  
**Verdicts**: APPROVE / CONCERNS / REJECT

Verdict words are ordered best first; the last is the failing word.

## Prompt

Does the spec serve the vision, stay in scope and give testable acceptance criteria?

## How to answer

Begin with `PD-SPEC-REVIEW: <word>` on its own line, using only the words above — or `PD-SPEC-REVIEW: NOT ASSESSED` when an input this gate names was not given to you or could not be read; name that input. A problem you did find takes the gate's own word, and so does an artifact the calling skill reports as absent: a missing artifact is a finding, not a missing input.
