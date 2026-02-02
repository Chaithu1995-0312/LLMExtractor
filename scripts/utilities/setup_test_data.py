import os

def prepare_test_data():
    input_dir = 'toolanalysisinput'
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
    
    for i in range(1, 11):
        file_path = os.path.join(input_dir, f'file_{i:02d}.md')
        with open(file_path, 'w', encoding='utf-8') as f:
            for line_num in range(1, 11):
                f.write(f'File {i} - Line {line_num}\n')
    print(f"Created 10 sample files in {input_dir}")

if __name__ == "__main__":
    prepare_test_data()
