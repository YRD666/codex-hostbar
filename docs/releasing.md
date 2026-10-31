# Release checklist

1. Run `python3 -m unittest discover -s tests -v` on Linux with tmux 3.4+.
2. Run `python3 scripts/check_public.py` and inspect every staged diff.
3. Review `git ls-files` and the complete commit history. No machine snapshots,
   `.codex` directories, auth files, SSH files, logs, proxy configuration or local
   deployment backups belong in this repository. `.gitignore` alone is not a
   security check. The included scanner is heuristic, not a guarantee.
4. Validate a real Codex launch: two adjacent rows, 80/100/120-column resize,
   warning panel, draft input, copy mode and Ctrl+Z. Use a disposable test session;
   never inject keys into someone else's active conversation.
5. Review version, compatibility claims and license. Use synthetic screenshots
   or sample text, never real conversations or account usage snapshots.
6. Create the source archive from committed, reviewed files with `git archive`.
   Inspect the archive entries before publishing.

CI uses only synthetic fixtures and never requires Codex authentication or an API
key. Please report potential leaks privately through GitHub's private reporting
feature if the repository has enabled it; do not paste secrets in public issues.
