import os
import shutil

# Целевая папка — прямо корень, где лежит скрипт
OUTPUT_FOLDER = os.getcwd() 

current_dir = os.getcwd()
moved_count = 0

for item in os.listdir(current_dir):
    item_path = os.path.join(current_dir, item)
    
    # Ищем только папки с гифтами
    if os.path.isdir(item_path) and item != "flattened_gifts" and not item.startswith('.'):
        for root, dirs, files in os.walk(item_path):
            for file in files:
                if file.lower().endswith(('.webp', '.png', '.jpg', '.jpeg', '.gif')):
                    source_file = os.path.join(root, file)
                    
                    # Вариант 1: Если оригинальный файл уже содержит ЦЕНАS (например, "50S.webp")
                    # Скрипт сделает имя типа "50S_Artisan_Brick.webp"
                    name_without_ext, file_extension = os.path.splitext(file)
                    
                    if "S" in name_without_ext:
                        # Если в файле уже есть цена, просто склеиваем её с красивым именем папки
                        new_file_name = f"{name_without_ext}_{item}{file_extension}"
                    else:
                        # Если цены внутри файла не было, оставляем имя папки
                        new_file_name = f"{item}{file_extension}"
                    
                    dest_file = os.path.join(OUTPUT_FOLDER, new_file_name)
                    
                    # Копируем в корень папки Gifts
                    shutil.copy2(source_file, dest_file)
                    print(f"Скопирован по формуле: {file} -> {new_file_name}")
                    moved_count += 1
                    break 

print(f"\nГотово! Все файлы ({moved_count} шт.) собраны по формуле цены прямо в '{OUTPUT_FOLDER}'")