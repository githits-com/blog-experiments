# blog-experiments

Code behind [GitHits](https://githits.com) blog posts, so readers can reproduce the numbers. Published results live in the posts. This repo holds the harness and analysis scripts only; run output is not committed.

Each folder is one post. Nothing here calls an LLM unless a post says so.

## Posts

| Post                                     | Folder                                                                                         | Blog                                                                                                                                  |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Agent37, Daytona, and InstaBox sandboxes | [`sandbox-benchmark-agent37-daytona-instabox/`](./sandbox-benchmark-agent37-daytona-instabox/) | [githits.com/blog/agent37-daytona-sandboxes-for-coding-agents](https://githits.com/blog/agent37-daytona-sandboxes-for-coding-agents/) |

## How to run

See each folder's `README.md` for prerequisites, environment variables, and the exact commands. Most folders follow the same shape:

```bash
cd <folder>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# export the API keys named in that folder's README
./run.sh                      # paid provider runs; writes local results/ and logs/
python3 analysis/analyze.py   # writes local out/tables.md from those results
```

`results/`, `logs/`, and `out/` are gitignored. If `results/` is missing, the analysis scripts print a short message and exit.

## Development

Format Python with `ruff format .`

## License

MIT. See [LICENSE](./LICENSE). Copyright GitHits.
