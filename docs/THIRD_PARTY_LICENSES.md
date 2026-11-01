# Third-party licences

IrysQuest is AGPL-3.0-or-later. These are its runtime dependencies: `httpx` and `python-dotenv` from
`pyproject.toml`, plus everything they pull in, as installed on Python 3.12 on 1 Nov 2026. Nothing is vendored;
pip installs each from PyPI under its own licence.

| Package | Version | Licence | Pulled in by | Source |
|---|---|---|---|---|
| httpx | 0.28.1 | BSD-3-Clause | IrysQuest | https://github.com/encode/httpx |
| python-dotenv | 1.2.4 | BSD-3-Clause | IrysQuest | https://github.com/theskumar/python-dotenv |
| httpcore | 1.0.9 | BSD-3-Clause | httpx | https://github.com/encode/httpcore |
| anyio | 4.15.1 | MIT | httpx | https://github.com/agronholm/anyio |
| h11 | 0.16.0 | MIT | httpcore | https://github.com/python-hyper/h11 |
| idna | 3.20 | BSD-3-Clause | httpx, anyio | https://github.com/kjd/idna |
| typing_extensions | 4.16.0 | PSF-2.0 | anyio | https://github.com/python/typing_extensions |
| certifi | 2026.10.23 | **MPL-2.0** | httpx, httpcore | https://github.com/certifi/python-certifi |

**Not Apache/MIT/BSD/PSF: certifi (MPL-2.0).** It is the Mozilla CA bundle, used unmodified as an installed
dependency. MPL-2.0 is file-level copyleft and explicitly compatible with the GNU licences (MPL-2.0 §3.3), so
using it from an AGPL program is fine; modifying certifi's own files would mean publishing those changes under
MPL-2.0.

`exceptiongroup` (MIT) is required by anyio only on Python < 3.11, which IrysQuest doesn't support, so it is not
installed. Dev-only tools (`pytest` and what it pulls in) are not runtime dependencies and are not listed.

Regenerate with `pip install pip-licenses` in the venv, then
`pip-licenses --packages anyio certifi h11 httpcore httpx idna python-dotenv typing-extensions --from=mixed --with-urls`.
