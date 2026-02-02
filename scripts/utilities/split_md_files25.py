import os
import math

def split_md_files():
    input_dir = 'toolanalysisinput'
    output_dir = 'toolanalysisoutputdocs25'
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # Get list of .md files in input directory
    files = [f for f in os.listdir(input_dir) if f.endswith('.md')]
    files.sort()
    
    # Process only the first 10 files as requested
    files_to_process = files[:10]
    
    if not files_to_process:
        print("No .md files found in toolanalysisinput folder.")
        return

    print(f"Processing {len(files_to_process)} files...")

    for filename in files_to_process:
        input_path = os.path.join(input_dir, filename)
        
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Split into 5 parts
        num_parts = 5
        lines_per_part = math.ceil(len(lines) / num_parts)
        
        base_name = os.path.splitext(filename)[0]
        
        for i in range(num_parts):
            start_index = i * lines_per_part
            end_index = (i + 1) * lines_per_part
            part_content = lines[start_index:end_index]
            
            output_filename = f"{base_name}_part{i+1}.md"
            output_path = os.path.join(output_dir, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(part_content)
                
    print(f"Done! Split {len(files_to_process)} files into {len(files_to_process) * 5} files in {output_dir}.")

if __name__ == "__main__":
    split_md_files()
