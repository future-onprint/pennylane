<div align="center">

# 🪙 Pennylane

**Pennylane integration for the Frappe ecosystem.**

[![Python](https://img.shields.io/badge/python-3.14+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Frappe](https://img.shields.io/badge/frappe-v16-0089ff?style=flat-square)](https://frappeframework.com)
[![License](https://img.shields.io/badge/license-AGPL--3.0-green?style=flat-square)](license.txt)

*A project by [Underscore Blank OÜ](mailto:contact@underscore-blank.io)*

</div>

---

## About

**Pennylane** is a Frappe app that integrates [Pennylane](https://www.pennylane.com) — a modern accounting tool — directly into the Frappe ecosystem.

---

## Requirements

- [Frappe Bench](https://github.com/frappe/bench) installed and configured
- Frappe Framework **v16**
- Python **≥ 3.14**

---

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench install-app pennylane
```

---

## Development

This project uses `pre-commit` to enforce code quality. Install it and enable it for this repository:

```bash
cd apps/pennylane
pre-commit install
```

Configured tools:

| Tool | Role |
|------|------|
| `ruff` | Python linting and formatting |
| `eslint` | JavaScript linting |
| `prettier` | JavaScript / CSS formatting |
| `pyupgrade` | Python syntax modernization |

---

## CI / CD

The following GitHub Actions workflows are configured:

- **CI** — Installs the app and runs unit tests on every push to `develop`
- **Linters** — Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [`pip-audit`](https://pypi.org/project/pip-audit/) on every pull request

---

## License

Distributed under the **AGPL-3.0** License. See [`license.txt`](license.txt) for details.

---

<div align="center">
  <sub>Maintained by <a href="mailto:contact@underscore-blank.io">Underscore Blank OÜ</a></sub>
</div>
