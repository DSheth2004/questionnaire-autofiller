# Sources

Every document this project runs on is real and publicly published. Nothing is invented.

## Policy library: GitLab's security policies

GitLab Inc. publishes its information security policies and standards openly in the GitLab Handbook.
The 25 documents used here (access management, cryptography, logging, incident response, third-party
risk, business continuity, password, data classification and more) are fetched by
`scripts/fetch_sources.py` from the handbook's source repository:

- Repository: https://gitlab.com/gitlab-com/content-sites/handbook
- Pinned commit: `ddc319726d9e3f1cfd7f88faf4798bf31af6bf10`
- Published at: https://handbook.gitlab.com/handbook/security/

Every chunk keeps the public handbook URL of the page it came from, so each drafted answer links back
to GitLab's live page. Copyright GitLab B.V.; see the repository's LICENSE and the handbook for terms.

## Questionnaire: Google VSAQ

Google's Vendor Security Assessment Questionnaire, an open-source questionnaire Google used to assess
vendors. Three questionnaires (security & privacy programs, infrastructure, web application) give
126 real questions.

- Repository: https://github.com/google/vsaq (Apache License 2.0, copy in `data/raw/vsaq/LICENSE`)

## Gold evaluation set

`eval/gold.jsonl` holds 42 VSAQ questions. For 32 of them the GitLab policy documents that
answer the question are labelled, each checked by reading the cited sections. The other 10 are questions GitLab's published
policies do not answer (for example firewalls/DMZ, Wi-Fi, background checks for employees), so the
correct behaviour is to flag them for human review.
