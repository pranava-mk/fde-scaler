# fde

Course projects. Each project is a git submodule with its own repository.

| Project | Description |
|---|---|
| [meridianRetail](https://github.com/pranava-mk/meridianRetail) | Support-draft review tool (human review only) |

## Clone with all projects

```bash
git clone --recurse-submodules https://github.com/pranava-mk/fde.git
```

Already cloned without them:

```bash
git submodule update --init --recursive
```

## Pull the latest of every project

```bash
git pull
git submodule update --remote --merge
```

## Add a new project

Create the project's own GitHub repo first, then:

```bash
git submodule add https://github.com/pranava-mk/<project>.git <project>
git commit -m "Add <project> submodule"
git push
```
