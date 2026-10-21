@.github/copilot-instructions.md

# Claude-specific instructions

The file imported above is the shared guide for all coding agents. Keep it up to
date rather than repeating it here. The developer guides are
`doc/source/dev_standards.rst` and `doc/source/dev_checklist.rst`.

## Pull requests

- Base PRs on `develop`. `main` is only for releases.
- Always fill in `.github/pull_request_template.md` as the PR body, rather than
  writing a free-form description, then end it with the Claude Code attribution line.
- In "LLM Disclosure", check "A large language model" and "Yes", and fill in:
  - **Model(s) used**: the model actually running the session.
  - **Harness used**: Claude Code.
  - **Reasoning effort**: the session's effort setting. If you can't tell what
    it is, ask the user. Never guess.
- Before opening a PR, work through the template's checklists: `black`,
  tests, docstrings, type hints, and `.. versionadded::`/`.. versionchanged::` on
  every changed public API. Check the patch's coverage with `coverage run -m pytest`
  and `coverage report`, not just that the tests pass.

## Issues

- Use the templates in `.github/ISSUE_TEMPLATE/`, and fill in every section.
- Apply the labels and issue type the template sets. `gh issue create` does not
  apply a template's `type:`, so set it afterwards, e.g.
  `gh api -X PATCH repos/idaholab/MontePy/issues/<n> -f type=Bug`.
- Before opening one, search for an existing issue and check whether the bug
  also exists on `develop` and in the latest release.

## MCNP

- MCNP is export controlled. Only the public MCNP 6.2 and 6.3 user manuals may
  be used as sources. Don't add anything about MCNP that can't be found in them.
- Cite the manual in docstrings with the custom roles in `doc/source/conf.py`,
  e.g. ``:manual63:`5.9.7` ``.

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
