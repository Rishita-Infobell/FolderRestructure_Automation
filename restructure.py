import os
import shutil
import uuid
import argparse
import tarfile # Re-added for tar.gz support

def extract_tar_gz(tar_path, extract_to):
    """Extract a .tar.gz file into a target directory."""
    if tar_path.endswith(".tar.gz"):
        os.makedirs(extract_to, exist_ok=True)
        try:
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=extract_to)
            print(f" Extracted {os.path.basename(tar_path)} → {extract_to}")
        except tarfile.TarError as e:
            print(f" Error extracting {os.path.basename(tar_path)}: {e}")


def restructure_directory(source_dir, target_dir):
    """
    Enhanced restructuring:
    - Supports multi-system (VM/SUT) structure (Case 1) using detailed logic.
    - Supports single-system (manual) structure (Case 2) with sequential run indexing for WP.
    - Automatically extracts .tar.gz files in Case 2.
    """

    # Create the root directory with a unique UUID
    uuid_folder = str(uuid.uuid4())
    uuid_dir = os.path.join(target_dir, uuid_folder)
    os.makedirs(uuid_dir, exist_ok=True)

    # Identify SUTs (case-insensitive for 'VM' or 'SUT')
    suts = []
    for d in os.listdir(source_dir):
        full_path = os.path.join(source_dir, d)
        if os.path.isdir(full_path):
            name_lower = d.lower()
            if name_lower.startswith('vm') or name_lower.startswith('sut'):
                suts.append(d)

    # ---------------------------------------------------
    # 🧩 Case 1: Normal VM/SUT structure (Restored detailed logic)
    # ---------------------------------------------------
    if suts:
        print("Detected structured VM/SUT folders → using existing multi-system logic ")

        for sut in suts:
            # Normalize SUT name to "SUTx"
            sut_name = 'SUT' + sut[len('VM'):] if sut.lower().startswith('vm') else 'SUT' + sut[len('SUT'):]
            sut_dir = os.path.join(uuid_dir, sut_name)
            os.makedirs(sut_dir, exist_ok=True)

            # Create PlatformProfiler, WorkloadProfiler, and Results directories
            platform_profiler_dir = os.path.join(sut_dir, 'PlatformProfiler')
            workload_profiler_dir = os.path.join(sut_dir, 'WorkloadProfiler')
            results_dir = os.path.join(sut_dir, 'Results')
            os.makedirs(platform_profiler_dir, exist_ok=True)
            os.makedirs(workload_profiler_dir, exist_ok=True)
            os.makedirs(results_dir, exist_ok=True)

            # ----- Copy PlatformProfiler files -----
            for src_folder_name in ['PlatformProfile', 'Host-pp']:
                src_folder_path = os.path.join(source_dir, src_folder_name)
                if os.path.exists(src_folder_path):
                    contents = os.listdir(src_folder_path)
                    subdirs = [f for f in contents if os.path.isdir(os.path.join(src_folder_path, f))]
                    files = [f for f in contents if os.path.isfile(os.path.join(src_folder_path, f))]

                    # Case 1: single-level files (no subfolders)
                    if files and not subdirs:
                        for file_name in files:
                            shutil.copy(os.path.join(src_folder_path, file_name), platform_profiler_dir)

                    # Case 2: multiple pp1, pp2... subfolders
                    elif subdirs:
                        for idx, sub in enumerate(sorted(subdirs), start=1):
                            pp_folder = os.path.join(src_folder_path, sub)
                            run_dir = os.path.join(platform_profiler_dir, f'run{idx}')
                            os.makedirs(run_dir, exist_ok=True)
                            for file_name in os.listdir(pp_folder):
                                source_file = os.path.join(pp_folder, file_name)
                                if os.path.isfile(source_file):
                                    shutil.copy(source_file, run_dir)

            # ----- Copy WorkloadProfiler files -----
            wp_folder = None
            sut_number = ''.join(filter(str.isdigit, sut))  # extract number from VM1 or SUT1
            for candidate in os.listdir(source_dir):
                # Search for matching WP folder, e.g., 'wp-vm1'
                if candidate.lower().startswith("wp-") and candidate.lower().endswith(sut_number.lower()):
                    wp_folder = os.path.join(source_dir, candidate)
                    break

            if wp_folder and os.path.exists(wp_folder):
                # Only look for JSON files (assumed WorkloadProfiler output)
                wp_files = sorted([f for f in os.listdir(wp_folder) if f.lower().endswith(".json")])
                for run_idx, wp_file in enumerate(wp_files, start=1):
                    run_dir = os.path.join(workload_profiler_dir, f"run{run_idx}")
                    
                    # Check for iteration folders in the source WP folder
                    iteration_folders = [d for d in os.listdir(wp_folder)
                                         if os.path.isdir(os.path.join(wp_folder, d)) and d.lower().startswith("iteration")]
                    
                    if iteration_folders:
                        for iteration in iteration_folders:
                            iteration_dir = os.path.join(run_dir, iteration)
                            os.makedirs(iteration_dir, exist_ok=True)
                            shutil.copy(os.path.join(wp_folder, wp_file), iteration_dir)
                    else:
                        # Default to iteration1 if no iteration folders are found
                        iteration_dir = os.path.join(run_dir, "iteration1")
                        os.makedirs(iteration_dir, exist_ok=True)
                        shutil.copy(os.path.join(wp_folder, wp_file), iteration_dir)

            # ----- Copy Results files -----
            vm_dir = os.path.join(source_dir, sut)
            run_number = 1

            for run_dir_name in sorted(os.listdir(vm_dir)):
                run_path = os.path.join(vm_dir, run_dir_name)
                if not os.path.isdir(run_path):
                    continue

                # Detect iteration folders inside run
                iteration_folders = [
                    d for d in os.listdir(run_path)
                    if os.path.isdir(os.path.join(run_path, d)) and d.lower().startswith("iteration")
                ]

                if iteration_folders:
                    for iteration in iteration_folders:
                        iteration_path = os.path.join(run_path, iteration)
                        instance_folders = [
                            d for d in os.listdir(iteration_path)
                            if os.path.isdir(os.path.join(iteration_path, d))
                        ]

                        if instance_folders:
                            # Copy existing instance structure as-is
                            for instance in instance_folders:
                                target_instance_dir = os.path.join(results_dir, f'run{run_number}', iteration, instance)
                                os.makedirs(target_instance_dir, exist_ok=True)
                                for item in os.listdir(os.path.join(iteration_path, instance)):
                                    source_item = os.path.join(iteration_path, instance, item)
                                    if os.path.isfile(source_item):
                                        shutil.copy(source_item, target_instance_dir)
                                    elif os.path.isdir(source_item):
                                        shutil.copytree(source_item, os.path.join(target_instance_dir, item), dirs_exist_ok=True)
                        else:
                            # No instance folders → create one per log file
                            for item in os.listdir(iteration_path):
                                source_item = os.path.join(iteration_path, item)
                                if os.path.isfile(source_item):
                                    filename = os.path.basename(source_item)
                                    instance_num = None
                                    # Attempt to extract instance number from log-run-X format
                                    if "log-run" in filename:
                                        try:
                                            part = filename.split("log-run")[1]
                                            run_id = ''.join(filter(str.isdigit, part.split('-')[0]))
                                            instance_num = int(run_id)
                                        except (IndexError, ValueError):
                                            pass
                                    if instance_num is None:
                                        instance_num = 1
                                    
                                    target_instance_dir = os.path.join(results_dir, f'run{run_number}', iteration, f'instance{instance_num}')
                                    os.makedirs(target_instance_dir, exist_ok=True)
                                    shutil.copy(source_item, target_instance_dir)
                                elif os.path.isdir(source_item):
                                    # Copy directory contents into instance1
                                    target_dir = os.path.join(results_dir, f'run{run_number}', iteration, 'instance1', item)
                                    os.makedirs(os.path.dirname(target_dir), exist_ok=True) # Ensure parent directory exists
                                    shutil.copytree(source_item, target_dir, dirs_exist_ok=True)
                else:
                    # No iteration folders, use BenchmarkLog or default structure
                    benchmarklog_dir = os.path.join(run_path, 'BenchmarkLog')
                    items = os.listdir(benchmarklog_dir) if os.path.exists(benchmarklog_dir) else os.listdir(run_path)
                    
                    for item in items:
                        source_item = os.path.join(benchmarklog_dir if os.path.exists(benchmarklog_dir) else run_path, item)
                        
                        if os.path.isfile(source_item):
                            filename = os.path.basename(source_item)
                            instance_num = None
                            if "log-run" in filename:
                                try:
                                    part = filename.split("log-run")[1]
                                    run_id = ''.join(filter(str.isdigit, part.split('-')[0]))
                                    instance_num = int(run_id)
                                except (IndexError, ValueError):
                                    pass
                            if instance_num is None:
                                instance_num = 1
                            
                            target_instance_dir = os.path.join(results_dir, f'run{run_number}', 'iteration1', f'instance{instance_num}')
                            os.makedirs(target_instance_dir, exist_ok=True)
                            shutil.copy(source_item, target_instance_dir)

                run_number += 1

        # ----- Copy root-level files for Case 1 -----
        for item in os.listdir(source_dir):
            source_item = os.path.join(source_dir, item)
            if os.path.isfile(source_item):
                for sut in suts:
                    sut_lower = sut.lower()
                    sut_name = 'SUT' + sut[len('VM'):] if sut_lower.startswith('vm') else 'SUT' + sut[len('SUT'):]
                    sut_dir = os.path.join(uuid_dir, sut_name)
                    # Copy to the SUT root
                    shutil.copy(source_item, sut_dir)
                    
     # ---------------------------------------------------
    # 🧩 Case 2: Single-system folder (manual results) - UPDATED SYNCHRONIZATION LOGIC
    # ---------------------------------------------------
    else:
        print("No VM/SUT folders detected → structuring as single-system (SUT1) ")

        sut_dir = os.path.join(uuid_dir, "SUT1")
        os.makedirs(sut_dir, exist_ok=True)

        platform_profiler_dir = os.path.join(sut_dir, "PlatformProfiler")
        workload_profiler_dir = os.path.join(sut_dir, "WorkloadProfiler")
        results_dir = os.path.join(sut_dir, "Results")
        os.makedirs(platform_profiler_dir, exist_ok=True)
        os.makedirs(workload_profiler_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)

        # 1. Determine the number of runs based on Logs folder (Results determinant)
        logs_src = os.path.join(source_dir, "Logs")
        log_subfolders = []
        num_runs = 1 # Default to 1 run if no clear structure is found

        if os.path.exists(logs_src):
            # Find all top-level subdirectories in Logs (assumed to be run folders)
            log_subfolders = sorted([d for d in os.listdir(logs_src) 
                                     if os.path.isdir(os.path.join(logs_src, d))])
            if log_subfolders:
                num_runs = len(log_subfolders)
        
        # 2. Identify and prepare the primary WorkloadProfiler artifact
        wp_src = os.path.join(source_dir, "WorkloadProfiler")
        wp_artifact_path = None
        wp_artifact_is_tar = False
        extracted_temp = None # Used for temporary tar extraction

        if os.path.exists(wp_src):
            # Find the first .json or .tar.gz file to replicate
            for item in sorted(os.listdir(wp_src)):
                source_item = os.path.join(wp_src, item)
                if os.path.isfile(source_item) and item.lower().endswith((".json", ".tar.gz")):
                    wp_artifact_path = source_item
                    if item.lower().endswith(".tar.gz"):
                        wp_artifact_is_tar = True
                        
                        # Extract once into a unique temp folder
                        extracted_temp = os.path.join(wp_src, f"extracted_wp_temp_{str(uuid.uuid4())}")
                        extract_tar_gz(wp_artifact_path, extracted_temp)
                        
                    print(f"Detected WP artifact: {os.path.basename(wp_artifact_path)}. Replicating across {num_runs} run(s).")
                    break # Use the first one found

        # ----- Handle PlatformProfile -----
        platform_src = os.path.join(source_dir, "PlatformProfile")
        if os.path.exists(platform_src):
            for item in os.listdir(platform_src):
                source_item = os.path.join(platform_src, item)
                if os.path.isfile(source_item):
                    shutil.copy(source_item, platform_profiler_dir)
                elif os.path.isdir(source_item):
                    shutil.copytree(source_item, os.path.join(platform_profiler_dir, item), dirs_exist_ok=True)

        # 3. Replication: Copy WP artifact across all determined runs (Synchronization)
        if wp_artifact_path:
            for run_idx in range(1, num_runs + 1):
                target_dir = os.path.join(workload_profiler_dir, f"run{run_idx}", "iteration1")
                os.makedirs(target_dir, exist_ok=True)

                if wp_artifact_is_tar:
                    # Copy contents of the extracted folder (recursive walk)
                    if extracted_temp and os.path.exists(extracted_temp):
                        for root, _, files in os.walk(extracted_temp):
                            for file in files:
                                src_file = os.path.join(root, file)
                                # Target is always the iteration1 directory
                                shutil.copy(src_file, target_dir)
                else:
                    # Copy loose file
                    shutil.copy(wp_artifact_path, target_dir)

        # 4. Handle Logs (Treated as Results) - Structure based on num_runs
        if os.path.exists(logs_src):
            if not log_subfolders:
                # Case: Logs exists but has no subfolders (num_runs = 1)
                instance_dir = os.path.join(results_dir, "run1", "iteration1", "instance1")
                os.makedirs(instance_dir, exist_ok=True)
                
                # Copy loose files/folders in Logs source to instance_dir
                for item in os.listdir(logs_src):
                    src_item = os.path.join(logs_src, item)
                    if os.path.isfile(src_item):
                        shutil.copy(src_item, instance_dir)
                    elif os.path.isdir(src_item):
                        # Copy subdirectories recursively
                        shutil.copytree(src_item, os.path.join(instance_dir, item), dirs_exist_ok=True)
            else:
                # Case: Logs exists with subfolders (num_runs = len(log_subfolders))
                for run_idx, sub in enumerate(log_subfolders, start=1):
                    sub_path = os.path.join(logs_src, sub)
                    instance_dir = os.path.join(results_dir, f"run{run_idx}", "iteration1", "instance1")
                    os.makedirs(instance_dir, exist_ok=True)

                    # Copy contents of the run subfolder (recursive walk)
                    for root, _, files in os.walk(sub_path):
                        # Calculate the path relative to the sub_path to maintain sub-structure
                        rel_path = os.path.relpath(root, sub_path)
                        
                        # Determine the target directory
                        current_target_dir = os.path.join(instance_dir, rel_path)
                        os.makedirs(current_target_dir, exist_ok=True)
                        
                        for file in files:
                            src_file = os.path.join(root, file)
                            shutil.copy(src_file, current_target_dir)

        # 5. Handle root-level JSON/TXT
        for item in os.listdir(source_dir):
            source_item = os.path.join(source_dir, item)
            
            if not os.path.isfile(source_item):
                continue

            # Check for the specific manual result file and copy to SUT root
            if item.lower() == "epyc_manual_result.json":
                # Copy to the SUT root folder (e.g., stuctured_data/UUID/SUT1)
                shutil.copy(source_item, sut_dir)
                continue # Skip to the next item

            # Copy other root-level JSON/TXT files to Results/run1/iteration1/instance1
            if item.lower().endswith((".json", ".txt")):
                instance_dir = os.path.join(results_dir, "run1", "iteration1", "instance1")
                os.makedirs(instance_dir, exist_ok=True)
                shutil.copy(source_item, instance_dir)

        # Cleanup temporary extraction directory if used
        if extracted_temp and os.path.exists(extracted_temp):
            shutil.rmtree(extracted_temp, ignore_errors=True)
            print("Cleaned up temporary WP extraction folder.")

    # ---------------------------------------------------
    # ✅ Final Output
    # ---------------------------------------------------
    print(f"\n Restructuring complete!\nUUID folder created: {uuid_folder}\nOutput: {uuid_dir}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Restructure raw folders (v3 enhanced).")
    parser.add_argument('source_dir', help='Path to the source directory (raw_unstructured)')
    parser.add_argument('target_dir', help='Path to the target directory (structured_data)')
    args = parser.parse_args()

    restructure_directory(args.source_dir, args.target_dir)