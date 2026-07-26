# Pull Request Checklist for MontePy

### Description

Please provide a summary of the change, referencing the issue it fixes, if applicable. Include relevant context and motivation.

Fixes # (issue number)

---

### General Checklist

- [ ] I have performed a self-review of my own code.
- [ ] The code follows the standards outlined in the [development documentation](https://www.montepy.org/en/stable/dev_standards.html).
- [ ] I have formatted my code with `black` version 25 or 26.
- [ ] I have added tests that prove my fix is effective or that my feature works (if applicable).

---

### LLM Disclosure

1. Are you?

   - [ ] A human user 
   - [ ] A large language model (LLM), including ones acting on behalf of a human

1. Were any large language models (LLM or "AI") used in to generate any of this code?

  - [ ] Yes
      - Model(s) used:
  - [ ] No

<details open> 

<summary><h2>Documentation Checklist</h2></summary>

- [ ] I have documented all added classes and methods.
- [ ] I have added [type hints](https://peps.python.org/pep-0484/) to all functions as needed.
- [ ] I have marked all changes with the `.. versionchanged::` or `.. versionadded::` directives.


<h3>Infrastructure Changes </h3>

- [ ] For infrastructure updates, I have updated the developer's guide.

<h3>Significant features or Behavior changes </h3>

- [ ] For significant new features, I have added a section to the getting started guide.

</details>

---

<details>
<summary><h2>First-Time Contributor Checklist</h2></summary>

- [ ] If this is your first contribution, add yourself to `pyproject.toml` if you wish to do so.

</details>

---

## Additional Notes for Reviewers

Ensure that:

- [ ] This PR fully addresses and resolves the referenced issue(s).
- [ ] The submitted code is consistent with the merge checklist outlined [here](https://www.montepy.org/en/stable/dev_checklist.html#merge-checklist).
- [ ] The PR covers all relevant aspects according to the development guidelines.
- [ ] 100% coverage of the patch is achieved, or justification for a variance is given.
