#!/usr/bin/env python3
"""Reliable chunked uploader using HfApi().upload_large_folder()."""
import os
import sys
from huggingface_hub import HfApi

api = HfApi()
repo_id = "sjkim1127/decbench-cpp-qualification"
folder_path = os.path.expanduser("~/cpp_corpus_root")

print(f"Starting upload_large_folder for {folder_path} -> {repo_id}...")
api.upload_large_folder(
    repo_id=repo_id,
    repo_type="dataset",
    folder_path=folder_path,
    num_workers=4,
    print_report_every=30,
)
print("Upload completed successfully!")
