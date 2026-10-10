"""Machine gate for every push to main (runs in build-and-publish before anything is published).

World loop: a push that only touches world data (new eras, their chronicles, names, people, documents)
is accepted when the rebuilt world passes engine/check.py and the tests. No PR, no human, no agent review.

Rules loop: a push that touches anything else (engine, rules, workflows, AGENTS/HEARTBEAT, published
history) is accepted only when it is the merge of a pull request on which a human, not an app, posted a
comment starting with 批准 after the PR's last commit. Every agent here acts through a GitHub App, so its
comments carry performed_via_github_app; the owner's own comments from the web or phone do not.

The workflow runs the copy of this file that was on main *before* the push, so a push cannot loosen
the gate that judges it. On failure the workflow reverts the push and opens an issue."""
import fnmatch, json, os, subprocess, sys, urllib.request

REPO, TOKEN = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
BEFORE, AFTER = os.environ["BEFORE"], os.environ["AFTER"]
DATA = ["proposals/era_*.json", "proposals/make_era_*.py", "chronicle/*.md", "chronicle/en/*.md",
        "i18n/i18n.json", "persons/*", "documents/*", "documents/**/*"]
APPEND_ONLY = ["proposals/era_*.json", "chronicle/*.md", "chronicle/en/*.md"]  # published history: add, never edit


def api(path):
    r = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{path}",
                               headers={"Accept": "application/vnd.github+json", **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    return json.load(urllib.request.urlopen(r))


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def human_approved():
    prs = [p for p in api(f"commits/{AFTER}/pulls") if p.get("merged_at") and p.get("merge_commit_sha") == AFTER]
    if not prs:
        return False, "protected files changed outside a pull request"
    pr = prs[0]
    last = max(c["commit"]["committer"]["date"] for c in api(f"pulls/{pr['number']}/commits?per_page=100"))
    for c in api(f"issues/{pr['number']}/comments?per_page=100"):
        if c["body"].strip().startswith("批准") and c.get("performed_via_github_app") is None \
                and c["user"]["login"] == REPO.split("/")[0] and c["created_at"] > last:
            return True, f"PR #{pr['number']} approved by the owner ({c['html_url']})"
    return False, f"PR #{pr['number']} has no 批准 from the owner (posted by a person, not an app) after its last commit"


def main():
    if set(BEFORE) == {"0"}:
        print("first push: nothing to compare"); return 0
    rows = [l.split("\t") for l in git("diff", "--name-status", BEFORE, AFTER).splitlines() if l]
    protected = []
    for r in rows:
        st, f = r[0], r[-1]
        data = any(fnmatch.fnmatch(f, p) for p in DATA)
        edit_history = st[0] in "MDR" and any(fnmatch.fnmatch(f, p) for p in APPEND_ONLY)
        if not data or edit_history:
            protected.append(f"{st} {f}")
    if not protected:
        print(f"world data only ({len(rows)} files): accepted on check.py + tests"); return 0
    ok, why = human_approved()
    print(("RULES CHANGE ACCEPTED: " if ok else "REJECTED: ") + why)
    print("protected changes:\n  " + "\n  ".join(protected))
    if not ok:
        open(os.environ.get("GUARD_REASON", "/tmp/guard_reason"), "w").write(why + "\n\n" + "\n".join(protected))
    return 0 if ok else 1


sys.exit(main())
