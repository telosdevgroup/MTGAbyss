import os
import sys
import subprocess
import tarfile

class ProgressStream:
    def __init__(self, target_stream, total_bytes):
        self.target = target_stream
        self.total = total_bytes
        self.written = 0
        self.last_pct = -1

    def write(self, b):
        self.target.write(b)
        self.written += len(b)
        self.print_progress()
        return len(b)

    def flush(self):
        self.target.flush()

    def print_progress(self):
        pct = (self.written / self.total) * 100 if self.total > 0 else 0
        display_pct = min(pct, 100.0)
        
        mb_written = self.written / (1024 * 1024)
        mb_total = self.total / (1024 * 1024)
        
        bar_length = 30
        filled_length = int(bar_length * (display_pct / 100.0))
        bar = '#' * filled_length + '-' * (bar_length - filled_length)
        
        current_pct_check = round(display_pct, 1)
        if current_pct_check != self.last_pct:
            sys.stdout.write(f"\r[{bar}] {display_pct:.1f}% | {mb_written:.2f} MB / {mb_total:.2f} MB")
            sys.stdout.flush()
            self.last_pct = current_pct_check

def main():
    source_dir = "public/card"
    remote_dest = "/srv/www/mtgabyss.com"
    remote_host = "ubuntu@15.204.113.15"

    if not os.path.exists(source_dir):
        print(f"Error: Local source directory '{source_dir}' does not exist.")
        sys.exit(1)

    print("Scanning public/card to calculate total transfer size...")
    total_bytes = 0
    file_paths = []
    
    for root, _, files in os.walk(source_dir):
        for file in files:
            path = os.path.join(root, file)
            total_bytes += os.path.getsize(path)
            file_paths.append(path)

    print(f"Found {len(file_paths):,} files. Total size: {total_bytes / (1024*1024):.2f} MB.")
    print(f"Starting stream upload to {remote_host}:{remote_dest}...")

    # Open SSH subprocess
    ssh_cmd = ["ssh", remote_host, f"tar -xf - -C {remote_dest}"]
    ssh_proc = subprocess.Popen(ssh_cmd, stdin=subprocess.PIPE)

    try:
        progress_wrapper = ProgressStream(ssh_proc.stdin, total_bytes)
        
        with tarfile.open(fileobj=progress_wrapper, mode="w|", encoding="utf-8") as tar:
            for path in file_paths:
                # Add path as relative to "public" directory
                arcname = os.path.relpath(path, "public")
                tar.add(path, arcname=arcname)
                
        ssh_proc.stdin.close()
        print("\n\nWaiting for remote server to finish unpacking files...")
        ssh_proc.wait()

        if ssh_proc.returncode == 0:
            print("Transfer completed successfully!")
        else:
            print(f"\nTransfer failed with return code {ssh_proc.returncode}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        if ssh_proc.poll() is None:
            ssh_proc.kill()
        sys.exit(1)

if __name__ == "__main__":
    main()
