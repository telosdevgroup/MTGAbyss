#!/usr/bin/env python3
"""
MongoDB Automated Backup Script with Syncthing Staging & Discord Notifications.

Workflow:
1. Connects to MongoDB via pymongo to discover target site databases.
2. Dumps each database via mongodump into a temporary staging folder outside
   Syncthing's immediate sync purview.
3. Atomically moves completed archives into the Syncthing folder for absorption
   by remote nodes (e.g. Core, Nimo).
4. Enforces retention by pruning archives older than configured retention days.
5. Sends detailed execution metrics and status alerts to a Discord webhook.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pymongo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SYSTEM_DATABASES = {"admin", "config", "local"}
AVASCRY_DATABASES = [
    "mtgabyss_next",
    "avascry_dominion",
    "avascry_minecraft",
    "avascry_necromunda",
    "avascry_swu",
]


def find_mongodump(custom_path: Optional[str] = None) -> Optional[str]:
    """Locate the mongodump executable."""
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    env_path = os.environ.get("MONGODUMP_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    which_path = shutil.which("mongodump")
    if which_path:
        return which_path

    # Common Windows installation search paths
    search_patterns = [
        r"C:\tools\mongodb-database-tools\*\bin\mongodump.exe",
        r"C:\tools\mongodb-database-tools\bin\mongodump.exe",
        str(Path(__file__).parent.parent / "bin" / "mongodb-tools" / "*" / "bin" / "mongodump.exe"),
        r"C:\Program Files\MongoDB\Tools\*\bin\mongodump.exe",
        r"C:\Program Files\MongoDB\Server\*\bin\mongodump.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\MongoDB.DatabaseTools*\*\bin\mongodump.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\mongodump.exe"),
    ]
    for pattern in search_patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

    return None


def ensure_mongodump(custom_path: Optional[str] = None) -> Optional[str]:
    """Locate or automatically download portable mongodump executable."""
    found = find_mongodump(custom_path)
    if found:
        return found

    target_dir = Path("C:/tools/mongodb-database-tools")
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        target_dir = Path(__file__).parent.parent / "bin" / "mongodb-tools"
        target_dir.mkdir(parents=True, exist_ok=True)

    tools_zip_url = "https://fastdl.mongodb.org/tools/db/mongodb-database-tools-windows-x86_64-100.18.0.zip"
    zip_path = target_dir / "tools.zip"

    print("[Setup] Downloading official portable MongoDB Database Tools from fastdl.mongodb.org...")
    try:
        import zipfile
        urllib.request.urlretrieve(tools_zip_url, zip_path)
        print(f"[Setup] Extracting tools into {target_dir}...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(target_dir)
        zip_path.unlink(missing_ok=True)

        found = find_mongodump(None)
        if found:
            print(f"[Setup] Successfully initialized mongodump at: {found}")
            return found
    except Exception as e:
        print(f"[Warning] Automatic download of MongoDB tools encountered: {e}", file=sys.stderr)

    return None


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_idx = 0
    val = float(size_bytes)
    while val >= 1024 and unit_idx < len(units) - 1:
        val /= 1024.0
        unit_idx += 1
    return f"{val:.2f} {units[unit_idx]}"


def get_free_disk_space(path: Path) -> str:
    """Retrieve free disk space on target filesystem."""
    try:
        target = path if path.exists() else path.parent
        usage = shutil.disk_usage(target if target.exists() else Path.cwd())
        return f"{format_bytes(usage.free)} free of {format_bytes(usage.total)}"
    except Exception:
        return "Unknown"


def send_discord_notification(
    webhook_url: str,
    success: bool,
    backed_up: List[Dict[str, any]],
    failed: List[Dict[str, any]],
    duration_sec: float,
    total_size_bytes: int,
    pruned_count: int,
    output_dir: Path,
    absorbing_nodes: str,
    is_dry_run: bool = False,
) -> bool:
    """Send formatted embed report to Discord webhook."""
    if not webhook_url:
        print("[Notice] No Discord webhook URL provided; skipping notification.")
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    free_space = get_free_disk_space(output_dir)

    if failed and backed_up:
        color = 0xF1C40F  # Amber / Partial warning
        status_text = "⚠️ Backup Completed with Warnings"
    elif failed:
        color = 0xE74C3C  # Red / Error
        status_text = "❌ Backup Failed"
    else:
        color = 0x2ECC71  # Green / Success
        status_text = "✅ Backup Completed Successfully"

    if is_dry_run:
        status_text = f"🔍 [DRY-RUN] {status_text}"

    # Build DB breakdown list (limit lines to fit Discord embed limit)
    db_summary_lines = []
    for item in backed_up[:25]:
        db_summary_lines.append(f"• **{item['db']}**: {format_bytes(item.get('size_bytes', 0))}")
    if len(backed_up) > 25:
        db_summary_lines.append(f"... and {len(backed_up) - 25} more databases")

    db_summary = "\n".join(db_summary_lines) if db_summary_lines else "None"

    fields = [
        {"name": "Databases Backed Up", "value": f"{len(backed_up)} database(s)\n{db_summary}"[:1024], "inline": False},
        {"name": "Total Backup Size", "value": format_bytes(total_size_bytes), "inline": True},
        {"name": "Elapsed Time", "value": f"{duration_sec:.2f}s", "inline": True},
        {"name": "Pruned Archives", "value": f"{pruned_count} old file(s)", "inline": True},
        {"name": "Storage Destination", "value": f"`{str(output_dir)}`\n({free_space})"[:1024], "inline": False},
        {"name": "Syncthing Absorbing Nodes", "value": f"📡 `{absorbing_nodes}`", "inline": True},
    ]

    if failed:
        fail_lines = [f"• **{item['db']}**: {item.get('error', 'Unknown error')}" for item in failed[:10]]
        fields.append({"name": "Failed Databases", "value": "\n".join(fail_lines)[:1024], "inline": False})

    payload = {
        "embeds": [
            {
                "title": status_text,
                "description": f"Automated MongoDB backup run on host: **{os.environ.get('COMPUTERNAME', 'Primary Host')}**",
                "color": color,
                "fields": fields,
                "timestamp": now_iso,
                "footer": {"text": "MongoDB Syncthing Backup Pipeline"},
            }
        ]
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "MongoDB-Backup-Bot/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 204)
    except urllib.error.HTTPError as e:
        print(f"[Error] Discord webhook HTTP error: {e.code} - {e.reason}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[Error] Failed to send Discord webhook: {e}", file=sys.stderr)
        return False


def prune_old_backups(db_dir: Path, retention_days: int, dry_run: bool = False) -> int:
    """Delete backup archives older than retention_days."""
    if not db_dir.exists() or retention_days <= 0:
        return 0

    cutoff_time = time.time() - (retention_days * 86400)
    pruned = 0

    for file_path in db_dir.glob("*.archive.gz"):
        try:
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                if dry_run:
                    print(f"  [Dry-Run] Would prune: {file_path.name}")
                else:
                    file_path.unlink()
                    print(f"  [Pruned] Removed old archive: {file_path.name}")
                pruned += 1
        except Exception as e:
            print(f"  [Warning] Could not prune {file_path}: {e}", file=sys.stderr)

    return pruned


def run_backup_pipeline(
    mongo_uri: str,
    output_dir: Path,
    target_dbs: Optional[List[str]],
    exclude_dbs: List[str],
    retention_days: int,
    discord_webhook: Optional[str],
    absorbing_nodes: str,
    mongodump_bin: Optional[str],
    dry_run: bool = False,
) -> int:
    """Main backup workflow execution."""
    start_time = time.time()
    print("=" * 60)
    print("MongoDB Automated Backup Pipeline")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Output (Syncthing): {output_dir}")
    print(f"Absorbing Nodes: {absorbing_nodes}")
    if dry_run:
        print("MODE: DRY RUN (No writes or executions)")
    print("=" * 60)

    # 1. Connect to MongoDB and discover databases
    try:
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        all_dbs = client.list_database_names()
    except Exception as e:
        err_msg = f"Failed to connect to MongoDB at {mongo_uri}: {e}"
        print(f"[Fatal] {err_msg}", file=sys.stderr)
        if discord_webhook and not dry_run:
            send_discord_notification(
                webhook_url=discord_webhook,
                success=False,
                backed_up=[],
                failed=[{"db": "Cluster Connection", "error": err_msg}],
                duration_sec=time.time() - start_time,
                total_size_bytes=0,
                pruned_count=0,
                output_dir=output_dir,
                absorbing_nodes=absorbing_nodes,
                is_dry_run=dry_run,
            )
        return 1

    # Filter target databases
    excluded_set = set(SYSTEM_DATABASES) | set(exclude_dbs)
    if target_dbs:
        selected_dbs = [db for db in target_dbs if db in all_dbs]
        missing = [db for db in target_dbs if db not in all_dbs]
        if missing:
            print(f"[Warning] Specified databases not found in cluster: {missing}")
    else:
        selected_dbs = [db for db in all_dbs if db not in excluded_set]

    print(f"[Discovery] Found {len(selected_dbs)} database(s) to back up: {', '.join(selected_dbs)}")

    # 2. Check mongodump binary
    if not dry_run:
        resolved_mongodump = ensure_mongodump(mongodump_bin)
        if not resolved_mongodump:
            err_msg = (
                "mongodump executable not found in PATH or standard directories.\n"
                "Install MongoDB Database Tools or specify --mongodump-path / MONGODUMP_PATH."
            )
            print(f"[Fatal] {err_msg}", file=sys.stderr)
            if discord_webhook:
                send_discord_notification(
                    webhook_url=discord_webhook,
                    success=False,
                    backed_up=[],
                    failed=[{"db": "Tools Validation", "error": err_msg}],
                    duration_sec=time.time() - start_time,
                    total_size_bytes=0,
                    pruned_count=0,
                    output_dir=output_dir,
                    absorbing_nodes=absorbing_nodes,
                    is_dry_run=dry_run,
                )
            return 1
        print(f"[Tool] Using mongodump: {resolved_mongodump}")
    else:
        resolved_mongodump = "mongodump (mocked in dry-run)"

    # Setup directories
    staging_dir = output_dir / "_staging"
    if not dry_run:
        staging_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backed_up: List[Dict[str, any]] = []
    failed: List[Dict[str, any]] = []
    total_size = 0
    total_pruned = 0

    # 3. Perform Dump & Atomic Staging
    for db_name in selected_dbs:
        print(f"\nProcessing database: [{db_name}]")
        archive_name = f"{db_name}_{timestamp_str}.archive.gz"
        staging_file = staging_dir / archive_name
        dest_db_dir = output_dir / db_name
        final_file = dest_db_dir / archive_name

        if dry_run:
            print(f"  [Dry-Run] Would dump {db_name} -> {staging_file}")
            print(f"  [Dry-Run] Would atomically move -> {final_file}")
            backed_up.append({"db": db_name, "size_bytes": 1024 * 1024, "archive": archive_name})
            continue

        dest_db_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            resolved_mongodump,
            f"--uri={mongo_uri}",
            f"--db={db_name}",
            f"--archive={str(staging_file)}",
            "--gzip",
        ]

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if proc.returncode != 0:
                err_text = proc.stderr.strip() or f"Process exited with code {proc.returncode}"
                print(f"  [Error] mongodump failed: {err_text}", file=sys.stderr)
                failed.append({"db": db_name, "error": err_text})
                if staging_file.exists():
                    staging_file.unlink(missing_ok=True)
                continue

            if not staging_file.exists() or staging_file.stat().st_size == 0:
                err_text = "Staged archive file is missing or empty"
                print(f"  [Error] {err_text}", file=sys.stderr)
                failed.append({"db": db_name, "error": err_text})
                continue

            file_size = staging_file.stat().st_size
            # Atomic move into final Syncthing sync path
            shutil.move(str(staging_file), str(final_file))
            print(f"  [Success] Archived: {format_bytes(file_size)} -> {final_file.name}")

            backed_up.append({"db": db_name, "size_bytes": file_size, "archive": archive_name})
            total_size += file_size

            # Prune old archives for this db
            pruned = prune_old_backups(dest_db_dir, retention_days, dry_run=False)
            total_pruned += pruned

        except Exception as e:
            print(f"  [Error] Exception during backup of {db_name}: {e}", file=sys.stderr)
            failed.append({"db": db_name, "error": str(e)})
            if staging_file.exists():
                staging_file.unlink(missing_ok=True)

    # Clean staging dir if empty
    if not dry_run and staging_dir.exists():
        try:
            if not any(staging_dir.iterdir()):
                staging_dir.rmdir()
        except Exception:
            pass

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"Backup run completed in {elapsed:.2f}s")
    print(f"Databases succeeded: {len(backed_up)}, failed: {len(failed)}")
    print(f"Total backup volume: {format_bytes(total_size)}")
    print(f"Archives pruned: {total_pruned}")
    print("=" * 60)

    # 4. Notify Discord
    if discord_webhook:
        print("[Notification] Dispatching Discord embed report...")
        sent = send_discord_notification(
            webhook_url=discord_webhook,
            success=(len(failed) == 0),
            backed_up=backed_up,
            failed=failed,
            duration_sec=elapsed,
            total_size_bytes=total_size,
            pruned_count=total_pruned,
            output_dir=output_dir,
            absorbing_nodes=absorbing_nodes,
            is_dry_run=dry_run,
        )
        if sent:
            print("[Notification] Discord webhook received report successfully.")

    return 0 if len(failed) == 0 else 2


def main():
    parser = argparse.ArgumentParser(
        description="MongoDB backup automation with atomic staging for Syncthing and Discord reporting."
    )
    parser.add_argument(
        "--uri",
        default=os.environ.get("MONGODB_URI", "mongodb://192.168.1.213:27017"),
        help="MongoDB connection URI (default: env MONGODB_URI or mongodb://192.168.1.213:27017)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("BACKUP_DIR", str(Path.home() / "Syncthing" / "db_backups")),
        help="Syncthing-watched backup root directory",
    )
    parser.add_argument(
        "--db",
        action="append",
        dest="databases",
        help="Specific database(s) to back up. Can be passed multiple times. If omitted, all non-system databases are backed up.",
    )
    parser.add_argument(
        "--exclude-db",
        action="append",
        default=["celery_broker", "celery_results"],
        help="Databases to exclude from backup (defaults: celery_broker, celery_results). Can be specified multiple times.",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.environ.get("RETENTION_DAYS", "14")),
        help="Days to retain historical backups (default: 14)",
    )
    parser.add_argument(
        "--webhook-url",
        default=os.environ.get("DISCORD_WEBHOOK_URL", ""),
        help="Discord Webhook URL for status notifications (default: env DISCORD_WEBHOOK_URL)",
    )
    parser.add_argument(
        "--absorbing-nodes",
        default=os.environ.get("SYNCTHING_NODES", "Core, Nimo"),
        help="Comma-separated labels of absorbing Syncthing nodes (default: 'Core, Nimo')",
    )
    parser.add_argument(
        "--mongodump-path",
        default=None,
        help="Explicit path to mongodump executable",
    )
    parser.add_argument(
        "--test-discord",
        action="store_true",
        help="Send a test embed to Discord and exit",
    )
    parser.add_argument(
        "--avascry",
        action="store_true",
        help="Target the 5 core Avascry gaming sites (mtgabyss_next, avascry_dominion, avascry_minecraft, avascry_necromunda, avascry_swu) to C:\\backups",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the backup process without executing mongodump or altering disk",
    )

    args = parser.parse_args()

    # Preset logic for Avascry 5 sites
    if args.avascry:
        if not args.databases:
            args.databases = list(AVASCRY_DATABASES)
        if args.output_dir == str(Path.home() / "Syncthing" / "db_backups") and not os.environ.get("BACKUP_DIR"):
            args.output_dir = "C:/backups"

    if args.test_discord:
        if not args.webhook_url:
            print("[Error] No Discord webhook URL provided or configured in .env", file=sys.stderr)
            sys.exit(1)
        print(f"[Test] Dispatching test embed to Discord webhook...")
        sent = send_discord_notification(
            webhook_url=args.webhook_url,
            success=True,
            backed_up=[
                {"db": "mtgabyss_next", "size_bytes": 1024 * 1024 * 245},
                {"db": "medicatalog_db", "size_bytes": 1024 * 1024 * 52},
            ],
            failed=[],
            duration_sec=3.42,
            total_size_bytes=1024 * 1024 * 297,
            pruned_count=1,
            output_dir=Path(args.output_dir).resolve(),
            absorbing_nodes=args.absorbing_nodes,
            is_dry_run=False,
        )
        if sent:
            print("[Test] ✅ Test Discord message dispatched successfully!")
            sys.exit(0)
        else:
            print("[Test] ❌ Failed to dispatch test Discord message.", file=sys.stderr)
            sys.exit(1)

    exit_code = run_backup_pipeline(
        mongo_uri=args.uri,
        output_dir=Path(args.output_dir).resolve(),
        target_dbs=args.databases,
        exclude_dbs=args.exclude_db,
        retention_days=args.retention_days,
        discord_webhook=args.webhook_url,
        absorbing_nodes=args.absorbing_nodes,
        mongodump_bin=args.mongodump_path,
        dry_run=args.dry_run,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
