import os
import shutil
import uuid
import argparse
 
def restructure_directory(source_dir, target_dir):
    """
    Restructures the directory based on the rules in rules.gemini.
 
    Handles:
    - SUT folders named 'VMx' or 'SUTx' (case-insensitive)
    - PlatformProfiler folder with:
        1. a single set of files (copied to all SUTs)
        2. multiple pp1, pp2... subfolders (copied into run1, run2... under each SUT)
    - WorkloadProfiler folders named 'wp_vmx' or 'wp_sutx' (case-insensitive),
      containing wp_runX.json files, placed under:
      SUTx/WorkloadProfiler/runX/iterationX/wp_runX.json
    - Results folders dynamically preserve iterations and instances if present,
      and create separate instance folders for each log file (instance1, instance2...)
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
            if candidate.lower().startswith("wp-") and candidate.lower().endswith(sut_number.lower()):
                wp_folder = os.path.join(source_dir, candidate)
                break
 
        if wp_folder and os.path.exists(wp_folder):
            wp_files = sorted([f for f in os.listdir(wp_folder) if f.lower().endswith(".json")])
            for run_idx, wp_file in enumerate(wp_files, start=1):
                run_dir = os.path.join(workload_profiler_dir, f"run{run_idx}")
                iteration_folders = [d for d in os.listdir(wp_folder)
                                     if os.path.isdir(os.path.join(wp_folder, d)) and d.lower().startswith("iteration")]
                if iteration_folders:
                    for iteration in iteration_folders:
                        iteration_dir = os.path.join(run_dir, iteration)
                        os.makedirs(iteration_dir, exist_ok=True)
                        shutil.copy(os.path.join(wp_folder, wp_file), iteration_dir)
                else:
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
                                    shutil.copytree(source_item, os.path.join(target_instance_dir, item))
                    else:
                        # No instance folders → create one per log file
                        for item in os.listdir(iteration_path):
                            source_item = os.path.join(iteration_path, item)
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
                                target_instance_dir = os.path.join(results_dir, f'run{run_number}', iteration, f'instance{instance_num}')
                                os.makedirs(target_instance_dir, exist_ok=True)
                                shutil.copy(source_item, target_instance_dir)
                            elif os.path.isdir(source_item):
                                target_dir = os.path.join(results_dir, f'run{run_number}', iteration, 'instance1', item)
                                os.makedirs(target_dir, exist_ok=True)
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
 
    # ----- Copy root-level files -----
    for item in os.listdir(source_dir):
        source_item = os.path.join(source_dir, item)
        if os.path.isfile(source_item):
            for sut in suts:
                sut_lower = sut.lower()
                sut_name = 'SUT' + sut[len('VM'):] if sut_lower.startswith('vm') else 'SUT' + sut[len('SUT'):]
                sut_dir = os.path.join(uuid_dir, sut_name)
                shutil.copy(source_item, sut_dir)
 
    # Print final UUID folder
    print(f"\n✅ Restructuring complete!\nUUID folder created: {uuid_folder}\n")
 
 
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Restructure Gemini raw data folders.")
    parser.add_argument('source_dir', help='Path to the source directory (raw_unstructured)')
    parser.add_argument('target_dir', help='Path to the target directory (structured_data)')
    args = parser.parse_args()
 
    restructure_directory(args.source_dir, args.target_dir)