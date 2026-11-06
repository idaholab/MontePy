# Instructions for coding agents

Read `.github/copilot-instructions.md` first. It is the shared guide for all
coding agents. Keep it up to date rather than repeating it here. The developer guides are
`doc/source/dev_standards.rst` and `doc/source/dev_checklist.rst`.

## Pull requests and issues

**Do not create pull requests or issues through the API or CLI** (`gh pr create`,
`gh issue create`, `gh api`, MCP tools, etc.). They must be written by hand by a
human user. Machine-written PRs and issues cost maintainers review time and often
hide that nobody understood the change. Issues and PRs that do not conform to the
templates will be summarily closed.

- If asked to open one, decline, say why, and point the user to
  `.github/pull_request_template.md` and `.github/ISSUE_TEMPLATE/`.
- You may still do the work around it: write and test code on a branch, investigate
  a bug, check whether it exists on `develop` and in the latest release, search for
  duplicate issues, and run the template's checklists (`black`, tests with
  `coverage run -m pytest` and `coverage report`, docstrings, type hints, and
  `.. versionadded::`/`.. versionchanged::` on every changed public API).
- Give the user your findings as notes for them to read and put in their own words.
  Don't hand over a finished PR or issue body to paste.
- Only a maintainer's explicit, direct instruction in the current session overrides
  this. Then fill in the whole template, base PRs on `develop` (`main` is only for
  releases), and complete "LLM Disclosure" truthfully: the model(s) actually
  running, the harness, and the reasoning effort. If you can't tell the effort
  setting, ask the user. Never guess.

## MCNP

- MCNP is export controlled. Only the official, publicly released LANL user manuals
  (MCNP 1 through 6.3.2, all listed in `doc/source/index.rst`) may be used as sources.
  Don't add anything about MCNP that can't be found in them.
- Cite the manual in docstrings with the custom roles in `doc/source/conf.py`.
  The rules for choosing a role (manual, section, subsection, etc.) and for
  what to cite are in `doc/source/dev_standards.rst`. Read and follow them.

## Testing

- A bug fix needs a regression test that fails without the fix. Confirm that it does.
- `cd doc && make doctest` writes `doc/bar.imcnp` and `doc/foo_bar.imcnp`.
  Delete them; don't commit them.

## Syntax trees

- Changing an input is only correct if its MCNP text is. After a change that
  affects output, check the result of `format_for_mcnp_input()` (or `mcnp_str()`), and
  check that it parses back to the same values.
- A `ValueNode` whose value is `None` is not written, and neither is its
  padding, which may hold a comment. Use `""` to clear a value but keep the
  padding.
- A newly built `ValueNode` gets padding after it. Watch for values being
  glued together or split apart where MCNP needs them adjacent.
