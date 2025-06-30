
To bump the version, add a tag, and push, run 
```bash
python bump_version.py patch --tag --push
```
If bumping a minor or major version, replace `patch` with `minor` or `major`

To bump the version by a patch, run:
```bash
poetry version patch
```

To bump the version by a minor, run:
```bash
poetry version minor
```

To bump the version by a major, run:
```bash
poetry version major
```

To publish to PyPi via Poetry, run:
```bash
poetry publish --build
```