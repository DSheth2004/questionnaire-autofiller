"""Download the real, publicly published source documents this project runs on.

Nothing here is invented. Two sources are pulled at pinned commits so results are reproducible:

* GitLab's security policies and standards, published in the GitLab Handbook
  (https://handbook.gitlab.com). GitLab is a public company that publishes its
  security policy set openly; we use it as the "company policy library".
* Google's open-source Vendor Security Assessment Questionnaire (VSAQ,
  https://github.com/google/vsaq, Apache-2.0), used as the incoming questionnaire.

Usage:  python scripts/fetch_sources.py
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

GITLAB_REPO = "https://gitlab.com/gitlab-com/content-sites/handbook.git"
GITLAB_COMMIT = "ddc319726d9e3f1cfd7f88faf4798bf31af6bf10"
VSAQ_REPO = "https://github.com/google/vsaq.git"
VSAQ_COMMIT = None  # repo is archived; HEAD is stable

GITLAB_DOCS = [
    "content/handbook/security/security-and-technology-policies/access-management-policy.md",
    "content/handbook/security/security-and-technology-policies/audit-logging-policy.md",
    "content/handbook/security/security-and-technology-policies/change-management-policy.md",
    "content/handbook/security/security-and-technology-policies/penetration-testing-policy.md",
    "content/handbook/security/security-and-technology-policies/software-development-lifecycle-policy.md",
    "content/handbook/security/security-and-technology-policies/security-and-technology-policies-management.md",
    "content/handbook/security/policies_and_standards/cryptographic-standard.md",
    "content/handbook/security/policies_and_standards/data-classification-standard.md",
    "content/handbook/security/policies_and_standards/password-standard.md",
    "content/handbook/security/policies_and_standards/physical-security-standard-for-company-assets.md",
    "content/handbook/security/policies_and_standards/records-retention-deletion.md",
    "content/handbook/security/policies_and_standards/security-logging-standard.md",
    "content/handbook/security/policies_and_standards/software-development-lifecycle-standard.md",
    "content/handbook/security/policies_and_standards/token-management-standard.md",
    "content/handbook/security/isms.md",
    "content/handbook/security/information-system-contingency-plan-iscp.md",
    "content/handbook/security/security-change-management-procedure.md",
    "content/handbook/security/security-observations-risk-management.md",
    "content/handbook/security/security-assurance/governance/sec-awareness-training.md",
    "content/handbook/security/security-assurance/security-compliance/access-reviews.md",
    "content/handbook/security/security-assurance/security-risk/third-party-risk-management.md",
    "content/handbook/security/security-operations/sirt/sec-incident-response.md",
    "content/handbook/security/product-security/vulnerability-management/sla.md",
    "content/handbook/business-technology/entapps-documentation/policies/gitlab-business-continuity-plan.md",
    "content/handbook/legal/acceptable-use-policy.md",
]

VSAQ_FILES = [
    "questionnaires/security_privacy_programs.json",
    "questionnaires/infrastructure.json",
    "questionnaires/webapp.json",
    "LICENSE",
]


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True)


def fetch_gitlab(tmp: Path):
    repo = tmp / "handbook"
    git("clone", "-q", "--filter=blob:none", "--no-checkout", GITLAB_REPO, str(repo))
    git("sparse-checkout", "set", "--no-cone", *GITLAB_DOCS, cwd=repo)
    git("checkout", "-q", GITLAB_COMMIT, cwd=repo)
    out = RAW / "gitlab"
    for rel in GITLAB_DOCS:
        dest = out / rel.removeprefix("content/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo / rel, dest)
    print(f"GitLab handbook: {len(GITLAB_DOCS)} documents @ {GITLAB_COMMIT[:10]}")


def fetch_vsaq(tmp: Path):
    repo = tmp / "vsaq"
    git("clone", "-q", "--depth", "1", VSAQ_REPO, str(repo))
    out = RAW / "vsaq"
    out.mkdir(parents=True, exist_ok=True)
    for rel in VSAQ_FILES:
        shutil.copy(repo / rel, out / Path(rel).name)
    print(f"Google VSAQ: {len(VSAQ_FILES) - 1} questionnaires")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as t:
        fetch_gitlab(Path(t))
        fetch_vsaq(Path(t))
