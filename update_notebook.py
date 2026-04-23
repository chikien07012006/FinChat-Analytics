import json

file_path = 'pipeline/model_experiment.ipynb'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for cell in data['cells']:
    if cell['cell_type'] == 'code' and any('columns_to_drop' in src for src in cell['source']):
        for i, src in enumerate(cell['source']):
            if 'promotion_types' in src:
                print("Found match!")
                cell['source'][i] = "    'first_tx', 'last_tx', 'promotion_types', 'last_promotion_date', 'transaction_date_x', 'transaction_date_y', 'transaction_date'\\n"

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=1)
