from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from .service import create_app
from .syncer import DEFAULT_SERVICE_URL, run_sync_loop, run_sync_once


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex Token Usage 服务与同步工具")
    subparsers = parser.add_subparsers(dest="command")

    serve = subparsers.add_parser("serve", help="启动 FastAPI 服务")
    serve.add_argument("--host", default="127.0.0.1", help="监听地址")
    serve.add_argument("--port", type=int, default=8000, help="监听端口")
    serve.add_argument("--db-file", default="data/token-account.db", help="SQLite 文件路径")
    serve.add_argument("--pricing-file", help="定价文件路径")

    sync = subparsers.add_parser("sync", help="执行一次同步")
    sync.add_argument("--service-url", default=DEFAULT_SERVICE_URL, help="服务地址")
    sync.add_argument("--codex-home", help=".codex 根目录")
    sync.add_argument("--sessions-root", help="sessions 目录路径")
    sync.add_argument("--state-file", help="本地同步状态文件")
    sync.add_argument("--source-id", help="来源设备标识")
    sync.add_argument("--hostname", help="来源设备主机名")
    sync.add_argument("--batch-size", type=int, default=1000, help="单次上传批大小")
    sync.add_argument("--timeout", type=int, default=30, help="HTTP 超时秒数")

    sync_loop = subparsers.add_parser("sync-loop", help="定时执行同步")
    sync_loop.add_argument("--service-url", default=DEFAULT_SERVICE_URL, help="服务地址")
    sync_loop.add_argument("--codex-home", help=".codex 根目录")
    sync_loop.add_argument("--sessions-root", help="sessions 目录路径")
    sync_loop.add_argument("--state-file", help="本地同步状态文件")
    sync_loop.add_argument("--source-id", help="来源设备标识")
    sync_loop.add_argument("--hostname", help="来源设备主机名")
    sync_loop.add_argument("--batch-size", type=int, default=1000, help="单次上传批大小")
    sync_loop.add_argument("--timeout", type=int, default=30, help="HTTP 超时秒数")
    sync_loop.add_argument("--interval", type=int, default=60, help="同步间隔秒数")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        db_path = Path(args.db_file)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        app = create_app(db_file=db_path, pricing_file=args.pricing_file)
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    if args.command == "sync":
        result = run_sync_once(
            service_url=args.service_url,
            sessions_root=args.sessions_root,
            codex_home=args.codex_home,
            state_file=args.state_file,
            source_id=args.source_id,
            hostname=args.hostname,
            batch_size=args.batch_size,
            timeout=args.timeout,
        )
        print(
            "同步完成："
            f"收到 {result['received_events']} 条，"
            f"写入 {result['inserted_events']} 条，"
            f"扫描 {result['scanned_files']} 个文件，"
            f"命中 {result['changed_files']} 个变更文件。"
        )
        return 0

    if args.command == "sync-loop":
        run_sync_loop(
            service_url=args.service_url,
            sessions_root=args.sessions_root,
            codex_home=args.codex_home,
            state_file=args.state_file,
            source_id=args.source_id,
            hostname=args.hostname,
            batch_size=args.batch_size,
            timeout=args.timeout,
            interval=args.interval,
        )
        return 0

    parser.print_help()
    return 1
