# blog-experiments

Code, data, and analysis behind [GitHits](https://githits.com) blog posts, so readers can reproduce the numbers.

Each folder is one post. The harness, raw result files, generated tables, and a short report live together. Nothing here calls an LLM unless a post says so.

## Posts

| Post | Folder | Blog |
|---|---|---|
| Agent37 vs Daytona: sandboxes for coding agents | [`agent37-vs-daytona-sandboxes/`](./agent37-vs-daytona-sandboxes/) | [githits.com/blog/agent37-daytona-sandboxes-for-coding-agents](https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/) |

## How to run

See each folder's `README.md` for prerequisites, environment variables, and the exact commands. Most folders follow the same shape:

```bash
cd <folder>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# export the API keys named in that folder's README
./run.sh                 # paid provider runs (optional; results are already committed)
python3 analysis/analyze.py   # regenerates out/tables.md from committed results
```

## License

MIT. See [LICENSE](./LICENSE). Copyright GitHits.
