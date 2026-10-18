# Publishing

The GitHub release already contains a wheel. Registry publishing is a one-time account setup.

## PyPI

1. Create the `alttext` project on PyPI.
2. Add a trusted publisher with:
   - owner: `iambiniyam`
   - repository: `alttext`
   - workflow: `publish.yml`
   - environment: `pypi`
3. In the GitHub repository, add the variable `PUBLISH_PYPI=true`.
4. Run the `publish` workflow manually, or publish a new release.

The workflow uses OIDC. No token is stored.

## Direct install

```bash
pip install https://github.com/iambiniyam/alttext/releases/download/v0.1.4/alttext-0.1.4-py3-none-any.whl
python scripts/download_model.py
```
