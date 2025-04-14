import os
import sys
import time
import logging
import argparse
import shlex
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class UploadHandler(FileSystemEventHandler):
    def __init__(self, watch_dir, user_host, remote_base_dir):
        """Initialize the event handler with directory and VPS details."""
        self.watch_dir = watch_dir
        self.user_host = user_host
        self.remote_base_dir = remote_base_dir
        self.uploaded_files = {}
        self.upload_queue = []
        self.pending_chunks = set()
    
    def _process_mpd_file(self, mpd_path):
        """Extract chunk references from the MPD file and ensure they're uploaded first."""
        try:
            with open(mpd_path, 'r') as f:
                mpd_content = f.read()
            
            chunk_files = []
            for line in mpd_content.split('\n'):
                if 'media="chunk-stream' in line and '.m4s"' in line:
                    start_idx = line.find('media="') + 7
                    end_idx = line.find('"', start_idx)
                    chunk_file = line[start_idx:end_idx]
                    chunk_files.append(chunk_file)
            
            mpd_dir = os.path.dirname(mpd_path)
            
            for chunk in chunk_files:
                chunk_path = os.path.join(mpd_dir, chunk)
                norm_path = chunk_path.replace('\\', '/')
                
                if os.path.exists(chunk_path):
                    if norm_path not in self.uploaded_files:
                        logging.info(f"Prioritizing chunk from MPD: {chunk}")
                        self._upload_file(chunk_path, high_priority=True)
                    self.pending_chunks.discard(norm_path)  # Remove from pending if it exists
                else:
                    self.pending_chunks.add(norm_path)
                    logging.info(f"Chunk referenced in MPD but not yet available: {chunk}")
            
            return True
        except Exception as e:
            logging.error(f"Error processing MPD file {mpd_path}: {e}")
            return False
    
    def _upload_file(self, full_local_path, high_priority=False):
        """Common method to handle file uploads with priority support."""
        if full_local_path.endswith('.tmp'):
            logging.info(f"Ignoring .tmp file: {full_local_path}")
            return
        
        if not os.path.exists(full_local_path):
            logging.warning(f"File does not exist: {full_local_path}")
            return
            
        normalized_path = full_local_path.replace('\\', '/')
        current_mtime = os.path.getmtime(full_local_path)
        
        if normalized_path in self.uploaded_files and self.uploaded_files[normalized_path] == current_mtime:
            logging.info(f"No changes to file since last upload: {normalized_path}")
            return
        
        if full_local_path.endswith('.mpd'):
            self._process_mpd_file(full_local_path)
            
        relative_path = os.path.relpath(normalized_path, self.watch_dir).replace('\\', '/')
        
        remote_path = f"{self.remote_base_dir}/{relative_path}"
        remote_dir = os.path.dirname(remote_path)
        
        logging.info(f"Processing file: {normalized_path}")
        
        try:
            ssh_cmd = ['ssh', self.user_host, f'mkdir -p {shlex.quote(remote_dir)}']
            subprocess.run(ssh_cmd, check=True)
            
            scp_cmd = ['scp', normalized_path, f'{self.user_host}:{remote_path}']
            logging.info(f"Uploading to: {self.user_host}:{remote_path}")
            subprocess.run(scp_cmd, check=True)
            logging.info(f"Successfully uploaded: {normalized_path}")
            
            self.uploaded_files[normalized_path] = current_mtime
            
            if normalized_path in self.pending_chunks:
                self.pending_chunks.remove(normalized_path)
                logging.info(f"Uploaded pending chunk: {normalized_path}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to upload {normalized_path}: {e}")
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            norm_path = event.src_path.replace('\\', '/')
            is_priority = norm_path in self.pending_chunks
            self._upload_file(event.src_path, high_priority=is_priority)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            if event.src_path.endswith('.mpd'):
                logging.info(f"MPD file modified: {event.src_path}")
                self._upload_file(event.src_path, high_priority=True)
            else:
                self._upload_file(event.src_path)
    
    def on_moved(self, event):
        """Handle file move/rename events (important for .tmp to .m4s conversions)."""
        if not event.is_directory:
            if event.src_path.endswith('.tmp') and not event.dest_path.endswith('.tmp'):
                logging.info(f"File renamed from {event.src_path} to {event.dest_path}")
                norm_path = event.dest_path.replace('\\', '/')
                is_priority = norm_path in self.pending_chunks
                self._upload_file(event.dest_path, high_priority=is_priority)

if __name__ == '__main__':
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Watch a directory and upload modified files to a VPS using SCP.")
    parser.add_argument('watch_dir', help='Directory to watch for changes')
    parser.add_argument('remote_dest', help='Remote destination in the form user@host:/remote/dir')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                        help='Set logging level (default: INFO)')
    args = parser.parse_args()
    
    watch_dir = args.watch_dir
    remote_dest = args.remote_dest
    
    # Split remote destination into user@host and remote base directory
    try:
        user_host, remote_base_dir = remote_dest.split(':', 1)
    except ValueError:
        logging.error("Invalid remote destination format. Use user@host:/remote/dir")
        sys.exit(1)
    
    # Validate the watch directory
    if not os.path.isdir(watch_dir):
        logging.error(f"{watch_dir} is not a directory")
        sys.exit(1)
    
    # Configure logging
    log_level = getattr(logging, args.log_level)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Initialize the event handler
    event_handler = UploadHandler(watch_dir, user_host, remote_base_dir)
    
    # Set up the observer to monitor the directory
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()
    
    logging.info(f"Watching directory: {watch_dir}")
    logging.info(f"Uploading to: {remote_dest}")
    
    # Keep the script running until interrupted
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Script stopped by user")
    
    observer.join()