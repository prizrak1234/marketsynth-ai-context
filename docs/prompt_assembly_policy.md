# Prompt Assembly Policy

Single assembler: `app/prompts/specialist/assembler.py`.

## Order

1. Constitutional policy
2. Specialist role
3. Skill instruction
4. Approved knowledge snapshot
5. User request + structured inputs
6. Output schema
7. Quality gates
8. Tool policy
9. Locale / style

Do not hand-build prompts in React, routes or provider adapters.
