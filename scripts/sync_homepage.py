import os
import sys
import subprocess
import tarfile

def main():
    remote_dest = "/srv/www/mtgabyss.com"
    remote_host = "ubuntu@15.204.113.15"

    files_to_sync = [
        "public/index.html",
        "public/search.html",
        "public/search-index.json",
        "public/assets/site.css"
    ]

    print("Checking files to sync...")
    total_bytes = 0
    valid_files = []
    for path in files_to_sync:
        if os.path.exists(path):
            total_bytes += os.path.getsize(path)
            valid_files.append(path)
        else:
            print(f"Warning: file '{path}' does not exist and will be skipped.")

    if not valid_files:
        print("Error: No valid files to sync.")
        sys.exit(1)

    print(f"Found {len(valid_files)} files. Total size: {total_bytes / 1024:.2f} KB.")
    print(f"Starting upload to {remote_host}:{remote_dest}...")

    # Open SSH subprocess to unpack tar into remote_dest
    ssh_cmd = ["ssh", remote_host, f"tar -xf - -C {remote_dest}"]
    ssh_proc = subprocess.Popen(ssh_cmd, stdin=subprocess.PIPE)

    try:
        with tarfile.open(fileobj=ssh_proc.stdin, mode="w|", encoding="utf-8") as tar:
            for path in valid_files:
                # Add path as relative to "public" directory
                arcname = os.path.relpath(path, "public")
                tar.add(path, arcname=arcname)
                
        ssh_proc.stdin.close()
        print("Waiting for remote server to finish unpacking files...")
        ssh_proc.wait()

        if ssh_proc.returncode == 0:
            # Set correct file permissions on VPS
            perm_cmd = (
                f"chmod 644 {remote_dest}/index.html {remote_dest}/search.html "
                f"{remote_dest}/search-index.json {remote_dest}/assets/site.css"
            )
            subprocess.run(["ssh", remote_host, perm_cmd], check=True)
            print("Homepage and assets deployment completed successfully!")
        else:
            print(f"Deployment failed with return code {ssh_proc.returncode}")
            
    except Exception as e:
        print(f"Error during deployment: {e}")
        if ssh_proc.poll() is None:
            ssh_proc.kill()
        sys.exit(1)

if __name__ == "__main__":
    main()
