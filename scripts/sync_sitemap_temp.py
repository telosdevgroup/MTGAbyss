import os
import subprocess
import tarfile

def main():
    remote_dest = "/srv/www/mtgabyss.com"
    remote_host = "ubuntu@15.204.113.15"

    files_to_sync = [
        "public/sitemap.xml",
        "public/robots.txt"
    ]
    
    # Dynamically find all sitemap*.html files in public/
    if os.path.exists("public"):
        for f in os.listdir("public"):
            if f.startswith("sitemap") and f.endswith(".html"):
                full_path = os.path.join("public", f).replace("\\", "/")
                if full_path not in files_to_sync:
                    files_to_sync.append(full_path)

    print("Checking files to sync...")
    valid_files = []
    for path in files_to_sync:
        if os.path.exists(path):
            valid_files.append(path)
        else:
            print(f"Warning: file '{path}' does not exist.")

    if not valid_files:
        print("Error: No valid files to sync.")
        return

    print(f"Found {len(valid_files)} files. Starting upload...")
    ssh_cmd = ["ssh", remote_host, f"tar -xf - -C {remote_dest}"]
    ssh_proc = subprocess.Popen(ssh_cmd, stdin=subprocess.PIPE)

    try:
        with tarfile.open(fileobj=ssh_proc.stdin, mode="w|", encoding="utf-8") as tar:
            for path in valid_files:
                arcname = os.path.relpath(path, "public")
                tar.add(path, arcname=arcname)
                
        ssh_proc.stdin.close()
        ssh_proc.wait()

        if ssh_proc.returncode == 0:
            remote_paths = [f"{remote_dest}/{os.path.relpath(p, 'public')}".replace("\\", "/") for p in valid_files]
            # Batch chmod in chunks to avoid command line length limits if there are many files
            chunk_size = 50
            for i in range(0, len(remote_paths), chunk_size):
                chunk = remote_paths[i:i+chunk_size]
                perm_cmd = f"chmod 644 {' '.join(chunk)}"
                subprocess.run(["ssh", remote_host, perm_cmd], check=True)
            print("Sitemaps and robots.txt deployment completed successfully!")
        else:
            print(f"Deployment failed with return code {ssh_proc.returncode}")
    except Exception as e:
        print(f"Error during deployment: {e}")

if __name__ == "__main__":
    main()
