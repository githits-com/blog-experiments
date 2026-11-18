# blog-experiments

Code behind [GitHits](https://githits.com) blog posts. Each folder is one post: the harness, analysis code, run scripts, and design notes. Published numbers live in the posts. This repository does not commit run output.

## Posts

| Post | Folder | Blog |
| --- | --- | --- |
| Agent37, Daytona, InstaBox, and Vercel Sandbox | [`sandbox-benchmark/`](./sandbox-benchmark/) | [Agent37 and Daytona: sandboxes for coding agents](https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents) |

That benchmark covers Agent37, Daytona, InstaBox, and Vercel Sandbox.

## How to run

See each folder's `README.md` for prerequisites, environment variables, and commands. Most folders follow the same shape:

```bash
cd <folder>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# export the API keys named in that folder's README
./run.sh                      # paid provider runs; writes local results/ and logs/
python3 analysis/analyze.py   # writes local out/tables.md from those results
```

Running a benchmark calls the providers' paid APIs. Read the warning at the top of the folder README before you start.

`results/`, `logs/`, and `out/` are gitignored. If `results/` is missing, the analysis scripts print a short message and exit.

## Development

```bash
ruff check .
ruff format --check .
```

## License

MIT. See [LICENSE](./LICENSE). Copyright GitHits.
