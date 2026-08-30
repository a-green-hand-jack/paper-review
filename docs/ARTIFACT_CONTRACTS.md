# Open ScholarPeer Artifact Contracts

The batch runner copies this file into each isolated workspace so the
orchestrator can validate phase boundaries without searching outside the
workspace.

| Phase | Required inputs | Expected outputs |
|---|---|---|
| onboarding | session, paper input | guidelines, parsed paper, session state |
| summary | parsed paper, session | `raw/01_structured_summary.md` |
| literature | structured summary | `raw/02_retrieved_literature.md` and round artifacts |
| historian | summary, literature | `raw/03_domain_narrative.md` |
| baseline scout | summary, literature | `raw/04_missing_baselines.md` |
| qa | summary, literature, historian, baselines | `raw/05_qa_*.md` |
| review | all prior artifacts and QA files | `review/final_review.md` |

All raw artifacts use the universal `Method`, `Output`, and `Provenance`
sections defined by the OSP project rules.
