import os

directory = '.' 

# ПОЛНЫЙ список всех твоих подарков со скрина image_287355.jpg
rename_map = {
   "Big Years.png": "2026S_Big Years.png",
    "Cupid Charms.png": "1500S_Cupid Charms.png",
    "Easter Eggs.png": "400S_Easter Eggs.png",
    "Electric Skulls.png": "1100S_Electric Skulls.png",
    "GiftBox.png": "500S_GiftBox.png",
    "Heart Lockets.png": "1200S_Heart Lockets.png",
    "Hearth.png": "950S_Hearth.png",
    "Skull Flowers.png": "1300S_Skull Flowers.png",
}

def rename_gifts():
    files = os.listdir(directory)
    count = 0
    print("--- ЗАПУСК ПОЛНОЙ ПЕРЕЗАГРУЗКИ ЭКОНОМИКИ ---")
    for filename in files:
        if filename in rename_map:
            new_name = rename_map[filename]
            if filename == new_name: continue 
            try:
                os.rename(filename, new_name)
                print(f"✅ Готово: {filename} -> {new_name}")
                count += 1
            except Exception as e:
                print(f"❌ Ошибка {filename}: {e}")
    
    print(f"\n🚀 ОГО! Переименовано: {count} предметов.")
    print("Теперь твои ассеты полностью готовы для ScreamCase!")

if __name__ == "__main__":
    rename_gifts()